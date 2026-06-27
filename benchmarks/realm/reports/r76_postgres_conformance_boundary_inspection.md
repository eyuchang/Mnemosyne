# R7.6 PostgreSQL Conformance Boundary Inspection

## Summary

- Store schema id: `mnemosyne.store.sqlite`
- Store schema version: `1.0`
- SQLite table count: 9
- Required PostgreSQL table count: 2
- Decision: `postgres_conformance_boundary_ready_for_contract_tests`

## Required PostgreSQL Tables

- `store_schema_metadata`
- `recovery_events`

## Conformance Requirements

- `postgres_table_store_schema_metadata`: PostgreSQL store must provide `store_schema_metadata` with equivalent logical fields.
- `postgres_table_recovery_events`: PostgreSQL store must provide `recovery_events` with equivalent logical fields.
- `postgres_recovery_events_unique_event_id`: Preserve unique `(tenant_id, event_id)` for durable idempotency.
- `postgres_recovery_events_unique_idempotency_key`: Preserve unique `(tenant_id, idempotency_key)` for retry safety.
- `postgres_recovery_events_unique_sequence_no`: Preserve unique `(tenant_id, recovery_id, sequence_no)` for deterministic replay.
- `postgres_recovery_events_ordering`: List recovery events deterministically by recovery id, sequence number, and event id.
- `postgres_recovery_events_json_payload`: Payloads must round-trip JSON-compatible data without changing replay semantics.
- `postgres_schema_metadata`: Store schema id/version must be queryable and stable across restart.
- `postgres_capability_report`: PostgreSQL store must report durable recovery, idempotency, replay, and restart persistence capabilities.
- `postgres_default_ci_skip`: Live PostgreSQL conformance tests must be skipped unless an explicit database URL is supplied.

## PostgreSQL Schema Draft

```sql
CREATE TABLE store_schema_metadata (schema_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL, store_type TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL);
CREATE TABLE recovery_events (event_id TEXT NOT NULL, tenant_id TEXT NOT NULL, workflow_id TEXT, recovery_id TEXT NOT NULL, sequence_no INTEGER NOT NULL, event_type TEXT NOT NULL, idempotency_key TEXT NOT NULL, causality_key TEXT, payload JSONB NOT NULL, schema_id TEXT NOT NULL, schema_version TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (tenant_id, event_id), UNIQUE (tenant_id, idempotency_key), UNIQUE (tenant_id, recovery_id, sequence_no));
CREATE INDEX idx_recovery_events_recovery ON recovery_events (tenant_id, recovery_id, sequence_no);
CREATE INDEX idx_recovery_events_workflow ON recovery_events (tenant_id, workflow_id, created_at);
```

## Claims

- postgres_conformance_boundary_defined: True
- postgres_schema_draft_defined: True
- sqlite_remains_default_store: True
- live_postgres_required: False
- postgres_adapter_implemented: False
- postgres_live_conformance_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

## Limitations

- R7.6 Commit 1 defines the PostgreSQL conformance boundary only.
- No live PostgreSQL adapter is implemented in this commit.
- SQLite remains the default store and test target.
- Live PostgreSQL tests should remain skipped unless an explicit database URL is supplied.

