"""R7.11 follow-up: TRUE concurrency through the pooled PostgresStore path.

This is the test the milestone is missing. The existing pooled tests append
sequentially, so they never contend the pool or the idempotency / sequence
gates. This test runs real concurrent appends against a live PostgreSQL pool
and asserts the observable contract only (no assumptions about the store's
internal SQL or exception handling).

Why threads, not asyncio.gather: PostgresStore's append/list are `async def`
but perform synchronous psycopg I/O with no await points, so awaiting them in
one event loop serializes them. Real contention requires separate OS threads,
each running the coroutine to completion against its own pooled connection.

Gating: skipped unless MNEMOSYNE_POSTGRES_DATABASE_URL is set, and psycopg_pool
is importorskip-ed, so default CI stays PostgreSQL-free and pool-free.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# The sequence-conflict error class is named in the R7.10 report. Import it if
# present so we can assert the *typed* error; otherwise fall back to asserting
# that exactly one writer won and the rest raised something.
try:  # pragma: no cover - import shape depends on the build
    from mnemosyne.store.postgres import PostgresRecoveryEventConflictError
except ImportError:  # pragma: no cover
    try:
        from mnemosyne.store.postgres.store import PostgresRecoveryEventConflictError
    except ImportError:
        PostgresRecoveryEventConflictError = None  # type: ignore[assignment]


DATABASE_URL = os.environ.get(POSTGRES_DATABASE_URL_ENV)

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason=f"{POSTGRES_DATABASE_URL_ENV} is not set",
)

CONCURRENCY = 12


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
        payload={"event_id": event_id, "source": "r711-pooled-concurrency"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _make_pool():
    return create_psycopg_connection_pool(
        PostgresConnectionPoolConfig(
            database_url=DATABASE_URL,
            min_size=2,
            max_size=CONCURRENCY,
            timeout_seconds=10.0,
            open_immediately=True,
        )
    )


def _append_in_thread(store: PostgresStore, event: RecoveryEvent) -> RecoveryEvent:
    """Run one async append to completion in this thread's own event loop."""
    return asyncio.run(store.append_recovery_event(event))


def _run_concurrently(store: PostgresStore, events: list[RecoveryEvent]):
    results: list[RecoveryEvent] = []
    errors: list[BaseException] = []
    with ThreadPoolExecutor(max_workers=len(events)) as pool:
        futures = [pool.submit(_append_in_thread, store, ev) for ev in events]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except BaseException as exc:  # noqa: BLE001 - we classify below
                errors.append(exc)
    return results, errors


@pytest.mark.asyncio
async def test_pooled_concurrent_duplicate_idempotency_returns_one_canonical_event():
    """N writers, same idempotency_key, distinct event_id and sequence_no.

    Correct behavior: every concurrent append converges on ONE canonical event
    and none raises. A failure here (some append raising a unique violation)
    means the idempotency path is check-then-insert and loses the TOCTOU race
    under contention, i.e. it is not concurrency-safe.
    """
    pytest.importorskip("psycopg_pool")
    pool = _make_pool()
    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )
        tenant_id = f"tenant-conc-{uuid.uuid4()}"
        workflow_id = f"wf-{uuid.uuid4()}"
        recovery_id = f"rec-{uuid.uuid4()}"
        shared_key = f"idem-{uuid.uuid4()}"

        events = [
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"evt-{i}-{uuid.uuid4()}",
                sequence_no=i + 1,  # distinct, so only idempotency_key collides
                idempotency_key=shared_key,
            )
            for i in range(CONCURRENCY)
        ]

        results, errors = _run_concurrently(store, events)

        assert errors == [], f"idempotent append raced (not concurrency-safe): {errors!r}"
        canonical = {ev.event_id for ev in results}
        assert len(canonical) == 1, f"expected one canonical event, got {canonical}"

        listed = await store.list_recovery_events(
            tenant_id, workflow_id=workflow_id, recovery_id=recovery_id
        )
        assert len(listed) == 1
        assert listed[0].event_id in canonical
    finally:
        pool.close()


@pytest.mark.asyncio
async def test_pooled_concurrent_sequence_conflict_has_exactly_one_winner():
    """N writers, same (recovery_id, sequence_no), distinct event_id and idem key.

    Correct behavior: exactly one append commits; the rest are rejected by the
    UNIQUE(recovery_id, sequence_no) gate and surface a clean conflict error.
    The store must never end up with two rows at the same (recovery_id, seq).
    """
    pytest.importorskip("psycopg_pool")
    pool = _make_pool()
    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )
        tenant_id = f"tenant-conf-{uuid.uuid4()}"
        workflow_id = f"wf-{uuid.uuid4()}"
        recovery_id = f"rec-{uuid.uuid4()}"

        events = [
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id=f"evt-{i}-{uuid.uuid4()}",
                sequence_no=7,  # identical -> conflict on (recovery_id, sequence_no)
                idempotency_key=f"idem-{i}-{uuid.uuid4()}",  # distinct
            )
            for i in range(CONCURRENCY)
        ]

        results, errors = _run_concurrently(store, events)

        assert len(results) == 1, f"expected exactly one winner, got {len(results)}"
        assert len(errors) == CONCURRENCY - 1

        if PostgresRecoveryEventConflictError is not None:
            offenders = [e for e in errors if not isinstance(e, PostgresRecoveryEventConflictError)]
            assert not offenders, f"losers raised non-conflict errors: {offenders!r}"

        listed = await store.list_recovery_events(
            tenant_id, workflow_id=workflow_id, recovery_id=recovery_id
        )
        assert len(listed) == 1
        assert listed[0].sequence_no == 7
    finally:
        pool.close()


@pytest.mark.asyncio
async def test_pool_not_exhausted_by_repeated_concurrent_bursts():
    """The pool is still usable after several concurrent bursts (no leak).

    If borrowed connections were not returned, max_size would be exhausted and
    a later burst would block until timeout. This catches a borrow/return leak
    that the fake tests cannot.
    """
    pytest.importorskip("psycopg_pool")
    pool = _make_pool()
    try:
        store = PostgresStore(
            PostgresStoreConfig(database_url=DATABASE_URL),
            connection_provider=pool.connection,
        )
        for burst in range(3):
            tenant_id = f"tenant-burst-{burst}-{uuid.uuid4()}"
            workflow_id = f"wf-{uuid.uuid4()}"
            recovery_id = f"rec-{uuid.uuid4()}"
            events = [
                _event(
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    recovery_id=recovery_id,
                    event_id=f"evt-{i}-{uuid.uuid4()}",
                    sequence_no=i + 1,
                    idempotency_key=f"idem-{i}-{uuid.uuid4()}",
                )
                for i in range(CONCURRENCY)
            ]
            results, errors = _run_concurrently(store, events)
            assert errors == [], f"burst {burst} raised: {errors!r}"
            assert len(results) == CONCURRENCY
    finally:
        pool.close()
