from __future__ import annotations

import pytest

from mnemosyne.api.recovery_events import (
    append_recovery_event,
    list_recovery_events,
    recovery_event_api_result_to_dict,
    recovery_events_to_dicts,
)
from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError
from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.store.sqlite.store import SQLiteStore


class EmptyStore:
    pass


def _event(
    *,
    event_id: str,
    sequence_no: int,
    idempotency_key: str,
    event_type: str = "commitment_fired",
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        sequence_no=sequence_no,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload={"sequence": sequence_no},
    )


@pytest.mark.asyncio
async def test_append_recovery_event_api_appends_event():
    store = SQLiteStore()
    event = _event(event_id="event-1", sequence_no=1, idempotency_key="idem-1")

    result = await append_recovery_event(store=store, event=event)

    assert result.event == event
    assert result.created_or_existing == "created"

    result_dict = recovery_event_api_result_to_dict(result)
    assert result_dict["created_or_existing"] == "created"
    assert result_dict["event"]["event_id"] == "event-1"


@pytest.mark.asyncio
async def test_append_recovery_event_api_returns_existing_on_idempotent_retry():
    store = SQLiteStore()
    first = _event(event_id="event-1", sequence_no=1, idempotency_key="same-key")
    duplicate = _event(event_id="event-2", sequence_no=2, idempotency_key="same-key")

    await append_recovery_event(store=store, event=first)
    result = await append_recovery_event(store=store, event=duplicate)

    assert result.created_or_existing == "existing"
    assert result.event.event_id == "event-1"
    assert result.event.sequence_no == 1


@pytest.mark.asyncio
async def test_list_recovery_events_api_filters_and_serializes_events():
    store = SQLiteStore()

    await append_recovery_event(
        store=store,
        event=_event(
            event_id="event-1",
            sequence_no=1,
            idempotency_key="idem-1",
            event_type="commitment_fired",
        ),
    )
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="event-2",
            sequence_no=2,
            idempotency_key="idem-2",
            event_type="proposal_package_created",
        ),
    )

    events = await list_recovery_events(
        store=store,
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        event_type="proposal_package_created",
    )

    assert [event.event_id for event in events] == ["event-2"]

    dicts = recovery_events_to_dicts(events)
    assert dicts[0]["event_type"] == "proposal_package_created"


@pytest.mark.asyncio
async def test_recovery_event_api_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError):
        await append_recovery_event(
            store=EmptyStore(),
            event=_event(event_id="event-1", sequence_no=1, idempotency_key="idem-1"),
        )

    with pytest.raises(RecoveryStoreCapabilityError):
        await list_recovery_events(
            store=EmptyStore(),
            tenant_id="tenant",
            workflow_id="workflow",
        )
