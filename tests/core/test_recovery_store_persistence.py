from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    COMMITMENT_FSM,
    CommitmentEventType,
    CommitmentStatus,
    commitment_entity_id,
    extract_commitment_events_from_ctl_records,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
    replay_commitments,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryContext, RecoveryProposal, orchestrate_recovery
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:recovery-store"
W = "workflow:recovery-store"
G = "tx:recovery-store"
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


def batch(candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id="batch:recovery-store",
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


@pytest.mark.asyncio
async def test_allowed_recovery_orchestration_persists_as_proposed_commitment_state():
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
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

    orchestrated = orchestrate_recovery(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": "domain:entity:1"},
        ),
        workflow_id=W,
        rid="rid:proposal",
        dependency_rid="rid:fire",
    )

    assert orchestrated.allowed

    candidates = [register, fire, orchestrated.candidate]
    records = [
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
        record_from_candidate(orchestrated.candidate, version=3),
    ]

    await store.commit_batch(batch(candidates), records)

    history = await store.get_full_entity_history(
        T,
        commitment_entity_id("c1"),
        COMMITMENT_FSM,
    )

    events = extract_commitment_events_from_ctl_records(history)
    projection = replay_commitments(events)

    assert [event.event_type for event in events] == [
        CommitmentEventType.REGISTERED,
        CommitmentEventType.FIRED,
        CommitmentEventType.PROPOSAL_EMITTED,
    ]
    assert projection.status("c1") == CommitmentStatus.PROPOSED
    assert "c1" in projection.live_commitments()

    # Recovery proposal is only a commitment-FSM transition. It must not mutate
    # the domain entity named in proposal_scope.
    domain_view = await store.get_state_view(T, "domain:entity:1", "domain.fsm")
    assert domain_view.state is None
    assert domain_view.version == 0
    assert domain_view.effective_records == []


@pytest.mark.asyncio
async def test_denied_recovery_orchestration_persists_as_rejected_commitment_state():
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        workflow_id=W,
        rid="rid:register-denied",
    )

    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire-denied",
    )

    orchestrated = orchestrate_recovery(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:bad",
            proposal_scope={"entity_id": "domain:entity:outside-scope"},
        ),
        workflow_id=W,
        rid="rid:rejected",
        dependency_rid="rid:fire-denied",
    )

    assert not orchestrated.allowed

    candidates = [register, fire, orchestrated.candidate]
    records = [
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
        record_from_candidate(orchestrated.candidate, version=3),
    ]

    await store.commit_batch(batch(candidates), records)

    history = await store.get_full_entity_history(
        T,
        commitment_entity_id("c1"),
        COMMITMENT_FSM,
    )

    events = extract_commitment_events_from_ctl_records(history)
    projection = replay_commitments(events)

    assert [event.event_type for event in events] == [
        CommitmentEventType.REGISTERED,
        CommitmentEventType.FIRED,
        CommitmentEventType.REJECTED,
    ]
    assert projection.status("c1") == CommitmentStatus.REJECTED
    assert "c1" in projection.live_commitments()

    domain_view = await store.get_state_view(T, "domain:entity:outside-scope", "domain.fsm")
    assert domain_view.state is None
    assert domain_view.version == 0
    assert domain_view.effective_records == []
