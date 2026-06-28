# R7.9 Live PostgreSQL DATABASE_URL Conformance Report

## Summary

R7.9 validates that the PostgreSQL recovery-event adapter works against a real PostgreSQL service when explicitly enabled through:

`MNEMOSYNE_POSTGRES_DATABASE_URL`

## Live validation

- Live PostgreSQL server: yes
- PostgreSQL version: PostgreSQL 16.14 via Homebrew
- Live DATABASE_URL test: passed
- Live append/list/replay/reopen path: passed
- Live duplicate idempotency path: passed
- Live sequence-conflict path: passed
- Live conformance contract path: passed

## Default CI validation

- Default CI PostgreSQL dependency: no
- Default CI live PostgreSQL tests: skipped
- Default suite without DATABASE_URL: passed

## Validation evidence

With `MNEMOSYNE_POSTGRES_DATABASE_URL` set:

- `tests/core/test_postgres_live_database_url_conformance.py`: passed
- `tests/core/test_postgres_live_conformance_boundary.py`: passed

Without `MNEMOSYNE_POSTGRES_DATABASE_URL`:

- Full suite: 372 passed, 26 skipped

## Claim boundary

Claimed:

- Real PostgreSQL DATABASE_URL conformance.
- PostgreSQL append recovery event.
- PostgreSQL duplicate idempotency.
- PostgreSQL sequence-conflict handling.
- PostgreSQL deterministic list ordering.
- PostgreSQL replay after list.
- PostgreSQL reopen persistence.
- Default CI remains PostgreSQL-free.

Not claimed:

- Kubernetes.
- Temporal.
- Distributed storage.
- Production-runtime recovery.
- Connection pooling.
- High-concurrency load testing.
