# R7.8 PostgreSQL Live Adapter Report

## Summary

- PostgreSQL env: `MNEMOSYNE_POSTGRES_DATABASE_URL`
- Schema version: `1.0`
- Event ids: ['r78-event-1', 'r78-event-2']
- Replay event ids: ['r78-event-1', 'r78-event-2']
- Duplicate result event id: `r78-event-1`
- Adapter event count: 2
- Conformance passed: True
- Default CI safe: True
- Decision: `opt_in_postgres_recovery_event_adapter_established`

## Claims

- postgres_recovery_event_adapter_claimed: True
- postgres_schema_initialization_claimed: True
- postgres_event_append_claimed: True
- postgres_event_list_claimed: True
- postgres_idempotent_retry_claimed: True
- postgres_conformance_fake_connection_claimed: True
- live_postgres_env_opt_in_claimed: True
- default_ci_postgres_free_claimed: True
- real_postgres_service_required_in_default_ci: False
- distributed_storage_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

## Limitations

- R7.8 implements the PostgreSQL recovery-event adapter surface.
- Default CI uses fake connection tests and does not require a PostgreSQL service.
- Real live PostgreSQL conformance remains gated by MNEMOSYNE_POSTGRES_DATABASE_URL.
- R7.8 does not claim Kubernetes, Temporal, or production-runtime recovery.

