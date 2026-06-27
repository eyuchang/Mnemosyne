# Mnemosyne / ALAS Architecture Status

This document summarizes the current implementation status of Mnemosyne / ALAS from small local correctness components to larger production-scale architecture.

It complements `DEVELOPMENT_LOG.md`.

- `DEVELOPMENT_LOG.md` records chronological implementation progress.
- This document records architectural position, integration boundaries, and what remains to be connected.

---

## 1. Current architectural center

The current system is built around a local correctness kernel.

The core path is:

`CommitBatch -> Validator -> Store -> CTL -> StateView`

The key source-of-truth contract is:

- CTL/store owns committed domain truth.
- StateView owns current effective truth.
- Event inbox is the external-event dedupe boundary.
- Event log records observed causes.
- Outbox is the external side-effect boundary.
- Runtime drivers orchestrate only.
- Benchmark fixtures provide scenarios but do not own truth.
- Solvers propose plans but do not own truth.

This separation is intentional. The project first establishes a visible, auditable correctness kernel before connecting industrial solvers, workflow engines, cloud services, or provider APIs.

---

## 2. What is currently custom-built

The following are currently implemented directly in the repository.

### 2.1 Transaction kernel

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

### 2.2 Temporal boundary

Temporal is not yet a production runtime dependency.

Current Temporal-related implementation includes:

- optional dependency guard;
- fake Temporal client;
- `TemporalClientLike` protocol;
- `TemporalRuntimeDriver`;
- activity-like boundary for durable Mnemosyne operations.

Current rule:

`Temporal workflow/runtime orchestration -> activity boundary -> Validator -> Store.commit_batch -> StateView`

Temporal remains orchestration only. It does not own domain truth.

No real Temporal workers, Temporal server, or Temporal cloud deployment is currently required for the local path.

### 2.3 Benchmark runner

The REALM-style benchmark path is implemented locally.

Current path:

`fixture JSON -> BenchmarkCase -> CommitBatch -> Validator -> Store -> StateView -> BenchmarkRunResult -> JSONL`

The benchmark runner can:

- load local fixture JSON;
- run one or more cases;
- collect metrics;
- emit JSONL;
- represent positive and expected-negative cases;
- include family-specific oracle details for P1-compatible Campus Tour cases.

Benchmark results report observed outcomes. They do not become domain truth.

### 2.4 P1-compatible Campus Tour solver

The current P1B solver is custom-built.

It is a small deterministic brute-force solver over required visit locations.

It currently handles:

- required visit locations;
- travel times;
- visit durations;
- time windows;
- deadline;
- visit-order constraints compatible with `CampusTourFSM`;
- conversion of solver output into a `BenchmarkCase`.

Current P1B route:

`S -> D -> A -> B -> L -> S`

Current P1B timing:

- start time: `09:00`
- finish time: `12:10`
- travel minutes: `70`
- visit minutes: `120`
- total minutes: `190`

This is a local P1-compatible solver boundary. It is not an official REALM-Bench score.

---

## 3. What is not yet integrated

The following categories are intentionally not yet integrated into the active correctness path.

### 3.1 OR solvers

No external OR solver is currently linked into the core benchmark-solving path.

Not currently used:

- OR-Tools CP-SAT
- OR-Tools routing solver
- MILP solvers
- CP solvers
- NetworkX optimization routines
- SciPy optimization
- commercial solvers

The current P1-compatible solver is a hand-written brute-force solver.

Future integration point:

`Solver protocol -> OR-Tools / CP-SAT / Routing / MILP adapter -> proposed plan -> Mnemosyne commit path`

The solver should propose. Mnemosyne should validate and commit.

### 3.2 External transaction-processing frameworks

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

### 3.3 Cloud management and distributed scalability

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

- Temporal workers behind the Temporal activity boundary;
- Postgres behind the Store protocol;
- outbox relay workers for side effects;
- provider adapters for airline/hotel/rideshare/calendar/email-like effects;
- deployment orchestration after local correctness and benchmark semantics are stable.

---

## 4. Current completion picture

Approximate current completion:

- local correctness kernel: `90%+`
- Stage 1 infrastructure: `75-80%`
- REALM local benchmark readiness: `55-60%`
- P1-compatible local benchmark: `65-70%`
- full production system: `30-35%`

The production percentage is lower because important deployment-scale components are not yet connected:

- Postgres store
- real Temporal SDK adapter
- real workers
- external provider APIs
- scalable outbox relay
- full benchmark suite
- official benchmark fixture alignment
- reporting and baseline comparison

This is expected. The project has intentionally built the correctness kernel before plugging in scale infrastructure.

---

## 5. Why this staged design matters

The project is following a small-to-large path.

### Small

Local correctness is established first:

- CTL records
- StateView
- compensation
- idempotency
- outbox
- benchmark replay
- P1-compatible local solver

### Medium

Adapter boundaries are added next:

- runtime driver protocol
- Temporal client boundary
- Temporal activity boundary
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

This prevents external infrastructure from obscuring the central research claim:

Mnemosyne / ALAS is about transactional memory, effective state, compensation, and controlled orchestration, not about delegating truth to a workflow engine or solver.

---

## 6. Near-term recommended next steps

Recommended next stages:

1. Add a human-readable benchmark report for P1A/P1B results.
2. Add a solver CLI path for P1B.
3. Add more P1-compatible fixtures.
4. Define a general solver protocol.
5. Add an OR-Tools adapter behind the solver protocol.
6. Add PostgresStore behind the Store protocol.
7. Add real Temporal SDK adapter behind the existing Temporal boundary.

The next immediate step should likely be:

`Stage 1.6R-P1B-REPORT`

Purpose:

Produce a Markdown or text benchmark report so results can be inspected without reading raw JSONL.
