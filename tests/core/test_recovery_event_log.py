from __future__ import annotations

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.store.sqlite.store import SQLiteStore


@pytest.mark.asyncio
async def test_sqlite_recovery_event_log_appends_and_lists_in_replay_order():
    store = SQLiteStore()

    event2 = RecoveryEvent(
        event_id="event-2",
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        sequence_no=2,
        event_type="proposal_package_created",
        idempotency_key="idem-2",
        payload={"step": 2},
    )
    event1 = RecoveryEvent(
        event_id="event-1",
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        sequence_no=1,
        event_type="commitment_fired",
        idempotency_key="idem-1",
        payload={"step": 1},
    )

    await store.append_recovery_event(event2)
    await store.append_recovery_event(event1)

    events = await store.list_recovery_events(
        "tenant",
        workflow_id="workflow",
        recovery_id="recovery",
    )

    assert [event.event_id for event in events] == ["event-1", "event-2"]
    assert [event.sequence_no for event in events] == [1, 2]


@pytest.mark.asyncio
async def test_sqlite_recovery_event_log_dedupes_by_idempotency_key():
    store = SQLiteStore()

    first = RecoveryEvent(
        event_id="event-1",
        tenant_id="tenant",
        recovery_id="recovery",
        sequence_no=1,
        event_type="commitment_fired",
        idempotency_key="same-key",
        payload={"first": True},
    )
    duplicate = RecoveryEvent(
        event_id="event-duplicate",
        tenant_id="tenant",
        recovery_id="recovery",
        sequence_no=2,
        event_type="commitment_fired",
        idempotency_key="same-key",
        payload={"first": False},
    )

    assert await store.append_recovery_event(first) == first
    returned = await store.append_recovery_event(duplicate)

    assert returned.event_id == "event-1"
    assert returned.payload == {"first": True}

    events = await store.list_recovery_events("tenant", recovery_id="recovery")
    assert len(events) == 1


@pytest.mark.asyncio
async def test_sqlite_recovery_event_log_persists_across_store_instances(tmp_path):
    db_path = tmp_path / "recovery.sqlite"

    first_store = SQLiteStore(db_path)
    await first_store.append_recovery_event(
        RecoveryEvent(
            event_id="event-1",
            tenant_id="tenant",
            workflow_id="workflow",
            recovery_id="recovery",
            sequence_no=1,
            event_type="repair_admission_committed",
            idempotency_key="idem-1",
            payload={"admitted": True},
        )
    )

    second_store = SQLiteStore(db_path)
    events = await second_store.list_recovery_events(
        "tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        event_type="repair_admission_committed",
    )

    assert len(events) == 1
    assert events[0].event_id == "event-1"
    assert events[0].payload == {"admitted": True}
