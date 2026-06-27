# R7.5 Store Durability and Migration Readiness

R7.5 adds explicit store schema metadata and a durability capability report.

## Added surface

- `STORE_SCHEMA_ID`
- `STORE_SCHEMA_VERSION`
- `StoreCapabilityReport`
- `get_store_schema_version`
- `get_store_capability_report`
- SQLite `store_schema_metadata` table

## Current claim

SQLiteStore remains the local durable conformance target.

R7.5 records:

- schema identity,
- schema version,
- recovery-event durability capability,
- recovery-event idempotency capability,
- deterministic recovery replay ordering,
- restart-persistence capability for file-backed SQLite stores.

## Claim boundary

R7.5 does not claim:

- PostgreSQL support,
- distributed storage,
- Kubernetes deployment,
- Temporal execution,
- production-runtime recovery execution.

PostgreSQL remains a later conformance target.
