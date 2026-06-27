# Mnemosyne Phase 0 / Stage 1 Scaffold

This repository contains the local correctness foundation for the ALAS / SagaLLM / Mnemosyne production build.

The current implementation pins the contracts needed before full Temporal, Postgres, OR-Tools, LLM, and external provider integrations are added.

The main design principle is:

Mnemosyne / ALAS preserves durable transactional memory while exposing a coherent current operational state.

---

## Current status

Stage 0 is closed.

Stage 1 runtime preparation has started.

Current implementation status:

- Stage 0 local correctness foundation: complete
- Stage 1.0 runtime boundary preparation: complete
- Stage 1.1 optional Temporal dependency guard: in progress
- Temporal runtime adapter: stubbed, not functional yet
- Production Postgres store: schema draft only
- OR-Tools / LLM / external provider integrations: not added yet

The standard local test suite is fast, deterministic, and does not require external services.

---

## What the current implementation includes

- Pure, domain-independent `mnemosyne/core/`
- First-class `Command`, `ExternalEvent`, `TransitionCandidate`, `CommitBatch`, `CTLRecord`, `OutboxIntent`, and `StateView` models
- Action-typed FSM registry
- Validator over log-grounded `StateView` and effective dependencies
- SQLite store for local/unit tests
- CTL, command, event, inbox, outbox, projection, and effective-record tables
- Postgres schema draft with tenant-scoped idempotency and production table shapes
- App registry plus rideshare, travel, and JSSP plug-ins
- Deterministic `LocalRuntimeDriver`
- Stubbed `TemporalRuntimeDriver`
- Store protocol alignment tests
- Runtime protocol alignment tests
- End-to-end local persistence tests
- Compensation and supersession projection tests
- Optional Temporal dependency policy and guards

---

## Source-of-truth contract

The system separates orchestration from domain truth.

The source-of-truth contract is:

- CTL is the source of truth for committed state.
- Event log is the source of truth for observed causes.
- Inbox is the external-event dedupe boundary.
- Outbox is the external side-effect boundary.
- StateView is the public API for current effective state.
- Runtime engines orchestrate workflows but do not own domain truth.

This rule applies to both the current local runtime and the future Temporal runtime.

---

## Local runtime

The current implementation runs locally without external services.

By default, the system uses:

- `SQLiteStore` for local durable state
- `LocalRuntimeDriver` for deterministic local workflow orchestration
- no external workflow server
- no Temporal dependency
- no Postgres server
- no external provider APIs

The local runtime is intended for deterministic development, testing, and contract hardening.

---

## Optional Temporal runtime support

Temporal support is planned as a future runtime option.

Temporal will be used only as an orchestration engine. It will not become the source of domain truth.

Temporal-specific code is isolated under:

`mnemosyne/runtime/temporal/`

The optional Temporal SDK dependency can be installed with:

`python -m pip install -e ".[temporal]"`

This is not required for the standard local test suite.

The standard test command remains:

`python -m pytest -q`

Current Temporal status:

- `TemporalRuntimeDriver` exists as a stub.
- It exposes the runtime API shape.
- It checks whether the Temporal SDK is installed.
- It raises a clear error if `temporalio` is missing.
- It still raises `NotImplementedError` for actual workflow operations because real Temporal integration has not been implemented yet.

Temporal integration tests will be added separately once the Temporal adapter becomes functional.

See:

`docs/STAGE1_PLAN.md`

---

## Long-horizon transaction tests

Mnemosyne / ALAS is designed to support long-horizon transactional memory.

Long-horizon tests exercise many-step CTL histories, compensation chains, supersession chains, StateView reconstruction, local-log ordering, and outbox/idempotency behavior.

These tests are important for:

- research validation
- book evidence
- stress testing
- benchmark design
- confidence in long-running planning scenarios

They are intentionally not part of the default public test run.

The default test command remains:

`python -m pytest -q`

Future long-horizon tests should be marked explicitly and run opt-in:

`python -m pytest -q -m long_horizon`

Policy:

- keep default tests fast, local, and deterministic
- keep long-horizon tests visible in the repository
- exclude long-horizon tests from default public test runs
- use long-horizon tests for research, book evidence, stress testing, and nightly validation

See:

`docs/LONG_HORIZON_TEST_POLICY.md`

---

## Testing

Run the standard local test suite:

`python -m pytest -q`

The standard suite should remain:

- fast
- deterministic
- local
- free of external services
- suitable for public release
- suitable for contributor smoke checks

The standard suite should not require:

- Temporal server
- Postgres server
- OR-Tools
- LLM APIs
- external provider APIs
- long-running stress tests

Optional future test groups may include:

- `long_horizon`
- `research`
- `temporal`
- `integration`
- `external`

---

## Development docs

Important design and planning documents:

- `docs/STAGE0_CLOSEOUT.md`
- `docs/STAGE1_PLAN.md`
- `docs/LONG_HORIZON_TEST_POLICY.md`
- `PHASE0_CONTRACT.md`
- `DEVELOPMENT_LOG.md`

---

## Architecture status

The repository is stable as a local correctness kernel.

It is not production-ready yet.

Production readiness still requires:

- functional Temporal adapter
- production Postgres store
- migrations
- worker-safe inbox processing
- worker-safe outbox claiming
- provider adapters
- real compensation execution
- observability
- deployment documentation
- integration and stress tests

The current implementation should be understood as:

A local, deterministic Mnemosyne / ALAS correctness kernel with CTL, event memory, inbox/outbox durability, StateView projection, compensation representation, store protocol alignment, and local runtime boundary tests.