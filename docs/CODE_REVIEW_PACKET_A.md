# Claude Review Packet A

## Review objective

This review covers the first meaningful Mnemosyne / ALAS architecture milestone after Stage 1.2.

The goal is to review the local correctness kernel, source-of-truth boundaries, optional Temporal boundary, long-horizon test policy, and REALM smoke-test adapter boundary.

The goal is not to ask Claude to redesign the system from scratch.

The reviewer should focus on correctness, architectural separation, failure modes, missing invariants, and whether the current tests actually support the intended claims.

---

## Milestone boundary

This packet covers:

- Stage 0 local correctness foundation
- Stage 1.0 runtime boundary preparation
- Stage 1.1 optional Temporal dependency guard
- long-horizon transaction policy and first opt-in test
- Stage 1.2 REALM smoke-test adapter boundary

---

## Completed in this milestone

### Core correctness kernel

Implemented:

- domain-independent core models
- `Command`
- `ExternalEvent`
- `TransitionCandidate`
- `CommitBatch`
- `CTLRecord`
- `OutboxIntent`
- `WorkflowHandle`
- `RuntimeStatus`
- `StateView`
- validator path over FSM and constraint registries

### Store foundation

Implemented:

- SQLite local durable store
- command log
- event log
- event inbox
- CTL records
- effective-record index
- state projection
- outbox table
- idempotent commit behavior
- batch atomicity
- StateView reconstruction
- entity history retrieval

### Runtime foundation

Implemented:

- `LocalRuntimeDriver`
- runtime protocol alignment tests
- local runtime end-to-end test
- `TemporalRuntimeDriver` stub
- Temporal SDK optional dependency guard
- Temporal import isolation tests

### Compensation and effectiveness foundation

Implemented:

- compensation metadata
- supersession/effectiveness projection
- ineffective dependency rejection
- compensated dependency behavior
- current StateView after correction

### Long-horizon foundation

Implemented:

- long-horizon test policy
- pytest marker policy
- optional test skip policy
- deterministic SQLite-only long-horizon transaction test

### REALM smoke-test foundation

Implemented:

- benchmark-neutral case models
- REALM-style adapter boundary
- conversion from benchmark case to `CommitBatch`
- local validator/store/StateView path
- simple benchmark metrics
- opt-in `realm` pytest marker
- deterministic SQLite-only REALM smoke test

Current benchmark path:

`REALM-style case -> CommitBatch -> Validator -> Store -> StateView -> metrics`

---

## Explicit non-goals for this review

The following are intentionally not implemented yet and should not be treated as defects unless they reveal a flaw in the current boundary design:

- functional Temporal adapter
- Temporal workers
- Temporal server integration
- Postgres store implementation
- database migrations
- worker-safe inbox claiming
- worker-safe outbox claiming
- external provider adapters
- OR-Tools integration
- LLM integration
- real compensation execution engine
- full REALM benchmark runner
- benchmark result serialization
- baseline comparison framework
- production deployment
- observability stack

---

## Source-of-truth contract

Please review whether the code preserves this contract:

- CTL is the source of truth for committed state.
- Event log is the source of truth for observed causes.
- Inbox is the external-event dedupe boundary.
- Outbox is the external side-effect boundary.
- StateView is the public API for current effective state.
- Runtime engines orchestrate workflows but do not own domain truth.
- Benchmark adapters provide scenarios but do not own domain truth.

This contract should remain true for:

- local runtime
- future Temporal runtime
- benchmark adapters
- long-horizon transaction tests

---

## Files to inspect first

Start with these files:

- `README.md`
- `PHASE0_CONTRACT.md`
- `DEVELOPMENT_LOG.md`
- `docs/PROJECT_STATUS.md`
- `docs/STAGE0_CLOSEOUT.md`
- `docs/STAGE1_PLAN.md`
- `docs/LONG_HORIZON_TEST_POLICY.md`
- `docs/CODE_REVIEW_PACKET_A.md`

