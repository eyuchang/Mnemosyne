"""R7.11 follow-up: default-CI contract tests for the pooled PostgresStore path.

These run with no PostgreSQL and no psycopg_pool. They build on the existing
``FakePostgresConnection`` (so the fake stays in step with the store's current
SQL) but add the unique-constraint enforcement the R7.8 fake was missing, which
lets us assert two things the prior fakes could not:

  1. The pooled provider borrows and returns a connection per operation and the
     store never closes a pooled connection, even across many operations.
  2. The store does not SILENTLY accept a duplicate (recovery_id, sequence_no)
     row; a conflicting insert surfaces an error rather than producing two rows.

Honest limits (do not over-read these):
  * A synchronous fake cursor cannot interleave, so this file does NOT prove
    concurrency timing. The TOCTOU idempotency race and the *typed*
    PostgresRecoveryEventConflictError are proven only by the live test,
    tests/core/test_postgres_live_pooled_concurrency.py.
"""

from __future__ import annotations

import pytest

from mnemosyne.store.postgres import PostgresStore, PostgresStoreConfig
from tests.core.test_postgres_store_live_adapter_surface import (
    FakePostgresConnection,
    _event,
)


class _FakeUniqueViolation(Exception):
    """Stand-in for a DB unique-constraint violation (no psycopg dependency)."""


class _ConstraintEvents(list):
    """An in-memory recovery_events table that enforces the three unique keys."""

    def append(self, row: dict) -> None:  # type: ignore[override]
        for existing in self:
            if existing["tenant_id"] != row["tenant_id"]:
                continue
            if existing["event_id"] == row["event_id"]:
                raise _FakeUniqueViolation("PRIMARY KEY (tenant_id, event_id)")
            if existing["idempotency_key"] == row["idempotency_key"]:
                raise _FakeUniqueViolation("UNIQUE (tenant_id, idempotency_key)")
            if (
                existing["recovery_id"] == row["recovery_id"]
                and existing["sequence_no"] == row["sequence_no"]
            ):
                raise _FakeUniqueViolation("UNIQUE (tenant_id, recovery_id, sequence_no)")
        list.append(self, row)


class ConstraintFakeConnection(FakePostgresConnection):
    """FakePostgresConnection whose recovery_events enforces unique keys."""

    def __init__(self) -> None:
        super().__init__()
        self.recovery_events = _ConstraintEvents()
        self.close_count = 0

    def close(self) -> None:  # the store must never call this on a pooled conn
        self.close_count += 1


class _PooledBorrow:
    def __init__(self, pool: "FakeConstraintPool") -> None:
        self.pool = pool

    def __enter__(self) -> ConstraintFakeConnection:
        self.pool.acquire_count += 1
        return self.pool.conn

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.pool.release_count += 1
        return False  # never suppress; the store owns rollback/raise


class FakeConstraintPool:
    """Minimal pool: one shared connection, context-manager borrow/return."""

    def __init__(self) -> None:
        self.conn = ConstraintFakeConnection()
        self.acquire_count = 0
        self.release_count = 0

    def connection(self) -> _PooledBorrow:  # provider == pool.connection
        return _PooledBorrow(self)


def _store(pool: FakeConstraintPool) -> PostgresStore:
    return PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_provider=pool.connection,
    )


@pytest.mark.asyncio
async def test_pooled_idempotency_returns_canonical_and_inserts_once():
    pool = FakeConstraintPool()
    store = _store(pool)

    first = await store.append_recovery_event(_event("evt-a", 1, "idem-K"))
    # Same idempotency_key, different event_id/sequence_no -> must dedupe.
    dup = await store.append_recovery_event(_event("evt-b", 2, "idem-K"))

    assert first.event_id == "evt-a"
    assert dup.event_id == "evt-a"  # canonical returned, not the new id

    listed = await store.list_recovery_events(
        "tenant-pg", workflow_id="workflow-pg", recovery_id="recovery-pg"
    )
    assert [e.event_id for e in listed] == ["evt-a"]
    assert pool.acquire_count == pool.release_count
    assert pool.conn.close_count == 0


@pytest.mark.asyncio
async def test_pooled_sequence_conflict_is_not_silently_accepted():
    pool = FakeConstraintPool()
    store = _store(pool)

    await store.append_recovery_event(_event("evt-a", 1, "idem-1"))

    # New event_id + new idempotency_key, but same (recovery_id, sequence_no):
    # the dedupe SELECT cannot catch it, so the INSERT must hit the unique key.
    # Contract: this raises rather than producing a second row at (rec, seq=1).
    # (The *typed* PostgresRecoveryEventConflictError is asserted in the live test;
    #  here the store may not recognize the fake's exception type, so we only
    #  assert that no silent duplicate is created.)
    with pytest.raises(Exception):  # noqa: B017 - intentionally broad; see comment
        await store.append_recovery_event(_event("evt-c", 1, "idem-2"))

    listed = await store.list_recovery_events(
        "tenant-pg", workflow_id="workflow-pg", recovery_id="recovery-pg"
    )
    assert len(listed) == 1  # no second row at sequence_no=1
    assert pool.acquire_count == pool.release_count
    assert pool.conn.close_count == 0


@pytest.mark.asyncio
async def test_pooled_borrow_return_symmetry_and_no_close_under_many_ops():
    pool = FakeConstraintPool()
    store = _store(pool)

    n = 20
    for i in range(n):
        await store.append_recovery_event(_event(f"evt-{i}", i + 1, f"idem-{i}"))
    listed = await store.list_recovery_events(
        "tenant-pg", workflow_id="workflow-pg", recovery_id="recovery-pg"
    )

    assert len(listed) == n
    # Every borrow is returned, and the store never closes a pooled connection.
    assert pool.acquire_count == pool.release_count
    assert pool.acquire_count >= n
    assert pool.conn.close_count == 0
