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
from mnemosyne.core.recovery import RecoveryContext, RecoveryPolicy, RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import (
    LocalActiveRecoveryExecutor,
    ctl_record_from_transition_candidate,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:runtime-active-recovery-validation"
W = "workflow:runtime-active-recovery-validation"
G = "tx:runtime-active-recovery-validation"
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


def retry_provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:bad",
            proposal_scope={"entity_id": "domain:outside"},
        ),
        RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        ),
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


async def seed_fired_commitment(store: SQLiteStore) -> None:
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
        batch("batch:commitment-fire", [register, fire]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )


@pytest.mark.asyncio
async def test_validated_executor_commits_recovery_candidate_through_validator():
    store = SQLiteStore()

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
    await seed_fired_commitment(store)

    executor = LocalActiveRecoveryExecutor(store)
    validation = Validator(build_commitment_fsm_registry())

    execution = await executor.plan_validate_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:validated-active-recovery",
        workflow_id=W,
        proposal_provider=provider,
        validator=validation,
    )

    assert execution.has_committed_records
    assert len(execution.validation_results) == 1
    assert execution.validation_results[0].ok
    assert execution.committed[0].action_type == "commitment_proposal_emitted"
    assert execution.committed[0].validator_id == "core.validator"

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1


@pytest.mark.asyncio
async def test_validation_failure_commits_no_recovery_candidate():
    store = SQLiteStore()
    await seed_fired_commitment(store)

    executor = LocalActiveRecoveryExecutor(store)

    execution = await executor.plan_validate_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:invalid-active-recovery",
        workflow_id=W,
        proposal_provider=provider,
        validator=incomplete_commitment_validator(),
    )

    assert not execution.has_committed_records
    assert execution.records == []
    assert execution.committed == []
    assert len(execution.validation_results) == 1
    assert not execution.validation_results[0].ok

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.FIRED


@pytest.mark.asyncio
async def test_validated_executor_sequentially_admits_retry_candidates():
    store = SQLiteStore()
    await seed_fired_commitment(store)

    executor = LocalActiveRecoveryExecutor(store)
    validation = Validator(build_commitment_fsm_registry())

    execution = await executor.plan_validate_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:validated-retry",
        workflow_id=W,
        proposal_provider=retry_provider,
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
        validator=validation,
        contexts={"c1": RecoveryContext(commitment_id="c1")},
    )

    assert [record.action_type for record in execution.committed] == [
        "commitment_rejected",
        "commitment_proposal_emitted",
    ]
    assert [record.version for record in execution.committed] == [3, 4]
    assert len(execution.validation_results) == 2
    assert all(result.ok for result in execution.validation_results)

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED


@pytest.mark.asyncio
async def test_validated_executor_still_never_mutates_domain_state():
    store = SQLiteStore()

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
    await seed_fired_commitment(store)

    executor = LocalActiveRecoveryExecutor(store)
    validation = Validator(build_commitment_fsm_registry())

    await executor.plan_validate_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:validated-no-domain-mutation",
        workflow_id=W,
        proposal_provider=provider,
        validator=validation,
    )

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]
