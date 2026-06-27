from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.api.commitments import (
    fire_active_commitment,
    get_active_commitment_status,
    register_active_commitment,
)
from mnemosyne.api.recovery import (
    plan_active_recovery,
    validate_and_commit_active_recovery,
)
from mnemosyne.core.commitments import ActiveCommitment, CommitmentStatus
from mnemosyne.core.fsm import FSMDef, FSMEdge, FSMRegistry
from mnemosyne.core.models import CommitBatch, CTLRecord
from mnemosyne.core.recovery import RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r50-api-recovery"
W = "workflow:r50-api-recovery"
G = "tx:r50-api-recovery"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Product-facing recovery API commitment.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def proposal_provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:r50-api-repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
            rationale="Repair stale dependent entity.",
        )
    ]


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
        CommitBatch(
            batch_id="batch:domain-initial",
            tenant_id=T,
            workflow_id=W,
            tx_group_id=G,
            candidates=[],
        ),
        [
            domain_record(
                rid="rid:domain-initial",
                version=1,
                state_before="none",
                state_after="stale",
            )
        ],
    )

    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        rid="rid:api-fire",
        batch_id="batch:api-fire",
    )


@pytest.mark.asyncio
async def test_recovery_api_plans_without_committing():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    plan = await plan_active_recovery(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=proposal_provider,
    )

    assert plan.has_candidates
    assert [candidate.action_type for candidate in plan.candidates] == [
        "commitment_proposal_emitted"
    ]

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )
    assert status == CommitmentStatus.FIRED


@pytest.mark.asyncio
async def test_recovery_api_validates_and_commits_commitment_fsm_only():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    execution = await validate_and_commit_active_recovery(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:api-active-recovery",
        workflow_id=W,
        proposal_provider=proposal_provider,
    )

    assert execution.has_committed_records
    assert execution.committed_only_commitment_fsm
    assert execution.committed_action_types == ["commitment_proposal_emitted"]
    assert execution.validation_ok == [True]

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )
    assert status == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]


@pytest.mark.asyncio
async def test_recovery_api_validation_failure_commits_nothing():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    execution = await validate_and_commit_active_recovery(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:api-active-recovery-invalid",
        workflow_id=W,
        proposal_provider=proposal_provider,
        validator=incomplete_commitment_validator(),
    )

    assert not execution.has_committed_records
    assert execution.committed_rids == []
    assert execution.validation_ok == [False]

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )
    assert status == CommitmentStatus.FIRED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1


@pytest.mark.asyncio
async def test_recovery_api_skips_unfired_live_commitment():
    store = SQLiteStore()

    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    execution = await validate_and_commit_active_recovery(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:api-active-recovery-empty",
        workflow_id=W,
        proposal_provider=proposal_provider,
    )

    assert not execution.has_committed_records
    assert execution.committed_rids == []
    assert execution.validation_ok == []
    assert execution.skipped == {"c1": "status_live_not_recoverable"}
