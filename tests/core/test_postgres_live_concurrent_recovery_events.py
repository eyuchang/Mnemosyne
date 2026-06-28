from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresRecoveryEventConflictError,
    PostgresStore,
    PostgresStoreConfig,
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
            "source": "r710-live-postgres-concurrency",
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_live_postgres_concurrent_duplicate_idempotency_returns_canonical_event():
    tenant_id = f"tenant-r710-{uuid.uuid4()}"
    workflow_id = f"workflow-r710-{uuid.uuid4()}"
    recovery_id = f"recovery-r710-{uuid.uuid4()}"

    async def append_duplicate(index: int) -> str:
        store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))
        result = await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"r710-duplicate-event-{index}",
                sequence_no=index + 1,
                idempotency_key="r710-shared-idempotency-key",
            )
        )
        return result.event_id

    results = await asyncio.gather(*(append_duplicate(index) for index in range(12)))

    assert len(set(results)) == 1

    store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))
    listed = await store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
    )

    assert len(listed) == 1
    assert listed[0].event_id == results[0]
    assert listed[0].idempotency_key == "r710-shared-idempotency-key"


@pytest.mark.asyncio
async def test_live_postgres_concurrent_sequence_conflicts_are_cleanly_reported():
    tenant_id = f"tenant-r710-{uuid.uuid4()}"
    workflow_id = f"workflow-r710-{uuid.uuid4()}"
    recovery_id = f"recovery-r710-{uuid.uuid4()}"

    async def append_sequence_conflict(index: int):
        store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))
        return await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"r710-sequence-event-{index}",
                sequence_no=1,
                idempotency_key=f"r710-sequence-idem-{index}",
            )
        )

    results = await asyncio.gather(
        *(append_sequence_conflict(index) for index in range(8)),
        return_exceptions=True,
    )

    successes = [result for result in results if isinstance(result, RecoveryEvent)]
    conflicts = [
        result
        for result in results
        if isinstance(result, PostgresRecoveryEventConflictError)
    ]

    assert len(successes) == 1
    assert len(conflicts) == 7

    store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))
    listed = await store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
    )

    assert len(listed) == 1
    assert listed[0].sequence_no == 1
