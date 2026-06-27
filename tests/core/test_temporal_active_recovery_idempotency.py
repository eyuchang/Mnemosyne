from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    active_commitment_index_from_store,
    build_commitment_fsm_registry,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.fsm import FSMDef, FSMEdge, FSMRegistry
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import ctl_record_from_transition_candidate
from mnemosyne.runtime.temporal import plan_validate_and_commit_active_recovery_activity
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r48-temporal-idempotency"
W = "workflow:r48-temporal-idempotency"
G = "tx:r48-temporal-idempotency"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def domain_record(*, rid: str, version: int, state_before: str, state_after: str) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        op_id=rid,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        binding_id=None,
        eid=DOMAIN_EID,
        fsm=DOMAIN_FSM,
        version=version,
        state_before=state_before,
        state_after=state_after,
        action_type="domain_transition",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_transition"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="test.validator",
        validator_version="1.0",
        timestamp=FT,
    )


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Temporal active recovery idempotency test.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def proposal_provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:temporal-idempotent-repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
            rationale="Repair stale dependent entity through activity boundary.",
        )
    ]


def incomplete_commitment_validator() -> Validator:
    registry = FSMRegistry()
    registry.register(
        FSMDef(
            fsm_id="mnemosyne.commitment",
            fsm_version="1.0",
            initial_state="none",
            edges=(
                FSMEdge("none", "live", "commitment_registered"),
                FSMEdge("live", "fired", "commitment_fired"),
            ),
        )
    )
    return Validator(registry)


async def seed_domain_and_fired_commitment(store: SQLiteStore) -> None:
    await store.commit_batch(
        batch("batch:domain-initial", []),
        [
            domain_record(
                rid="rid:domain-initial",
                version=1,
                state_before="none",
                state_after="stale",
            )
        ],
    )

    c = commitment()
    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:commitment-register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:commitment-fire",
    )

    await store.commit_batch(
        batch("batch:commitment-fire", [register, fire]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )


@pytest.mark.asyncio
async def test_temporal_active_recovery_activity_is_noop_after_successful_retry():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    validator = Validator(build_commitment_fsm_registry())

    first = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery:first",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    assert first.has_committed_records
    assert first.committed_action_types == ["commitment_proposal_emitted"]
    assert first.commitment_statuses == {"c1": "proposed"}

    second = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery:retry",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    assert not second.has_committed_records
    assert second.committed_rids == []
    assert second.committed_action_types == []
    assert second.validation_ok == []
    assert second.skipped == {"c1": "status_proposed_not_recoverable"}
    assert second.commitment_statuses == {"c1": "proposed"}

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]


@pytest.mark.asyncio
async def test_temporal_active_recovery_validation_failure_commits_nothing():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    result = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery:invalid",
        workflow_id=W,
        store=store,
        validator=incomplete_commitment_validator(),
        proposal_provider=proposal_provider,
    )

    assert not result.has_committed_records
    assert result.committed_rids == []
    assert result.committed_action_types == []
    assert result.validation_ok == [False]
    assert result.commitment_statuses == {"c1": "fired"}

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.FIRED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]


@pytest.mark.asyncio
async def test_temporal_active_recovery_activity_result_is_workflow_safe_summary():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    validator = Validator(build_commitment_fsm_registry())

    result = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery:summary",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    summary = {
        "batch_id": result.batch_id,
        "tenant_id": result.tenant_id,
        "workflow_id": result.workflow_id,
        "committed_rids": result.committed_rids,
        "committed_fsms": result.committed_fsms,
        "committed_action_types": result.committed_action_types,
        "validation_ok": result.validation_ok,
        "skipped": result.skipped,
        "commitment_statuses": result.commitment_statuses,
    }

    assert summary["batch_id"] == "batch:temporal-active-recovery:summary"
    assert summary["tenant_id"] == T
    assert summary["workflow_id"] == W
    assert summary["committed_fsms"] == ["mnemosyne.commitment"]
    assert summary["committed_action_types"] == ["commitment_proposal_emitted"]
    assert summary["validation_ok"] == [True]
    assert summary["skipped"] == {}
    assert summary["commitment_statuses"] == {"c1": "proposed"}

    # The returned result is orchestration-safe summary data, not CTL records
    # or mutable Store handles.
    assert "store" not in summary
    assert "records" not in summary
    assert "candidates" not in summary
