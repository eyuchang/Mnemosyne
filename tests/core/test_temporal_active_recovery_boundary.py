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
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import ctl_record_from_transition_candidate
from mnemosyne.runtime.temporal import (
    FakeTemporalClient,
    TemporalRuntimeDriver,
    plan_validate_and_commit_active_recovery_activity,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r48-temporal-active-recovery"
W = "workflow:r48-temporal-active-recovery"
G = "tx:r48-temporal-active-recovery"
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
        description="Temporal active recovery for scoped dependent entity.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def proposal_provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:temporal-repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
            rationale="Repair stale dependent entity through activity boundary.",
        )
    ]


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
async def test_temporal_active_recovery_activity_commits_only_commitment_fsm():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    validator = Validator(build_commitment_fsm_registry())

    result = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    assert result.has_committed_records
    assert result.committed_only_commitment_fsm
    assert result.committed_action_types == ["commitment_proposal_emitted"]
    assert result.validation_ok == [True]
    assert result.commitment_statuses == {"c1": "proposed"}

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED


@pytest.mark.asyncio
async def test_temporal_active_recovery_activity_does_not_mutate_domain_state():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    validator = Validator(build_commitment_fsm_registry())

    await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]


@pytest.mark.asyncio
async def test_temporal_runtime_orchestrates_active_recovery_but_activity_commits_truth():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    client = FakeTemporalClient()
    runtime = TemporalRuntimeDriver(
        namespace="default",
        task_queue="mnemosyne-r48",
        client=client,
    )

    handle = await runtime.submit_workflow(
        {
            "workflow_id": W,
            "tenant_id": T,
            "app_id": "mnemosyne",
            "entity_id": "commitment:c1",
        }
    )

    assert handle.workflow_id == W
    assert handle.status == "submitted"

    status_before = await runtime.query_status(W)
    assert status_before.status == "submitted"

    validator = Validator(build_commitment_fsm_registry())

    activity_result = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    assert activity_result.committed_rids
    assert activity_result.committed_only_commitment_fsm

    status_after = await runtime.query_status(W)
    assert status_after.status == "submitted"
    assert status_after.detail["runtime"] == "fake_temporal"

    assert not hasattr(runtime, "commit_batch")
    assert not hasattr(runtime, "get_state_view")

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED


@pytest.mark.asyncio
async def test_temporal_active_recovery_activity_skips_unfired_commitment():
    store = SQLiteStore()

    c = commitment()
    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:commitment-register",
    )

    await store.commit_batch(
        batch("batch:commitment-live", [register]),
        [ctl_record_from_transition_candidate(register, version=1)],
    )

    validator = Validator(build_commitment_fsm_registry())

    result = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:temporal-active-recovery-empty",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    assert not result.has_committed_records
    assert result.committed_rids == []
    assert result.validation_ok == []
    assert result.skipped == {"c1": "status_live_not_recoverable"}
    assert result.commitment_statuses == {"c1": "live"}
