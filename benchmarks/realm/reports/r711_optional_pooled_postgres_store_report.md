# R7.11 Optional Pooled PostgresStore Runtime Path Report

## Summary

R7.11 completes the optional PostgreSQL pooling path.

R7.10 defined the connection-pooling boundary. R7.11 connects that boundary to `PostgresStore` by allowing the store to use an explicitly supplied pooled connection provider.

## What changed

R7.11 adds:

- Optional `connection_provider` support in `PostgresStore`.
- Pool-compatible managed connection handling.
- Fake-pool tests proving that pooled connections are borrowed and returned.
- Rollback handling for pooled-provider failures.
- Env-gated live pooled PostgreSQL smoke test using `psycopg_pool`.
- Default CI remains PostgreSQL-free.
- Default CI remains pool-dependency-free.

## Runtime behavior

Without a connection provider:

- `PostgresStore` keeps the existing behavior.
- Each operation opens and closes its own PostgreSQL connection.

With a connection provider:

- `PostgresStore` borrows a connection from the provider.
- The store performs schema initialization and recovery-event operations.
- The borrowed connection is returned to the provider.
- The store does not close the pooled connection itself.

## Default validation

With `MNEMOSYNE_POSTGRES_DATABASE_URL` unset:

- Default suite after R7.11 Commit 2: 385 passed, 29 skipped.
- The live pooled PostgreSQL test is skipped by default.

## Live validation

With `MNEMOSYNE_POSTGRES_DATABASE_URL` set and `psycopg_pool` installed:

- `tests/core/test_postgres_live_pooled_runtime_path.py`: 1 passed.

## Claim boundary

Claimed:

- Optional pooled `PostgresStore` runtime path.
- Existing non-pooled `PostgresStore` path preserved.
- Explicit connection-provider injection.
- Pooled context manager borrow/return behavior.
- Pooled-provider rollback behavior.
- Live pooled PostgreSQL smoke validation.
- Default CI remains PostgreSQL-free.
- Default CI remains pool-dependency-free.

Not claimed:

- Production deployment.
- Kubernetes deployment.
- Temporal deployment.
- Pool performance benchmarking.
- High-concurrency pool saturation testing.
- Autoscaling.
- Distributed recovery storage.
- Production-runtime recovery.

## Milestone decision

R7.11 completes the PostgreSQL runtime adapter closure needed before deployment work.

After R7.11, R7 should be considered complete.
