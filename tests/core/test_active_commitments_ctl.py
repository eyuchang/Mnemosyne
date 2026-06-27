from datetime import datetime, timezone

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEvent,
    CommitmentEventType,
    CommitmentStatus,
    event_from_extension,
    event_to_extension,
    extract_commitment_events_from_ctl_records,
    is_commitment_extension,
    replay_commitments,
)
from mnemosyne.core.models import CTLRecord


def make_ctl_record(rid: str, extension: dict) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        eid="entity:1",
        fsm="test.fsm",
        version=1,
        state_before="before",
        state_after="after",
        action_type="commitment_event",
        workflow_id="workflow:1",
        binding_id=None,
        triggers=[],
        dependencies=[],
        metadata={},
        extension=extension,
        app_id="core",
        app_version="1.0",
        schema_id="mnemosyne.active_commitment_event",
        schema_version="1.0",
        fsm_version="1.0",
        timestamp=datetime.now(timezone.utc),
    )


def test_commitment_event_round_trips_through_ctl_extension():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Revalidate dependent state when upstream evidence changes.",
        dependency_scope={"entity_id": "entity:1"},
        trigger={"kind": "world_change"},
    )

    event = CommitmentEvent(
        event_type=CommitmentEventType.REGISTERED,
        commitment_id="c1",
        payload={"commitment": commitment},
        record_id="rid:1",
        workflow_id="workflow:1",
    )

    extension = event_to_extension(event)

    assert is_commitment_extension(extension)

    restored = event_from_extension(extension)

    assert restored.event_type == CommitmentEventType.REGISTERED
    assert restored.commitment_id == "c1"
    assert restored.record_id == "rid:1"
    assert restored.workflow_id == "workflow:1"
    assert restored.payload["commitment"] == commitment


def test_commitment_events_can_be_extracted_from_ctl_records_and_replayed():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="delayed_guard",
        description="Wake when guard becomes true.",
    )

    registered = CommitmentEvent(
        event_type=CommitmentEventType.REGISTERED,
        commitment_id="c1",
        payload={"commitment": commitment},
        record_id="rid:1",
        workflow_id="workflow:1",
    )

    fired = CommitmentEvent(
        event_type=CommitmentEventType.FIRED,
        commitment_id="c1",
        payload={"reason": "trigger_true"},
        record_id="rid:2",
        workflow_id="workflow:1",
    )

    records = [
        make_ctl_record("rid:1", event_to_extension(registered)),
        make_ctl_record("rid:2", event_to_extension(fired)),
    ]

    events = extract_commitment_events_from_ctl_records(records)
    projection = replay_commitments(events)

    assert len(events) == 2
    assert projection.status("c1") == CommitmentStatus.FIRED
    assert "c1" in projection.live_commitments()


def test_non_commitment_ctl_record_is_ignored():
    record = make_ctl_record("rid:ordinary", {"kind": "ordinary_extension"})

    events = extract_commitment_events_from_ctl_records([record])

    assert events == []
