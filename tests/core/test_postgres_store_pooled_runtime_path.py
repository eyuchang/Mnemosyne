from __future__ import annotations

import pytest

from mnemosyne.store.postgres import (
    PostgresStore,
    PostgresStoreConfig,
)
from tests.core.test_postgres_store_live_adapter_surface import (
    FakePostgresConnection,
    _event,
)


class FakePooledConnectionContext:
    def __init__(self, pool: "FakePostgresConnectionPool") -> None:
        self.pool = pool

    def __enter__(self) -> FakePostgresConnection:
        self.pool.acquire_count += 1
        return self.pool.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        self.pool.release_count += 1
        return None


class FakePostgresConnectionPool:
    def __init__(self) -> None:
        self.connection = FakePostgresConnection()
        self.connection.close_count = 0
        self.acquire_count = 0
        self.release_count = 0

    def connection_context(self) -> FakePooledConnectionContext:
        return FakePooledConnectionContext(self)


@pytest.mark.asyncio
async def test_postgres_store_can_use_optional_pooled_connection_provider():
    pool = FakePostgresConnectionPool()
    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_provider=pool.connection_context,
    )

    first = await store.append_recovery_event(_event("pool-event-2", 2, "pool-idem-2"))
    second = await store.append_recovery_event(_event("pool-event-1", 1, "pool-idem-1"))
    duplicate = await store.append_recovery_event(
        _event("pool-event-duplicate", 3, "pool-idem-1")
    )

    assert first.event_id == "pool-event-2"
    assert second.event_id == "pool-event-1"
    assert duplicate.event_id == "pool-event-1"

    events = await store.list_recovery_events(
        "tenant-pg",
        workflow_id="workflow-pg",
        recovery_id="recovery-pg",
    )

    assert [event.event_id for event in events] == ["pool-event-1", "pool-event-2"]

    assert pool.acquire_count == 4
    assert pool.release_count == 4
    assert pool.connection.close_count == 0


class ExplodingCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def execute(self, *_args, **_kwargs):
        raise RuntimeError("synthetic pooled connection failure")


class ExplodingConnection:
    def __init__(self) -> None:
        self.rollback_count = 0
        self.close_count = 0

    def cursor(self):
        return ExplodingCursor()

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.close_count += 1


class ExplodingConnectionContext:
    def __init__(self, connection: ExplodingConnection) -> None:
        self.connection = connection
        self.acquire_count = 0
        self.release_count = 0

    def __enter__(self):
        self.acquire_count += 1
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        self.release_count += 1
        return None


@pytest.mark.asyncio
async def test_postgres_store_pooled_provider_rolls_back_on_error():
    connection = ExplodingConnection()
    context = ExplodingConnectionContext(connection)

    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_provider=lambda: context,
    )

    with pytest.raises(RuntimeError):
        await store.list_recovery_events("tenant-pg")

    assert context.acquire_count == 1
    assert context.release_count == 1
    assert connection.rollback_count == 1
    assert connection.close_count == 0
