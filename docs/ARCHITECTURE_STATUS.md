# Mnemosyne / ALAS Architecture Status

This document summarizes the current implementation status of Mnemosyne / ALAS from local correctness kernel to product-scale runtime architecture.

It records architectural position, integration boundaries, and what remains to be connected.

---

## 1. Current architectural center

The current system is built around a local correctness kernel:

`CommitBatch -> Validator -> Store -> CTL -> StateView`

The source-of-truth contract is:

- CTL/store owns committed domain truth.
- StateView owns current effective truth.
- Event inbox is the external-event dedupe boundary.
- Event log records observed causes.
- Outbox is the external side-effect boundary.
- Runtime drivers orchestrate only.
- Temporal workflow code orchestrates only.
- Temporal activity boundaries perform durable work.
- Benchmark fixtures provide scenarios but do not own truth.
- Solvers propose plans but do not own truth.
- Recovery packages describe possible repair but do not own truth.

This separation is intentional. The project first establishes a visible, auditable correctness kernel before connecting industrial solvers, workflow engines, cloud services, or provider APIs.

---

## 2. Current verified milestone

Current milestone:

`R5.0: Product API and audit surface`

Completed product tags:

- `r4.5-active-commitments`
- `r4.6-runtime-active-recovery`
- `r4.7-recovery-proposal-packages`
- `r4.8-temporal-active-recovery-boundary`

Current full local suite:

`198 passed, 24 skipped`

---

## 3. Implemented architecture

### 3.1 Transaction kernel

The transaction kernel is custom-built.

Implemented pieces include:

- `CommitBatch`
- `TransitionCandidate`
- `CTLRecord`
- validator path
- SQLite-backed store
- CTL append
- StateView projection
- effective-history view
- full-history view
- compensation handling
- fail-closed compensation invariants
- `op_id` logical idempotency
- outbox staging
- inbox/event-log idempotency

Current backing store:

- Python standard-library SQLite via `sqlite3`

No external transaction-processing framework is currently used.

This is deliberate. The goal at this stage is to make the transactional memory semantics explicit and testable before introducing Postgres, distributed workers, or cloud infrastructure.

### 3.2 Active commitment memory

R4.5 added CTL-resident active commitments.

Implemented components:

- `ActiveCommitment`
- `CommitmentEvent`
- commitment lifecycle events
- commitment CTL serialization
- replay-derived active commitment index
- store-backed active commitment index
- recovery policy
- bounded recursive recovery loop
- recovery orchestration
- admission-boundary tests
- R4.5 active commitment recovery demo

Lifecycle states include:

- `live`
- `fired`
- `proposed`
- `admitted`
- `rejected`
- `discharged`
- `expired`

Core invariant:

A fired commitment may wake recovery, but it cannot mutate domain state directly.

Domain mutation requires separately admitted domain CTL records.

### 3.3 Runtime active recovery

R4.6 integrated active recovery into the local runtime layer.

Implemented components:

- `LocalActiveRecoveryExecutor`
- runtime planning from CTL-derived active commitment index
- commitment-FSM-only recovery execution
- admission-validated recovery execution through `Validator`
- commitment FSM helper and registry builder
- R4.6 validated runtime recovery demo

Core invariant:

Runtime recovery may update commitment state, but it may not mutate domain state directly.

### 3.4 Recovery proposal packages

R4.7 introduced first-class recovery proposal packages.

Implemented components:

- `RecoveryProposalPackage`
- proposal package serialization helpers
- package references in commitment event payloads
- package-backed commitment proposal candidates
- package admission-boundary tests
- R4.7 recovery proposal package demo

A proposal package may contain proposed domain `TransitionCandidate` objects, but those candidates are proposal material only.

They are not CTL records.

They are not effective state.

They are not domain truth.

Core invariant:

`package describes repair -> commitment proposal records package reference -> domain repair remains inert -> later domain admission may apply repair`

### 3.5 Temporal boundary

Temporal is not yet a production runtime dependency.

Current Temporal-related implementation includes:

- optional dependency guard
- fake Temporal client
- `TemporalClientLike` protocol
- `TemporalRuntimeDriver`
- activity-like boundary for durable Mnemosyne operations
- Temporal active recovery activity boundary

Current rule:

`Temporal workflow/runtime orchestration -> activity boundary -> Validator -> Store.commit_batch -> StateView`

Temporal remains orchestration only. It does not own domain truth.

No real Temporal workers, Temporal server, or Temporal cloud deployment is currently required for the local path.

### 3.6 Temporal active recovery boundary

R4.8 added:

- `plan_validate_and_commit_active_recovery_activity(...)`
- `ActiveRecoveryActivityResult`
- activity-safe active recovery summaries
- retry/idempotency tests
- validation-failure tests
- R4.8 Temporal active recovery demo

The activity performs:

1. load active commitments from CTL/store
2. plan bounded recovery for fired/rejected commitments
3. validate commitment-FSM recovery candidates
4. commit admitted commitment-FSM records
5. return deterministic summary data to workflow orchestration

The activity does not return store handles, CTL mutation authority, or domain repair authority.

Core invariant:

Temporal active recovery may update commitment state, but it may not mutate domain state directly.

### 3.7 Benchmark runner

The REALM-style benchmark path is implemented locally.

Current path:

`fixture JSON -> BenchmarkCase -> CommitBatch -> Validator -> Store -> StateView -> BenchmarkRunResult -> JSONL`

The benchmark runner can:

