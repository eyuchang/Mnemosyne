from __future__ import annotations

import pytest

from mnemosyne.api.recovery_events import append_recovery_event
from mnemosyne.api.recovery_replay import (
    recovery_replay_api_result_to_dict,
    replay_recovery_events_from_store,
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
    event_type: str,
    idempotency_key: str,
    recovery_id: str = "recovery",
) -> RecoveryEvent:
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


@pytest.mark.asyncio
async def test_replay_recovery_events_from_store_reconstructs_state():
    store = SQLiteStore()

    await append_recovery_event(
        store=store,
        event=_event(
            event_id="event-2",
            sequence_no=2,
            event_type="proposal_package_created",
            idempotency_key="idem-2",
        ),
    )
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="idem-1",
        ),
    )

    result = await replay_recovery_events_from_store(
        store=store,
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
    )

    assert result.recovery_count == 1
    assert result.replayed_event_count == 2
    assert result.duplicate_event_count == 0

    state = result.states["recovery"]
    assert [event.event_id for event in state.events] == ["event-1", "event-2"]
    assert state.last_sequence_no == 2


@pytest.mark.asyncio
async def test_replay_recovery_events_from_store_serializes_report():
    store = SQLiteStore()

    await append_recovery_event(
        store=store,
        event=_event(
            event_id="event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="idem-1",
        ),
    )

    result = await replay_recovery_events_from_store(
        store=store,
        tenant_id="tenant",
        workflow_id="workflow",
    )

    report = recovery_replay_api_result_to_dict(result)

    assert report["tenant_id"] == "tenant"
    assert report["workflow_id"] == "workflow"
    assert report["recovery_count"] == 1
    assert report["states"][0]["recovery_id"] == "recovery"
    assert report["states"][0]["checkpoint"]["last_sequence_no"] == 1


@pytest.mark.asyncio
async def test_replay_recovery_events_from_store_filters_by_recovery_id():
    store = SQLiteStore()

    await append_recovery_event(
        store=store,
        event=_event(
            event_id="r1-event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="r1-idem-1",
            recovery_id="recovery-1",
        ),
    )
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="r2-event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="r2-idem-1",
            recovery_id="recovery-2",
        ),
    )

    result = await replay_recovery_events_from_store(
        store=store,
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery-2",
    )

    assert sorted(result.states) == ["recovery-2"]
    assert result.replayed_event_count == 1


@pytest.mark.asyncio
async def test_recovery_replay_api_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError):
        await replay_recovery_events_from_store(
            store=EmptyStore(),
            tenant_id="tenant",
            workflow_id="workflow",
        )
