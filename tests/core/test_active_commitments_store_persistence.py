from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    COMMITMENT_FSM,
    CommitmentEventType,
    CommitmentStatus,
    commitment_entity_id,
    event_from_extension,
    extract_commitment_events_from_ctl_records,
    make_discharge_commitment_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
    replay_commitments,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:active-commitment-store"
W = "workflow:active-commitment-store"
G = "tx:active-commitment-store"
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
        batch_id="batch:active-commitments",
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def test_generated_candidate_rid_matches_embedded_commitment_event_record_id():
    candidate = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c-generated",
        workflow_id=W,
    )

    event = event_from_extension(candidate.extension)

    assert event.record_id == candidate.rid


@pytest.mark.asyncio
async def test_active_commitment_candidates_persist_through_sqlite_ctl_and_replay():
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Revalidate when upstream evidence changes.",
        dependency_scope={"entity_id": "entity:upstream"},
        trigger={"kind": "world_change"},
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
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
    discharge = make_discharge_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:commitment-discharge",
        reason="obligation_satisfied",
    )

    candidates = [register, fire, discharge]
    records = [
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
        record_from_candidate(discharge, version=3),
    ]

    committed = await store.commit_batch(batch(candidates), records)

    assert [record.rid for record in committed] == [
        "rid:commitment-register",
        "rid:commitment-fire",
        "rid:commitment-discharge",
    ]

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
        CommitmentEventType.DISCHARGED,
    ]
    assert projection.status("c1") == CommitmentStatus.DISCHARGED
    assert "c1" not in projection.live_commitments()

    view = await store.get_state_view(T, commitment_entity_id("c1"), COMMITMENT_FSM)

    assert view.state == CommitmentStatus.DISCHARGED.value
    assert view.version == 3