- load local fixture JSON
- run one or more cases
- collect metrics
- emit JSONL
- represent positive and expected-negative cases
- include family-specific oracle details for P1-compatible Campus Tour cases

Benchmark results report observed outcomes. They do not become domain truth.

### 3.8 Solver and proposal preflight path

The solver path is implemented locally and dependency-free.

Implemented components include:

- `SolverCertificate`
- `PlanProposal`
- `SolverResult`
- `BenchmarkSolver`
- P1 Campus Tour solver adapter
- solver registry
- proposal conflict preflight
- stale-world reconciliation preflight

Current architectural rule:

Solver backends may propose certified plans. Mnemosyne remains the commit authority.

A certified and conflict-free solver proposal is still not admissible if its world assumptions disagree with observed world facts.


### 3.9 Product API and audit surface

R5.0 adds the product-facing API layer:

- `mnemosyne.api.commitments`
- `mnemosyne.api.recovery`
- `mnemosyne.api.proposal_packages`
- `mnemosyne.api.audit`

The API layer wraps the internal R4.5-R4.8 machinery without changing the source-of-truth contract.

Product code should call `mnemosyne.api` rather than importing internal CTL, recovery, runtime, or package modules directly.

Core invariant:

    Application code -> mnemosyne.api -> Validator / Store / CTL / StateView

Audit APIs are read-only. Recovery APIs commit only commitment-FSM records. Proposal package APIs keep domain candidates inert unless separately admitted through the domain CTL path.

---

## 4. What is not yet integrated

The following categories are intentionally not yet integrated into the active production path.

### 4.1 OR solvers

No external OR solver is currently linked into the core benchmark-solving path.

Not currently used:

- OR-Tools CP-SAT
- OR-Tools routing solver
- MILP solvers
- CP solvers
- NetworkX optimization routines
- SciPy optimization
- commercial solvers

Future integration point:

`Solver protocol -> OR-Tools / CP-SAT / Routing / MILP adapter -> certified proposal -> proposal preflight -> Mnemosyne commit path`

The solver should propose. Mnemosyne should validate and commit.

### 4.2 External transaction-processing frameworks

No external transaction-processing framework is currently used.

Not currently used:

- distributed transaction manager
- workflow-as-transaction package
- event-sourcing framework
- CQRS framework
- cloud transaction orchestration framework

Current transaction substrate:

- custom Mnemosyne Store/Validator/CTL logic
- SQLite local persistence

Future integration point:

`Store protocol -> PostgresStore -> production persistence`

The production store should preserve the existing Store protocol and source-of-truth contract.

### 4.3 Cloud management and distributed scalability

No cloud management layer is currently connected.

Not currently used:

- managed Temporal Cloud
- Kubernetes deployment
- cloud SQL/Postgres
- Redis
- Kafka
- Celery
- cloud queues
- cloud functions
- external provider APIs

Future integration points:

- Temporal workers behind the Temporal activity boundary
- Postgres behind the Store protocol
- outbox relay workers for side effects
- provider adapters for airline/hotel/rideshare/calendar/email-like effects
- deployment orchestration after local correctness and benchmark semantics are stable

---

## 5. Current completion picture

Approximate current completion:

- local correctness kernel: `95%+`
- active commitment/recovery semantics: `85-90%`
- Temporal boundary readiness: `70-75%`
- REALM local benchmark readiness: `60-65%`
- P1-compatible local benchmark path: `75-80%`
- full production system: `40-45%`

The production percentage remains lower because important deployment-scale components are not yet connected:

- Postgres store
- real Temporal SDK adapter
- real workers
- external provider APIs
- scalable outbox relay
- full benchmark suite
- official benchmark fixture alignment
- reporting and baseline comparison
- observability and deployment documentation

This is expected. The project has intentionally built the correctness kernel and recovery semantics before plugging in scale infrastructure.

---

## 6. Why this staged design matters

The project is following a small-to-large path.

### Small

Local correctness is established first:

- CTL records
- StateView
- compensation
- idempotency
- outbox
- benchmark replay
- local solver protocol

### Medium

Adapter boundaries and recovery semantics are added next:

- runtime driver protocol
- Temporal client boundary
- Temporal activity boundary
- active commitments
- bounded recovery
- recovery proposal packages
- benchmark runner
- solver boundary

### Large

Production components should plug in later:

- OR solvers
- Postgres
- Temporal workers
- cloud deployment
- provider adapters
- long-horizon benchmark suites
- reporting and reproducibility artifacts
- audit/observability surfaces

This prevents external infrastructure from obscuring the central research claim:

Mnemosyne / ALAS is about transactional memory, effective state, compensation, controlled orchestration, and CTL-resident active memory, not about delegating truth to a workflow engine or solver.

---

## 7. Near-term recommended next steps

Recommended next stages:

1. Add product-facing APIs for commitments, recovery, proposal packages, and audit views.
2. Add active commitment audit reports.
3. Add human-readable recovery lineage reports.
4. Add a solver CLI/report path for broader P1 cases.
5. Add more P1-compatible fixtures.
6. Add an external OR-Tools adapter behind the solver protocol.
7. Add PostgresStore behind the Store protocol.
8. Add real Temporal SDK adapter behind the existing Temporal boundary.

The next immediate stage should likely be:

`R5.1 product reporting and CLI surface`

Purpose:

Expose stable product-facing APIs and audit views so applications can use active commitments, recovery planning, proposal packages, and recovery lineage without touching internal CTL/recovery modules directly.
