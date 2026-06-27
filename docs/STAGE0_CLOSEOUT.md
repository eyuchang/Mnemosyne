# Mnemosyne / ALAS Stage 0 Closeout

Stage 0 establishes the local correctness foundation for the Mnemosyne / ALAS production architecture.

This closeout records what has been implemented, what has been verified, what remains intentionally deferred, and what the next development stages should address.

---

## 1. Stage 0 objective

The objective of Stage 0 is to harden the local core before introducing distributed runtime, production SQL, optimization solvers, LLM planning, or external provider integrations.

The guiding principle is:

> Make the correctness contract local, deterministic, and testable before adding distributed complexity.

Stage 0 therefore focuses on the durable memory model:

* Command log
* External event inbox
* Event log
* Control Transition Ledger (CTL)
* Effective-record index
* Entity projection / StateView
* Outbox intent table
* Local runtime boundary
* Store protocol alignment

---

## 2. Source-of-truth contract

Stage 0 confirms the following source-of-truth separation:

### CTL

CTL is the source of truth for committed state.

It stores durable transition records and preserves historical memory.

### Event log

Event log is the source of truth for observed causes and non-commit decisions.

External facts, runtime signals, and provider observations are recorded here.

### Inbox

Inbox is the durable receiving surface for inbound external events.

It dedupes external retries by:

```text
tenant_id + source + dedupe_key
```

### Outbox

Outbox is the durable boundary for external side effects.

The system writes external-effect intents into the outbox rather than directly calling external APIs during CTL commit.

### Runtime

Runtime engines are orchestration mechanisms, not domain truth.

The current local runtime can submit workflows, receive signals, and report runtime status, but committed domain truth remains in CTL and StateView.

---

## 3. Implemented components

Stage 0 includes the following implementation surfaces.

### Core models

* `Command`
* `ExternalEvent`
* `TransitionCandidate`
* `CommitBatch`
* `CTLRecord`
* `OutboxIntent`
* `StateView`

### Store

Current implementation:

```text
SQLiteStore
```

Current runtime dependency:

```text
Python sqlite3
```

The SQLite store implements:

* `append_command(...)`
* `append_event(...)`
* `record_inbox_event(...)`
* `has_event(...)`
* `is_effective(...)`
* `get_latest_version(...)`
* `get_state_view(...)`
* `get_record(...)`
* `get_entity_history(...)`
* `enqueue_outbox(...)`
* `commit_batch(...)`

### Store protocol

The formal `Store` protocol now includes the Phase 0.1 APIs, including:

```text
record_inbox_event(...)
```

This gives the future `PostgresStore` a clear implementation target.

### Runtime

Current runtime implementation:

```text
LocalRuntimeDriver
```

It supports:

* `submit_workflow(...)`
* `signal_disruption(...)`
* `query_status(...)`

The local runtime is intentionally simple and deterministic.

### App registry and app skeletons

Current app skeletons include:

* Rideshare
* Travel
* JSSP

These apps share the same core/store/validator boundaries.

### Compensation support

Stage 0 supports compensation at the representation and projection level:

* CTL records can include `metadata["compensates"]`.
* CTL records can include `metadata["supersedes"]`.
* The effective-record index marks compensated or superseded records as ineffective.
* StateView is rebuilt from effective records only.
* CTL history remains preserved.

Full external compensation execution is deferred to later stages.

---

## 4. Verified behavior

Stage 0 verifies the following behavior through tests.

### Command logging

Commands are stored with tenant-scoped idempotency.

### Event inbox

Inbound external events are deduped by:

```text
tenant_id + source + dedupe_key
```

### Event log

External events are recorded idempotently by:

```text
tenant_id + event_id
```

### CommitBatch rollback atomicity

If a later record in a batch fails validation or version checks, no partial CTL, projection, effective-index, or outbox writes remain.

### CommitBatch success atomicity

A successful batch writes together:

* CTL records
* effective-record index updates
* entity projection updates
* outbox intents

### Outbox idempotency

Outbox intents are deduped by:

```text
tenant_id + provider + provider_idempotency_key
```

### Compensation and supersession

Compensation and supersession preserve CTL history while updating current effective projection.

### StateView API

The public `get_state_view(...)` API returns current effective state without requiring callers to inspect database tables.

### Protocol alignment

`SQLiteStore` satisfies the formal `Store` protocol.

### Local end-to-end persistence demo

The local persistence loop works:

```text
Command
→ inbox event
→ event log
→ CTL commit
→ StateView
→ outbox
```

### Local runtime end-to-end demo

The local runtime boundary works:

```text
LocalRuntimeDriver
→ workflow submission
→ signal handling
→ durable command/event/CTL/outbox store truth
→ StateView
```

---

## 5. Completed commits

The following commits form the Stage 0 hardening sequence:

```text
9508ce9  Add inbox dedupe support
66cd460  Add outbox intent idempotency tests
17a2e19  Add successful commit batch outbox test
5436daa  Add compensation projection tests
eaaeebc  Add StateView API contract tests
acf3b49  Align store protocol with Phase 0.1 APIs
e61329e  Add local end-to-end persistence demo
1834c30  Add local runtime driver end-to-end demo
```

---

## 6. Current dependency surface

Stage 0 intentionally avoids external runtime services.

### Runtime dependencies

* Python standard library
* SQLite through Python `sqlite3`

### Development and test dependencies

* `pytest`
* `pytest-asyncio`
* `ruff`
* `mypy`

### Not required in Stage 0

* Temporal
* Postgres server
* OR-Tools
* LLM APIs
* External provider APIs
* Redis
* Kafka
* Celery
* Docker services

---

## 7. Deferred work

The following items are intentionally deferred.

### Stage 1 — Temporal runtime

Add a `TemporalRuntimeDriver` while preserving the rule that runtime orchestration is not domain truth.

### Stage 2 — Production SQL store

Implement an async `PostgresStore` against the formal `Store` protocol.

Required work includes:

* migrations
* transaction semantics
* worker-safe inbox processing
* worker-safe outbox claiming
* production indexes
* concurrency tests

### Stage 3 — Domain app and solver integrations

Expand app-specific implementations for:

* Rideshare
* Travel
* JSSP
* OR-Tools / scheduling solvers

### Stage 4 — LLM planning and cognition

Add LLM-driven planning, critique, validation support, explanation, and policy reasoning.

### Stage 5 — Evaluation, observability, and packaging

Add:

* benchmark harnesses
* metrics
* tracing
* audit views
* packaging
* deployment documentation

---

## 8. Stage 0 closeout criteria

Stage 0 is considered closed when:

* the full test suite passes;
* `DEVELOPMENT_LOG.md` is updated;
* this closeout document is committed;
* `git status` is clean.

At closeout, the system should be described as:

```text
A local, deterministic Mnemosyne / ALAS correctness kernel with CTL, event memory, inbox/outbox durability, StateView projection, compensation representation, store protocol alignment, and local runtime boundary tests.
```

---

## 9. Status at closeout

Stage 0 status:

```text
Complete for local correctness foundation.
```

Production readiness status:

```text
Not production-ready yet.
```

Reason:

The core correctness model is now stable locally, but production operation still requires Temporal, Postgres, provider adapters, concurrency hardening, observability, and deployment work.
