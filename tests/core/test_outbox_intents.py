from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import OutboxIntent
from mnemosyne.store.sqlite import SQLiteStore


def make_outbox_intent(
    *,
    outbox_id: str,
    tenant_id: str = "tenant-a",
    provider: str = "twilio",
    provider_idempotency_key: str = "twilio:ride:R001:notify-driver",
) -> OutboxIntent:
    return OutboxIntent(
        outbox_id=outbox_id,
        tenant_id=tenant_id,
        provider=provider,
        effect_type="send_sms",
        payload={
            "to": "+15551234567",
            "body": "Driver has arrived.",
        },
        provider_idempotency_key=provider_idempotency_key,
        workflow_id="ride:R001",
        binding_id="binding:R001",
        created_at=datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_enqueue_outbox_dedupes_by_provider_idempotency_key():
    store = SQLiteStore()

    first = make_outbox_intent(
        outbox_id="outbox-001",
        provider_idempotency_key="twilio:ride:R001:notify-driver",
    )
    duplicate = make_outbox_intent(
        outbox_id="outbox-002",
        provider_idempotency_key="twilio:ride:R001:notify-driver",
    )

    await store.enqueue_outbox([first])
    await store.enqueue_outbox([duplicate])

    rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE tenant_id = ?
          AND provider = ?
          AND provider_idempotency_key = ?
        """,
        ("tenant-a", "twilio", "twilio:ride:R001:notify-driver"),
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["outbox_id"] == "outbox-001"
    assert rows[0]["status"] == "pending"
    assert rows[0]["effect_type"] == "send_sms"


@pytest.mark.asyncio
async def test_outbox_idempotency_is_tenant_scoped():
    store = SQLiteStore()

    tenant_a_intent = make_outbox_intent(
        outbox_id="outbox-shared",
        tenant_id="tenant-a",
        provider_idempotency_key="twilio:shared-key",
    )
    tenant_b_intent = make_outbox_intent(
        outbox_id="outbox-shared",
        tenant_id="tenant-b",
        provider_idempotency_key="twilio:shared-key",
    )

    await store.enqueue_outbox([tenant_a_intent])
    await store.enqueue_outbox([tenant_b_intent])

    rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE provider = ?
          AND provider_idempotency_key = ?
        ORDER BY tenant_id ASC
        """,
        ("twilio", "twilio:shared-key"),
    ).fetchall()

    assert len(rows) == 2
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[1]["tenant_id"] == "tenant-b"