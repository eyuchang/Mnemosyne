from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresConnectionPoolConfig,
    PostgresStore,
    PostgresStoreConfig,
    create_psycopg_connection_pool,
)


DATABASE_URL = os.environ.get(POSTGRES_DATABASE_URL_ENV)

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason=f"{POSTGRES_DATABASE_URL_ENV} is not set",
)


def _event(
    *,
    tenant_id: str,
    workflow_id: str,
    recovery_id: str,
    event_id: str,
    sequence_no: int,
    idempotency_key: str,
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        sequence_no=sequence_no,
        event_type="commitment_fired",
        idempotency_key=idempotency_key,
        causality_key=f"cause-{event_id}",
        payload={
            "event_id": event_id,
            "sequence_no": sequence_no,
            "source": "r711-live-pooled-postgres-runtime-path",
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_live_postgres_store_can_use_psycopg_pool_connection_provider():
    pytest.importorskip("psycopg_pool")

    tenant_id = f"tenant-r711-{uuid.uuid4()}"
    workflow_id = f"workflow-r711-{uuid.uuid4()}"
    recovery_id = f"recovery-r711-{uuid.uuid4()}"

    pool = create_psycopg_connection_pool(
        PostgresConnectionPoolConfig(
            database_url=DATABASE_URL,
            min_size=1,
            max_size=2,
            timeout_seconds=5.0,
            open_immediately=True,
        )
    )

    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )

        await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id="r711-pooled-event-2",
                sequence_no=2,
                idempotency_key="r711-pooled-idem-2",
            )
        )
        await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id="r711-pooled-event-1",
                sequence_no=1,
                idempotency_key="r711-pooled-idem-1",
            )
        )
        duplicate = await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id="r711-pooled-event-duplicate",
                sequence_no=3,
                idempotency_key="r711-pooled-idem-1",
            )
        )

        listed = await store.list_recovery_events(
            tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
        )

        assert duplicate.event_id == "r711-pooled-event-1"
        assert [event.event_id for event in listed] == [
            "r711-pooled-event-1",
            "r711-pooled-event-2",
        ]
    finally:
        pool.close()
