from __future__ import annotations

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.recovery.replay import (
    recovery_replay_states_to_dicts,
    replay_recovery_events,
)


def _event(
    *,
    event_id: str,
    recovery_id: str = "recovery",
    sequence_no: int,
    event_type: str,
    idempotency_key: str,
):
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id=recovery_id,
        sequence_no=sequence_no,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload={"event_id": event_id},
    )


def test_replay_recovery_events_reconstructs_state_in_sequence_order():
    events = [
        _event(
            event_id="event-2",
            sequence_no=2,
            event_type="proposal_package_created",
            idempotency_key="idem-2",
        ),
        _event(
            event_id="event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="idem-1",
        ),
        _event(
            event_id="event-3",
            sequence_no=3,
            event_type="repair_admission_committed",
            idempotency_key="idem-3",
        ),
    ]

    states = replay_recovery_events(events)

    state = states["recovery"]
    assert [event.event_id for event in state.events] == [
        "event-1",
        "event-2",
        "event-3",
    ]
    assert state.replayed_event_count == 3
    assert state.duplicate_event_count == 0
    assert state.last_sequence_no == 3
    assert state.terminal_event_seen is True
    assert state.event_counts == {
        "commitment_fired": 1,
        "proposal_package_created": 1,
        "repair_admission_committed": 1,
    }


def test_replay_recovery_events_is_idempotent_for_duplicate_event_id_and_key():
    original = _event(
        event_id="event-1",
        sequence_no=1,
        event_type="commitment_fired",
        idempotency_key="idem-1",
    )
    duplicate_id = _event(
        event_id="event-1",
        sequence_no=2,
        event_type="commitment_fired",
        idempotency_key="idem-duplicate",
    )
    duplicate_key = _event(
        event_id="event-duplicate-key",
        sequence_no=3,
        event_type="commitment_fired",
        idempotency_key="idem-1",
    )

    state = replay_recovery_events([original, duplicate_id, duplicate_key])["recovery"]

    assert [event.event_id for event in state.events] == ["event-1"]
    assert [event.event_id for event in state.duplicate_events] == [
        "event-1",
        "event-duplicate-key",
    ]
    assert state.replayed_event_count == 1
    assert state.duplicate_event_count == 2
    assert state.event_counts == {"commitment_fired": 1}


def test_replay_recovery_events_groups_multiple_recoveries():
    states = replay_recovery_events(
        [
            _event(
                event_id="r2-event-1",
                recovery_id="recovery-2",
                sequence_no=1,
                event_type="commitment_fired",
                idempotency_key="r2-idem-1",
            ),
            _event(
                event_id="r1-event-1",
                recovery_id="recovery-1",
                sequence_no=1,
                event_type="commitment_fired",
                idempotency_key="r1-idem-1",
            ),
        ]
    )

    assert sorted(states) == ["recovery-1", "recovery-2"]

    as_dicts = recovery_replay_states_to_dicts(states)
    assert [row["recovery_id"] for row in as_dicts] == ["recovery-1", "recovery-2"]
    assert as_dicts[0]["checkpoint"]["last_sequence_no"] == 1
