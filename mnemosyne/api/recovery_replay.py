from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.core.protocols.recovery_store import require_recovery_store
from mnemosyne.core.recovery.replay import (
    RecoveryReplayState,
    recovery_replay_state_to_dict,
    recovery_replay_states_to_dicts,
    replay_recovery_events,
)


@dataclass(frozen=True)
class RecoveryReplayApiResult:
    tenant_id: str
    workflow_id: str | None
    recovery_id: str | None
    states: dict[str, RecoveryReplayState]

    @property
    def recovery_count(self) -> int:
        return len(self.states)

    @property
    def replayed_event_count(self) -> int:
        return sum(state.replayed_event_count for state in self.states.values())

    @property
    def duplicate_event_count(self) -> int:
        return sum(state.duplicate_event_count for state in self.states.values())


async def replay_recovery_events_from_store(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
    recovery_id: str | None = None,
    event_type: str | None = None,
) -> RecoveryReplayApiResult:
    """Read durable recovery events and reconstruct replay state."""

    store = require_recovery_store(store)

    events = await store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        event_type=event_type,
    )

    return RecoveryReplayApiResult(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        states=replay_recovery_events(events),
    )


def recovery_replay_api_result_to_dict(result: RecoveryReplayApiResult) -> dict[str, Any]:
    return {
        "tenant_id": result.tenant_id,
        "workflow_id": result.workflow_id,
        "recovery_id": result.recovery_id,
        "recovery_count": result.recovery_count,
        "replayed_event_count": result.replayed_event_count,
        "duplicate_event_count": result.duplicate_event_count,
        "states": recovery_replay_states_to_dicts(result.states),
    }


def recovery_replay_state_to_report_dict(state: RecoveryReplayState) -> dict[str, Any]:
    return recovery_replay_state_to_dict(state)
