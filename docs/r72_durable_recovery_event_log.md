# R7.2 Durable Recovery Event Log

R7.2 adds the first durable recovery substrate primitive: an append-only recovery event log.

## Added surface

- `RecoveryEvent`
- `append_recovery_event`
- `list_recovery_events`
- SQLite-backed `recovery_events` table
- tenant-scoped event identity
- tenant-scoped idempotency key
- deterministic replay ordering by recovery id and sequence number

## Event fields

- `event_id`
- `tenant_id`
- `workflow_id`
- `recovery_id`
- `sequence_no`
- `event_type`
- `idempotency_key`
- `causality_key`
- `payload`
- `schema_id`
- `schema_version`
- `created_at`

## Claim boundary

R7.2 claims a durable append-only recovery event log in SQLite.

R7.2 does not claim:

- PostgreSQL support,
- Kubernetes deployment,
- Temporal execution,
- distributed recovery,
- production-runtime recovery execution.

Those remain later R7/R8 work.
