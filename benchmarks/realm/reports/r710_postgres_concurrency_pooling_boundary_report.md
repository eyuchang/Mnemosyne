# R7.10 PostgreSQL Concurrency and Connection-Pooling Boundary Report

## Summary

R7.10 validates live PostgreSQL concurrent recovery-event behavior and defines the explicit connection-pooling boundary.

## Live PostgreSQL concurrency validation

With `MNEMOSYNE_POSTGRES_DATABASE_URL` set:

- Concurrent duplicate idempotency gate: passed.
- Concurrent duplicate writers return one canonical event: passed.
- Concurrent sequence-conflict gate: passed.
- Sequence-conflict losers raise clean `PostgresRecoveryEventConflictError`: passed.
- PostgreSQL service required for these tests: yes.
- Default CI required to run these tests: no.

## Connection-pooling boundary

R7.10 adds an explicit pooling boundary without making pooling a default dependency.

Claimed:

- Pool configuration object.
- Pool env vars.
- Lazy optional `psycopg_pool` import.
- Fail-closed validation when DATABASE_URL is absent.
- Honest boundary report.
- Default CI does not require `psycopg_pool`.
- Default CI does not require PostgreSQL service.

Not claimed:

- Production pool deployment.
- Pool-backed `PostgresStore` runtime path.
- Connection pool performance validation.
- High-concurrency load testing.
- Kubernetes.
- Temporal.
- Distributed storage.
- Production-runtime recovery.

## Default validation

With `MNEMOSYNE_POSTGRES_DATABASE_URL` unset:

- Full suite: 380 passed, 28 skipped.

## Live validation

With `MNEMOSYNE_POSTGRES_DATABASE_URL` set:

- `tests/core/test_postgres_live_concurrent_recovery_events.py`: 2 passed.

## Milestone decision

R7.10 establishes the PostgreSQL concurrency and pooling boundary.

It demonstrates live concurrent idempotency/conflict behavior in an env-gated validation run and prepares the system for a later optional pooled adapter path, without introducing any required PostgreSQL or pool dependency into default CI.
