from __future__ import annotations

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresConnectionPoolConfig,
    PostgresRecoveryEventConflictError,
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
            "source": "r7111-live-pooled-concurrency",
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _append_sync(store: PostgresStore, event: RecoveryEvent):
    return asyncio.run(store.append_recovery_event(event))


@pytest.mark.asyncio
async def test_live_pooled_concurrent_duplicate_idempotency_returns_one_canonical_event():
    pytest.importorskip("psycopg_pool")

    tenant_id = f"tenant-r7111-idem-{uuid.uuid4()}"
    workflow_id = f"workflow-r7111-idem-{uuid.uuid4()}"
    recovery_id = f"recovery-r7111-idem-{uuid.uuid4()}"

    pool = create_psycopg_connection_pool(
        PostgresConnectionPoolConfig(
            database_url=DATABASE_URL,
            min_size=1,
            max_size=4,
            timeout_seconds=10.0,
            open_immediately=True,
        )
    )

    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )

        # Warm schema initialization outside the race.
        await store.list_recovery_events(tenant_id)

        events = [
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"r7111-pooled-idem-event-{index}",
                sequence_no=index + 1,
                idempotency_key="r7111-pooled-shared-idempotency-key",
            )
            for index in range(12)
        ]

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=12) as executor:
            results = await asyncio.gather(
                *[
                    loop.run_in_executor(executor, _append_sync, store, event)
                    for event in events
                ]
            )

        result_ids = {result.event_id for result in results}
        assert len(result_ids) == 1

        listed = await store.list_recovery_events(
            tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
        )

        assert len(listed) == 1
        assert listed[0].event_id == next(iter(result_ids))
    finally:
        pool.close()


@pytest.mark.asyncio
async def test_live_pooled_concurrent_sequence_conflicts_are_cleanly_reported():
    pytest.importorskip("psycopg_pool")

    tenant_id = f"tenant-r7111-seq-{uuid.uuid4()}"
    workflow_id = f"workflow-r7111-seq-{uuid.uuid4()}"
    recovery_id = f"recovery-r7111-seq-{uuid.uuid4()}"

    pool = create_psycopg_connection_pool(
        PostgresConnectionPoolConfig(
            database_url=DATABASE_URL,
            min_size=1,
            max_size=4,
            timeout_seconds=10.0,
            open_immediately=True,
        )
    )

    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )

        # Warm schema initialization outside the race.
        await store.list_recovery_events(tenant_id)

        events = [
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"r7111-pooled-seq-event-{index}",
                sequence_no=1,
                idempotency_key=f"r7111-pooled-seq-idem-{index}",
            )
            for index in range(8)
        ]

        def attempt(event: RecoveryEvent):
            try:
                result = _append_sync(store, event)
                return ("ok", result.event_id)
            except PostgresRecoveryEventConflictError as exc:
                return ("conflict", str(exc))

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = await asyncio.gather(
                *[
                    loop.run_in_executor(executor, attempt, event)
                    for event in events
                ]
            )

        successes = [value for kind, value in results if kind == "ok"]
        conflicts = [value for kind, value in results if kind == "conflict"]

        assert len(successes) == 1
        assert len(conflicts) == 7

        listed = await store.list_recovery_events(
            tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
        )

        assert len(listed) == 1
        assert listed[0].event_id == successes[0]
    finally:
        pool.close()
