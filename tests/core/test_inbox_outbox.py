import pytest

from mnemosyne.core.models import ExternalEvent
from mnemosyne.store.sqlite import SQLiteStore


@pytest.mark.asyncio
async def test_inbox_dedupes_by_source_and_dedupe_key():
    store = SQLiteStore()

    event = ExternalEvent(
        event_id="evt-001",
        event_type="driver_arrived",
        tenant_id="tenant-a",
        workflow_id="ride:R001",
        binding_id="binding:R001",
        entity_refs={"driver": "driver:Joe"},
        payload={"location": "pickup"},
        source="gps",
        dedupe_key="gps:joe:arrived:001",
        schema_id="rideshare.event",
        schema_version="1.0",
    )

    first = await store.record_inbox_event(event)
    second = await store.record_inbox_event(event)

    assert first.event_id == "evt-001"
    assert second.event_id == "evt-001"
    assert first.event_id == second.event_id

    rows = store.conn.execute(
        """
        SELECT *
        FROM event_inbox
        WHERE tenant_id = ? AND source = ? AND dedupe_key = ?
        """,
        ("tenant-a", "gps", "gps:joe:arrived:001"),
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["event_id"] == "evt-001"
    assert rows[0]["status"] == "received"
