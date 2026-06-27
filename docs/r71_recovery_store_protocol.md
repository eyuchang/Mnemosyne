# R7.1 Recovery Store Protocol

R7.1 introduces an explicit recovery store protocol surface.

This commit does not introduce PostgreSQL, Kubernetes, Temporal, or production-runtime recovery. It defines the durable-store boundary that later R7 commits can harden.

## Protocol surfaces

- `RecoveryReadStore`
  - `get_record`
  - `get_entity_history`
  - `get_full_entity_history`
  - `get_state_view`
  - `get_by_op_id`

- `RecoveryWriteStore`
  - all read methods
  - `commit_batch`

- `RecoveryStore`
  - complete recovery read/write surface

## Current conformance target

`SQLiteStore` satisfies the protocol surface and remains the local conformance target.

## Later R7 work

- Add fail-closed capability checks.
- Refactor recovery/audit APIs away from `Any` toward protocol-typed stores.
- Add append-only recovery event log.
- Add replay and idempotency tests.
- Add PostgreSQL-backed conformance target.

## Claim boundary

R7.1 claims only a protocol boundary and SQLite conformance surface.

R7.1 does not claim:

- PostgreSQL support,
- distributed storage,
- Kubernetes deployment,
- Temporal execution,
- production-runtime durable recovery.
