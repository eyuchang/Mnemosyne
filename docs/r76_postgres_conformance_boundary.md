# R7.6 PostgreSQL Conformance Boundary

R7.6 defines PostgreSQL as a conformance target, not as the architecture owner.

## Principle

The recovery-store protocol defines the architecture.

SQLite proves the local durable substrate.

PostgreSQL must later prove conformance to the same recovery-store contract.

## Added contract

- `RecoveryStoreConformanceCase`
- `RecoveryStoreConformanceObservation`
- `observe_recovery_store_conformance`
- `recovery_store_conformance_observation_to_dict`

## Required future PostgreSQL behavior

A future PostgreSQL store must pass the same recovery-store conformance contract:

- schema metadata is queryable,
- recovery events are durable,
- idempotency keys are enforced,
- recovery-event ordering is deterministic,
- replay after persistence preserves sequence semantics,
- live PostgreSQL tests are skipped unless a database URL is explicitly supplied.

## Claim boundary

R7.6 does not yet implement a PostgreSQL adapter.

R7.6 does not claim:

- live PostgreSQL conformance,
- distributed storage,
- Kubernetes deployment,
- Temporal execution,
- production-runtime recovery execution.
