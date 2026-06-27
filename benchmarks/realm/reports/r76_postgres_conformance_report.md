# R7.6 PostgreSQL Conformance Report

## Summary

- Store schema id: `mnemosyne.store.sqlite`
- Store schema version: `1.0`
- PostgreSQL conformance env: `MNEMOSYNE_POSTGRES_DATABASE_URL`
- Env present: False
- Live PostgreSQL required: False
- Default CI safe: True
- SQLite remains default store: True
- Decision: `postgres_live_conformance_harness_defined_as_opt_in`

## Future Live Conformance Plan

- Implement PostgreSQL recovery-store adapter behind the RecoveryStore protocol.
- Construct PostgreSQL store only when MNEMOSYNE_POSTGRES_DATABASE_URL is supplied.
- Run observe_recovery_store_conformance against PostgreSQL with restart persistence expected.
- Keep default CI independent of PostgreSQL service availability.

## Claims

- postgres_conformance_boundary_defined: True
- postgres_live_test_harness_defined: True
- postgres_live_test_opt_in: True
- sqlite_remains_default_store: True
- live_postgres_required: False
- postgres_adapter_implemented: False
- postgres_live_conformance_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

## Limitations

- R7.6 defines the PostgreSQL live conformance harness only.
- R7.6 does not implement the PostgreSQL adapter.
- R7.6 does not require a PostgreSQL service in default CI.
- R7.6 does not claim Kubernetes, Temporal, or production-runtime recovery.

