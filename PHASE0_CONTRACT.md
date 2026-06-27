# Mnemosyne Phase 0 Contract

Phase 0 pins implementation contracts before Temporal, OR-Tools, and LLM integrations.

## Source of truth

- CTL is the source of truth for committed state.
- Event log is the source of truth for observed causes and non-commit decisions.
- Runtime engines are orchestration mechanisms, not domain truth.

## Phase 0 contracts implemented

1. `Command` / Intent model for API, CLI, human, and runtime instructions.
2. `CommitBatch` for multi-entity atomic commits.
3. Tenant-scoped idempotency keys.
4. Action-typed FSM edges.
5. Durable event log interface.
6. SQLite local store with CTL, command, event, inbox, outbox, projection, and effective-record tables.
7. Postgres schema draft for the production store.
8. Synchronous entity projection and effective-record update inside CTL commit.
9. App registry with versioned app/FSM/schema/policy surfaces.
10. Rideshare, travel, and JSSP apps using the same core/store/validator boundary.
11. Deterministic local runtime driver.
12. Reverse-topological compensation ordering helper.

## Acceptance test summary

- App conformance: rideshare, travel, and JSSP run with unchanged core.
- CommitBatch updates StateView synchronously.
- Idempotent CTL append by rid/op_id.
- Effective dependency rejection after compensation/supersession.
- Command/event/local runtime boundary.
- Compensation DAG order.

## Deferred to Phase 1

- Temporal RuntimeDriver.
- Async Postgres implementation.
- Worker pools for validator/inbox/outbox/projection.
- Continue-As-New policy.
- Full compensation execution.
- External provider adapters.
