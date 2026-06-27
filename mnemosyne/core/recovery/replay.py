from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mnemosyne.core.recovery.events import RecoveryEvent, recovery_event_to_dict


TERMINAL_RECOVERY_EVENT_TYPES = frozenset(
    {
        "repair_admission_committed",
        "commitment_finalized",
        "recovery_lineage_audited",
    }
)


@dataclass(frozen=True)
class RecoveryReplayCheckpoint:
    tenant_id: str
    recovery_id: str
    last_sequence_no: int
    replayed_event_count: int
    duplicate_event_count: int
    idempotency_keys: tuple[str, ...]


@dataclass(frozen=True)
class RecoveryReplayState:
    tenant_id: str
    recovery_id: str
    workflow_id: str | None
    events: tuple[RecoveryEvent, ...]
    duplicate_events: tuple[RecoveryEvent, ...] = field(default_factory=tuple)
    event_counts: dict[str, int] = field(default_factory=dict)
    payloads_by_type: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    checkpoint: RecoveryReplayCheckpoint | None = None
    terminal_event_seen: bool = False

    @property
    def replayed_event_count(self) -> int:
        return len(self.events)

    @property
    def duplicate_event_count(self) -> int:
        return len(self.duplicate_events)

    @property
    def last_sequence_no(self) -> int:
        return self.checkpoint.last_sequence_no if self.checkpoint else 0


def _event_sort_key(event: RecoveryEvent) -> tuple[str, int, str]:
    return (event.recovery_id, event.sequence_no, event.event_id)


def replay_recovery_events(events: list[RecoveryEvent]) -> dict[str, RecoveryReplayState]:
    """Reconstruct recovery replay state from durable events.

    Replay is deterministic and idempotent:
    - events are sorted by recovery_id, sequence_no, event_id;
    - duplicate event_id values are ignored;
    - duplicate idempotency_key values are ignored;
    - duplicate events are retained separately for audit visibility.
    """

    grouped: dict[str, list[RecoveryEvent]] = {}
    for event in sorted(events, key=_event_sort_key):
        grouped.setdefault(event.recovery_id, []).append(event)

    states: dict[str, RecoveryReplayState] = {}

    for recovery_id, recovery_events in grouped.items():
        accepted: list[RecoveryEvent] = []
        duplicates: list[RecoveryEvent] = []
        seen_event_ids: set[str] = set()
        seen_idempotency_keys: set[str] = set()
        event_counts: dict[str, int] = {}
        payloads: dict[str, list[dict[str, Any]]] = {}
        terminal_seen = False

        tenant_id = recovery_events[0].tenant_id
        workflow_id = recovery_events[0].workflow_id

        for event in recovery_events:
            duplicate = (
                event.event_id in seen_event_ids
                or event.idempotency_key in seen_idempotency_keys
            )
            if duplicate:
                duplicates.append(event)
                continue

            accepted.append(event)
            seen_event_ids.add(event.event_id)
            seen_idempotency_keys.add(event.idempotency_key)

            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            payloads.setdefault(event.event_type, []).append(dict(event.payload))

            if event.event_type in TERMINAL_RECOVERY_EVENT_TYPES:
                terminal_seen = True

        checkpoint = RecoveryReplayCheckpoint(
            tenant_id=tenant_id,
            recovery_id=recovery_id,
            last_sequence_no=max((event.sequence_no for event in accepted), default=0),
            replayed_event_count=len(accepted),
            duplicate_event_count=len(duplicates),
            idempotency_keys=tuple(sorted(seen_idempotency_keys)),
        )

        states[recovery_id] = RecoveryReplayState(
            tenant_id=tenant_id,
            recovery_id=recovery_id,
            workflow_id=workflow_id,
            events=tuple(accepted),
            duplicate_events=tuple(duplicates),
            event_counts=event_counts,
            payloads_by_type={
                event_type: tuple(rows) for event_type, rows in payloads.items()
            },
            checkpoint=checkpoint,
            terminal_event_seen=terminal_seen,
        )

    return states


def recovery_replay_state_to_dict(state: RecoveryReplayState) -> dict[str, Any]:
    return {
        "tenant_id": state.tenant_id,
        "workflow_id": state.workflow_id,
        "recovery_id": state.recovery_id,
        "replayed_event_count": state.replayed_event_count,
        "duplicate_event_count": state.duplicate_event_count,
        "last_sequence_no": state.last_sequence_no,
        "terminal_event_seen": state.terminal_event_seen,
        "event_counts": dict(sorted(state.event_counts.items())),
        "payloads_by_type": {
            key: list(value) for key, value in sorted(state.payloads_by_type.items())
        },
        "checkpoint": {
            "tenant_id": state.checkpoint.tenant_id,
            "recovery_id": state.checkpoint.recovery_id,
            "last_sequence_no": state.checkpoint.last_sequence_no,
            "replayed_event_count": state.checkpoint.replayed_event_count,
            "duplicate_event_count": state.checkpoint.duplicate_event_count,
            "idempotency_keys": list(state.checkpoint.idempotency_keys),
        }
        if state.checkpoint
        else None,
        "events": [recovery_event_to_dict(event) for event in state.events],
        "duplicate_events": [
            recovery_event_to_dict(event) for event in state.duplicate_events
        ],
    }


def recovery_replay_states_to_dicts(
    states: dict[str, RecoveryReplayState],
) -> list[dict[str, Any]]:
    return [
        recovery_replay_state_to_dict(states[recovery_id])
        for recovery_id in sorted(states)
    ]
