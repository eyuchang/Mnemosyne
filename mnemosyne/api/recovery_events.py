from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.core.protocols.recovery_store import require_recovery_store
from mnemosyne.core.recovery.events import (
    RecoveryEvent,
    recovery_event_to_dict,
)


@dataclass(frozen=True)
class RecoveryEventApiResult:
    event: RecoveryEvent
    created_or_existing: str


async def append_recovery_event(
    *,
    store: Any,
    event: RecoveryEvent,
) -> RecoveryEventApiResult:
    """Append or dedupe a durable recovery event through the store boundary."""

    store = require_recovery_store(store)

    appended = await store.append_recovery_event(event)
    created_or_existing = "created" if appended.event_id == event.event_id else "existing"

    return RecoveryEventApiResult(
        event=appended,
        created_or_existing=created_or_existing,
    )


async def list_recovery_events(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
    recovery_id: str | None = None,
    event_type: str | None = None,
) -> list[RecoveryEvent]:
    """List durable recovery events in deterministic replay order."""

    store = require_recovery_store(store)

    return await store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        event_type=event_type,
    )


def recovery_events_to_dicts(events: list[RecoveryEvent]) -> list[dict[str, Any]]:
    return [recovery_event_to_dict(event) for event in events]


def recovery_event_api_result_to_dict(result: RecoveryEventApiResult) -> dict[str, Any]:
    return {
        "created_or_existing": result.created_or_existing,
        "event": recovery_event_to_dict(result.event),
    }