Core:

- `mnemosyne/core/models/records.py`
- `mnemosyne/core/protocols/interfaces.py`
- `mnemosyne/core/validation.py`

Store:

- `mnemosyne/store/sqlite/store.py`
- `mnemosyne/store/postgres/schema.sql`

Runtime:

- `mnemosyne/runtime/local/driver.py`
- `mnemosyne/runtime/temporal/driver.py`
- `mnemosyne/runtime/temporal/dependency.py`

Benchmark adapter:

- `mnemosyne/benchmarks/models.py`
- `mnemosyne/benchmarks/realm.py`

Tests:

- `tests/conftest.py`
- `tests/core/`
- `tests/apps/`
- `tests/research/test_long_horizon_transactions.py`
- `tests/benchmarks/test_realm_smoke_boundary.py`

---

## Test commands and expected results

Default public suite:

`python -m pytest -q`

Expected current result:

`41 passed, 2 skipped`

The skipped tests are expected:

- `long_horizon`
- `realm`

Long-horizon opt-in suite:

`python -m pytest -q -m long_horizon`

Expected:

- long-horizon test passes
- non-selected tests are deselected or skipped

REALM opt-in smoke suite:

`python -m pytest -q -m realm`

Expected current result:

`1 passed, 42 deselected`

---

## Questions for Claude

Please answer these questions directly.

### 1. Source-of-truth separation

Does the implementation preserve the separation between CTL, event log, inbox, outbox, StateView, runtime drivers, and benchmark adapters?

Where is the separation strong?

Where is it weak?

### 2. CTL and StateView semantics

Does the current CTL and StateView implementation support the intended distinction between historical memory and current effective truth?

Are effectiveness, supersession, and compensation semantics coherent?

Are there cases where historical records might be lost, hidden, or incorrectly treated as current truth?

### 3. Idempotency and atomicity

Do the tests adequately verify idempotent commit behavior and batch atomicity?

Are there missing idempotency cases that should be added before Postgres or workers are implemented?

### 4. Inbox and outbox boundary

Does the inbox/outbox design correctly separate external event dedupe from external side-effect staging?

Are there any risks in the current local SQLite implementation that should be addressed before worker-safe versions are added?

### 5. Runtime boundary

Does `LocalRuntimeDriver` correctly behave as an orchestrator rather than a source of domain truth?

Does the `TemporalRuntimeDriver` stub and dependency guard create a good boundary for future Temporal integration?

Are there hidden assumptions that would make Temporal integration difficult later?

### 6. Benchmark boundary

Does the REALM smoke-test adapter boundary correctly treat benchmark cases as scenarios rather than domain truth?

Is the translation path from benchmark case to `CommitBatch` clean enough to extend?

Are the current metrics useful, or should the metric boundary be redesigned before adding more cases?

### 7. Long-horizon test quality

Does the first long-horizon test meaningfully stress the architecture?

Is it too synthetic?

What additional long-horizon cases should be added next?

### 8. Missing invariants

What invariants should be documented or enforced with tests before proceeding?

Examples might include:

- local log position monotonicity
- one latest StateView per entity/FSM
- ineffective records excluded from current truth
- compensated records remain historically visible
- outbox idempotency by provider key
- no runtime driver writes domain truth directly

### 9. Public release risk

If this repo were shown publicly as an early correctness kernel, what would be confusing, misleading, or under-documented?

What claims should be avoided until later stages?

### 10. Next engineering priority

After this review, what should be the next highest-priority engineering slice?

Suggested candidates:

- fake Temporal client boundary
- more REALM smoke cases
- benchmark result serialization
- Postgres implementation
- worker-safe outbox claiming
- compensation DAG execution

---

## Requested finding format

Please classify each finding as one of:

- Blocker
- Important
- Design question
- Nit
- Future work

For each finding, use this format:

```text
Finding:
Category:
Evidence:
Why it matters:
Recommended action: