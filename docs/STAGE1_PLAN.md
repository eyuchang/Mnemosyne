# Mnemosyne / ALAS Stage 1 Plan

Stage 1 introduces runtime orchestration while preserving the Stage 0 correctness contract.

The main goal is to prepare for Temporal integration without allowing Temporal, or any runtime engine, to become the source of domain truth.

---

## 1. Stage 1 objective

Stage 1 adds a production-grade runtime orchestration path behind the existing `RuntimeDriver` protocol.

The guiding principle is:

```text
Runtime engines orchestrate.
CTL/store remains domain truth.
Event log remains observed-cause truth.
Outbox remains the side-effect boundary.
```

Stage 1 should therefore add Temporal incrementally, behind an adapter, without changing the core CTL model, store model, event model, or StateView contract.

---

## 2. Current Stage 0 foundation

Stage 0 closed with the following local correctness kernel:

```text
Command
→ inbox event
→ event log
→ CTL commit
→ StateView
→ outbox
```

Stage 0 also verified:

* `SQLiteStore` satisfies the formal `Store` protocol.
* `LocalRuntimeDriver` satisfies the formal `RuntimeDriver` protocol.
* `CommitBatch` is atomic.
* Compensation and supersession preserve CTL history while updating effective projection.
* `get_state_view(...)` exposes current effective state through a public API.
* Local runtime can submit workflows, receive signals, and coordinate with durable store truth.

At the beginning of Stage 1, the test suite passes:

```text
27 passed
```

---

## 3. Runtime source-of-truth rule

Temporal must not become domain truth.

Temporal may know:

* workflow id;
* run id;
* workflow status;
* signals received;
* activity progress;
* retry status;
* timer status;
* orchestration metadata.

Temporal must not be the canonical source of:

* committed domain state;
* effective entity state;
* business transition history;
* compensation truth;
* external-event truth;
* side-effect execution truth.

Those remain in:

```text
CTL
event_log
event_inbox
entity_projection / StateView
outbox
```

---

## 4. RuntimeDriver contract

The formal runtime boundary is:

```python
submit_workflow(...)
signal_disruption(...)
query_status(...)
```

Stage 1 must preserve this contract.

Current implementation:

```text
LocalRuntimeDriver
```

Future implementation:

```text
TemporalRuntimeDriver
```

Both should satisfy the same `RuntimeDriver` protocol.

This allows the system to switch orchestration engines without rewriting domain logic.

---

## 5. Stage 1 non-goals

Stage 1 should not introduce unnecessary coupling.

The following are not Stage 1 goals:

* rewrite CTL;
* rewrite `StateView`;
* move domain state into Temporal workflow memory;
* make Temporal history the source of domain truth;
* call external providers directly inside CTL commit;
* introduce LLM planning;
* introduce OR-Tools;
* implement full production Postgres concurrency;
* implement full deployment infrastructure.

Those belong to later stages.

---

## 6. Stage 1 implementation sequence

Stage 1 should proceed in small slices.

---

### Stage 1.0.1 — Runtime protocol alignment

Status:

```text
Complete
```

Commit:

```text
8547fc0 Add runtime protocol alignment tests
```

Verified:

* `RuntimeDriver` declares:

  * `submit_workflow(...)`
  * `signal_disruption(...)`
  * `query_status(...)`
* `LocalRuntimeDriver` exposes those APIs as async methods.
* Local runtime can submit, signal, and query a workflow.

---

### Stage 1.0.2 — Stage 1 plan

Status:

```text
In progress
```

Purpose:

Create this document before adding Temporal dependency.

Completion criteria:

* `docs/STAGE1_PLAN.md` exists.
* It states the runtime/source-of-truth boundary.
* It defines what Temporal may and may not own.
* Full tests pass.
* Repo is clean.

---

### Stage 1.0.3 — Temporal adapter skeleton, no Temporal dependency

Purpose:

Add the package/file structure for a future Temporal runtime adapter without installing Temporal yet.

Proposed files:

```text
mnemosyne/runtime/temporal/__init__.py
mnemosyne/runtime/temporal/driver.py
tests/core/test_temporal_runtime_stub.py
```

Initial behavior:

* `TemporalRuntimeDriver` class exists.
* It implements the same methods as `RuntimeDriver`.
* Methods raise `NotImplementedError` with clear messages.
* No Temporal package import is required yet.
* Tests verify the class shape and intentional not-yet-implemented behavior.

Reason:

This lets us lock the architectural boundary before introducing an external runtime dependency.

---

### Stage 1.0.4 — Runtime parity tests

Purpose:

Create tests that define expected runtime behavior independent of the runtime engine.

Target behavior:

```text
submit workflow
→ query submitted status
→ signal event
→ query signaled status
```

The same behavioral expectations should apply to:

* `LocalRuntimeDriver`
* future `TemporalRuntimeDriver`

During the stub stage, these tests may apply only to `LocalRuntimeDriver`, with placeholders documenting Temporal parity requirements.

---

### Stage 1.1 — Add Temporal dependency

Purpose:

Introduce Temporal only after the adapter skeleton and protocol tests are stable.

Expected dependency:

```text
temporalio
```

Rules:

