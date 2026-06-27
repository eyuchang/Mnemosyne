# R7.7 Optional PostgreSQL Adapter Skeleton

R7.7 adds the optional PostgreSQL adapter surface without requiring PostgreSQL in default CI.

## Added surface

- `PostgresStoreConfig`
- `PostgresStore`
- `PostgresStoreNotConfiguredError`
- `postgres_store_config_from_env`
- `MNEMOSYNE_POSTGRES_DATABASE_URL`

## Boundary

The PostgreSQL adapter is opt-in.

Default CI remains SQLite-only.

The adapter skeleton reports future PostgreSQL conformance capability but does not yet implement live PostgreSQL persistence.

## Claim boundary

R7.7 claims:

- PostgreSQL adapter module exists,
- PostgreSQL configuration boundary exists,
- missing configuration fails closed,
- default CI remains PostgreSQL-free.

R7.7 does not claim:

- live PostgreSQL persistence,
- live PostgreSQL conformance,
- distributed storage,
- Kubernetes deployment,
- Temporal execution,
- production-runtime recovery execution.
