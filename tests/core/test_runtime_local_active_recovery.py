from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    active_commitment_index_from_store,
    make_commitment_proposal_candidate,
    make_commitment_rejected_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryContext, RecoveryProposal
from mnemosyne.runtime.local import (
    LocalActiveRecoveryExecutor,
    ctl_record_from_transition_candidate,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:runtime-active-recovery"
W = "workflow:runtime-active-recovery"
G = "tx:runtime-active-recovery"
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
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        )
    ]


@pytest.mark.asyncio
async def test_local_executor_commits_recovery_candidate_for_fired_commitment():
    store = SQLiteStore()
    c = commitment()

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
        batch("batch:commitment-fire", [register, fire]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )

    executor = LocalActiveRecoveryExecutor(store)
    execution = await executor.plan_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:active-recovery",
        workflow_id=W,
        proposal_provider=provider,
    )

    assert execution.has_committed_records
    assert len(execution.committed) == 1
    assert execution.committed[0].action_type == "commitment_proposal_emitted"
    assert execution.committed[0].eid == "commitment:c1"
    assert execution.committed[0].fsm == "mnemosyne.commitment"
    assert execution.committed[0].version == 3

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]


@pytest.mark.asyncio
async def test_local_executor_skips_unfired_live_commitment():
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
        batch("batch:commitment-live", [register]),
        [ctl_record_from_transition_candidate(register, version=1)],
    )

    executor = LocalActiveRecoveryExecutor(store)
    execution = await executor.plan_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:active-recovery-empty",
        workflow_id=W,
        proposal_provider=provider,
    )

    assert not execution.has_committed_records
    assert execution.committed == []
    assert execution.plan.skipped == {"c1": "status_live_not_recoverable"}


@pytest.mark.asyncio
async def test_local_executor_retries_rejected_commitment_without_domain_mutation():
    store = SQLiteStore()
    c = commitment()

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
        batch("batch:commitment-rejected", [register, fire, rejected]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
            ctl_record_from_transition_candidate(rejected, version=3),
        ],
    )

    executor = LocalActiveRecoveryExecutor(store)
    execution = await executor.plan_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:active-recovery-retry",
        workflow_id=W,
        proposal_provider=provider,
        contexts={"c1": RecoveryContext(commitment_id="c1", attempt_index=1)},
    )

    assert execution.has_committed_records
    assert execution.committed[0].action_type == "commitment_proposal_emitted"
    assert execution.committed[0].state_before == CommitmentStatus.REJECTED.value
    assert execution.committed[0].state_after == CommitmentStatus.PROPOSED.value
    assert execution.committed[0].version == 4

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1


@pytest.mark.asyncio
async def test_local_executor_does_not_duplicate_already_proposed_commitment():
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
        proposal_scope={"entity_id": DOMAIN_EID},
        workflow_id=W,
        rid="rid:proposal",
    )

    await store.commit_batch(
        batch("batch:commitment-proposed", [register, fire, proposal]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
            ctl_record_from_transition_candidate(proposal, version=3),
        ],
    )

    executor = LocalActiveRecoveryExecutor(store)
    execution = await executor.plan_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:active-recovery-skip-proposed",
        workflow_id=W,
        proposal_provider=provider,
    )

    assert not execution.has_committed_records
    assert execution.plan.skipped == {"c1": "status_proposed_not_recoverable"}
