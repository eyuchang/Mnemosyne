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

## Store factory

R7.7 also adds an optional store factory:

- `StoreFactoryConfig`
- `store_factory_config_from_env`
- `create_store`
- `MNEMOSYNE_STORE_BACKEND`
- `MNEMOSYNE_SQLITE_PATH`

The default backend remains SQLite.

PostgreSQL selection is explicit through `MNEMOSYNE_STORE_BACKEND=postgres` or `StoreFactoryConfig(backend="postgres")`.