* Temporal imports should remain isolated under `mnemosyne/runtime/temporal/`.
* Core models must not import Temporal.
* Store models must not import Temporal.
* App models must not import Temporal.
* Tests requiring Temporal should be separable from pure unit tests.

Potential test markers:

```text
unit
integration
temporal
```

Stage 1.1 should avoid requiring a running Temporal server for all tests.

---

### Stage 1.2 — Temporal local integration

Purpose:

Run a minimal Temporal workflow locally.

The workflow should demonstrate orchestration only:

```text
Temporal workflow starts
→ receives signal
→ calls activity or adapter boundary
→ durable domain truth remains in store/CTL
```

The Temporal workflow should not store canonical business state internally.

Expected local requirements:

* Temporal dev server or local Temporal service.
* Clear setup instructions.
* Integration tests separated from standard unit tests.

---

### Stage 1.3 — Temporal-to-store bridge

Purpose:

Connect Temporal orchestration to the Stage 0 store truth model.

Target flow:

```text
Temporal workflow receives command/signal
→ records event/inbox as needed
→ invokes validator/planner boundary
→ creates CommitBatch
→ commits to Store
→ reads StateView
→ schedules outbox processing
```

Important:

Temporal should orchestrate these calls but should not replace them.

---

### Stage 1.4 — Failure and retry semantics

Purpose:

Define how Temporal retries interact with store idempotency.

Key requirements:

* command idempotency remains tenant-scoped;
* inbox dedupe remains tenant/source/dedupe_key-scoped;
* event log dedupe remains tenant/event_id-scoped;
* CTL idempotency remains tenant/rid and tenant/op_id-scoped;
* outbox idempotency remains tenant/provider/provider_idempotency_key-scoped.

Temporal retries should be safe because the store APIs are idempotent.

---

### Stage 1.5 — Stage 1 closeout

Stage 1 is complete when:

* `TemporalRuntimeDriver` exists.
* Runtime protocol parity is tested.
* Temporal dependency is isolated.
* At least one local Temporal workflow can run.
* Temporal workflow can coordinate with the Store without becoming domain truth.
* Standard unit tests remain fast and local.
* Temporal integration tests are clearly separated.
* Documentation explains how to run Temporal tests.
* Repo is clean.

---

## 7. Proposed Stage 1 file layout

```text
mnemosyne/runtime/
  __init__.py
  protocols.py
  local/
    __init__.py
    driver.py
  temporal/
    __init__.py
    driver.py
    workflows.py
    activities.py

tests/core/
  test_runtime_protocol_alignment.py
  test_temporal_runtime_stub.py
  test_runtime_parity.py

tests/integration/
  test_temporal_local_workflow.py

docs/
  STAGE1_PLAN.md
  TEMPORAL_LOCAL_SETUP.md
```

The initial Temporal skeleton should start smaller than this. Add files only as needed.

---

## 8. Dependency policy

Stage 1 should use a strict dependency policy.

Allowed immediately:

```text
No new runtime dependency for Stage 1.0.3
```

Allowed after adapter boundary is documented:

```text
temporalio
```

Not yet allowed:

```text
OR-Tools
LLM APIs
external provider SDKs
Kafka
Redis
Celery
production Postgres driver
```

Those belong to later stages unless explicitly needed.

---

## 9. Testing policy

Standard test command:

```bash
python -m pytest -q
```

This command should remain:

* fast;
* local;
* deterministic;
* free of external services.

Temporal integration tests should not break the standard test command.

If needed, Temporal tests should be marked separately, for example:

```bash
python -m pytest -q -m temporal
```

or placed under:

```text
tests/integration/
```

---

## 10. Stage 1 risks

### Risk 1 — Temporal becomes domain truth

Mitigation:

Keep domain state in CTL and StateView. Temporal stores orchestration status only.

### Risk 2 — Core imports Temporal

Mitigation:

Only `mnemosyne/runtime/temporal/` may import Temporal packages.

### Risk 3 — Tests become slow or service-dependent

Mitigation:

Keep standard unit tests local. Separate Temporal integration tests.

### Risk 4 — Retry behavior duplicates domain commits

Mitigation:

Use existing idempotency contracts:

* command idempotency;
* inbox dedupe;
* event log dedupe;
* CTL rid/op_id uniqueness;
* outbox provider idempotency.

### Risk 5 — External side effects execute during commit

Mitigation:

Preserve outbox pattern. External effects are written as intents first and executed by later workers/adapters.

---

## 11. Stage 1 first coding step

The next coding step after this plan is:

```text
Stage 1.0.3 — Temporal adapter skeleton, no Temporal dependency
```

Add:

```text
mnemosyne/runtime/temporal/__init__.py
mnemosyne/runtime/temporal/driver.py
tests/core/test_temporal_runtime_stub.py
```

Expected behavior:

* `TemporalRuntimeDriver` exists.
* It exposes:

  * `submit_workflow(...)`
  * `signal_disruption(...)`
  * `query_status(...)`
* It raises `NotImplementedError` for now.
* It does not import Temporal yet.
* Full test suite still passes locally.

---

## 12. Stage 1 status

Current status:

```text
Stage 1.0.1 complete.
Stage 1.0.2 in progress.
Temporal not yet added.
Production runtime not yet added.
```

Stage 1 should proceed only after this plan is committed and the repo is clean.
