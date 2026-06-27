from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    make_commitment_proposal_candidate,
    make_commitment_rejected_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import (
    RecoveryContext,
    RecoveryProposal,
    plan_recovery_from_store,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:recovery-service"
W = "workflow:recovery-service"
G = "tx:recovery-service"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def record_from_candidate(candidate: TransitionCandidate, *, version: int) -> CTLRecord:
    return CTLRecord(
        rid=candidate.rid,
        op_id=candidate.op_id or candidate.rid,
        tenant_id=candidate.tenant_id,
        tx_group_id=candidate.tx_group_id,
        workflow_id=candidate.workflow_id,
        binding_id=candidate.binding_id,
        eid=candidate.eid,
        fsm=candidate.fsm,
        version=version,
        state_before=candidate.state_before,
        state_after=candidate.state_after,
        action_type=candidate.action_type,
        triggers=list(candidate.triggers),
        dependencies=list(candidate.dependencies),
        metadata=dict(candidate.metadata),
        extension=dict(candidate.extension),
        app_id=candidate.app_id,
        app_version=candidate.app_version,
        schema_id=candidate.schema_id,
        schema_version=candidate.schema_version,
        fsm_version=candidate.fsm_version,
        policy_id=candidate.policy_id,
        policy_version=candidate.policy_version,
        validator_id=candidate.validator_id,
        validator_version=candidate.validator_version,
        timestamp=FT,
    )


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )


def provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": "domain:entity:1"},
        )
    ]


@pytest.mark.asyncio
async def test_service_plans_recovery_for_fired_commitment_from_store_index():
    store = SQLiteStore()
    c = commitment()

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )

    await store.commit_batch(
        batch("batch:fired", [register, fire]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
        ],
    )

    plan = await plan_recovery_from_store(
        store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=provider,
    )

    assert plan.has_candidates
    assert len(plan.candidates) == 1
    assert plan.candidates[0].eid == "commitment:c1"
    assert plan.candidates[0].fsm == "mnemosyne.commitment"
    assert plan.candidates[0].action_type == "commitment_proposal_emitted"
    assert plan.candidates[0].state_before == CommitmentStatus.FIRED.value


@pytest.mark.asyncio
async def test_service_skips_live_commitment_that_has_not_fired():
    store = SQLiteStore()
    c = commitment()

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )

    await store.commit_batch(
        batch("batch:live", [register]),
        [record_from_candidate(register, version=1)],
    )

    plan = await plan_recovery_from_store(
        store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=provider,
    )

    assert not plan.has_candidates
    assert plan.skipped == {"c1": "status_live_not_recoverable"}


@pytest.mark.asyncio
async def test_service_retries_from_rejected_commitment_state():
    store = SQLiteStore()
    c = commitment()

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    rejected = make_commitment_rejected_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        rejection_code="CONSTRAINT_FAILED",
        rejection_evidence={"reason": "first_repair_failed"},
        state_before=CommitmentStatus.FIRED.value,
        workflow_id=W,
        rid="rid:rejected",
    )

    await store.commit_batch(
        batch("batch:rejected", [register, fire, rejected]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(rejected, version=3),
        ],
    )

    plan = await plan_recovery_from_store(
        store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=provider,
        contexts={"c1": RecoveryContext(commitment_id="c1", attempt_index=1)},
    )

    assert plan.has_candidates
    assert plan.candidates[0].action_type == "commitment_proposal_emitted"
    assert plan.candidates[0].state_before == CommitmentStatus.REJECTED.value


@pytest.mark.asyncio
async def test_service_skips_already_proposed_commitment_to_avoid_duplicate_proposal():
    store = SQLiteStore()
    c = commitment()

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    proposal = make_commitment_proposal_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        proposal_ref="proposal:repair:1",
        proposal_scope={"entity_id": "domain:entity:1"},
        workflow_id=W,
        rid="rid:proposal",
    )

    await store.commit_batch(
        batch("batch:proposed", [register, fire, proposal]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(proposal, version=3),
        ],
    )

    plan = await plan_recovery_from_store(
        store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=provider,
    )

    assert not plan.has_candidates
    assert plan.skipped == {"c1": "status_proposed_not_recoverable"}
