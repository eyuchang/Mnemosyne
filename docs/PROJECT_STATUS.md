# Mnemosyne / ALAS Project Status

## Current checkpoint

The repository is clean and the local correctness kernel is passing.

Current verified state:

- default public test suite passes
- optional long-horizon test suite passes
- optional REALM smoke-test suite passes
- working tree clean after commit
- Stage 0 local correctness foundation complete
- Stage 1.0 runtime boundary preparation complete
- Stage 1.1 optional Temporal dependency guard complete
- Stage 1.2 REALM smoke-test adapter boundary complete

The project now has a stable local foundation for deterministic CTL, StateView, inbox/outbox, compensation, supersession, runtime-boundary, long-horizon, and REALM-style smoke tests.

---

## Current test commands

Default public test suite:

`python -m pytest -q`

Expected current result:

`41 passed, 2 skipped`

The skipped tests are expected because optional test groups are excluded from the default suite.

Long-horizon opt-in suite:

`python -m pytest -q -m long_horizon`

REALM opt-in smoke suite:

`python -m pytest -q -m realm`

Expected current REALM result:

`1 passed, 42 deselected`

The default suite remains fast, deterministic, local, and free of external services.

---

## Completed foundations

### Core model foundation

Implemented and tested:

- `Command`
- `ExternalEvent`
- `TransitionCandidate`
- `CommitBatch`
- `CTLRecord`
- `OutboxIntent`
- `WorkflowHandle`
- `RuntimeStatus`
- `StateView`

### Store foundation

Implemented and tested:

- SQLite local durable store
- command log
- event log
- event inbox
- CTL records
- effective-record index
- state projection
- outbox intent table
- idempotent commit behavior
- batch atomicity
- StateView reconstruction
- entity history retrieval

### Runtime foundation

Implemented and tested:

- `LocalRuntimeDriver`
- runtime protocol alignment
- local runtime end-to-end demo
- Temporal runtime stub
- Temporal dependency guard
- Temporal import isolation

### Compensation and supersession foundation

Implemented and tested:

- compensation metadata
- supersession/effectiveness projection
- ineffective dependency rejection
- compensated dependency behavior
- current StateView after correction

### Long-horizon foundation

Implemented and tested:

- long-horizon test policy
- pytest marker policy
- opt-in long-horizon test suite
- deterministic SQLite-only long-horizon transaction test

### REALM smoke-test foundation

Implemented and tested:

- benchmark-neutral case models
- REALM-style adapter boundary
- conversion from benchmark case to `CommitBatch`
- local validator/store/StateView path
- simple benchmark metrics
- opt-in `realm` pytest marker
- deterministic SQLite-only REALM smoke test

The current REALM smoke path is:

`REALM-style case -> CommitBatch -> Validator -> Store -> StateView -> metrics`

---

## Source-of-truth contract

The project has hardened the following source-of-truth contract:

- CTL is the source of truth for committed state.
- Event log is the source of truth for observed causes.
- Inbox is the external-event dedupe boundary.
- Outbox is the external side-effect boundary.
- StateView is the public API for current effective state.
- Runtime engines orchestrate workflows but do not own domain truth.
- Benchmark adapters provide scenarios but do not own domain truth.

This contract applies to the current local runtime, the future Temporal runtime, and the benchmark adapter path.

---

## Current architectural status

The repository is currently best described as:

A local, deterministic Mnemosyne / ALAS correctness kernel with durable CTL, event memory, inbox/outbox boundaries, StateView projection, compensation/supersession representation, store protocol alignment, runtime protocol alignment, opt-in long-horizon validation, and an opt-in REALM smoke-test adapter boundary.

It is not production-ready yet.

Production readiness still requires:

- functional Temporal adapter
- production Postgres store implementation
- migrations
- worker-safe inbox processing
- worker-safe outbox claiming
- provider adapters
- real compensation execution
- observability
- deployment documentation
- integration and stress tests
- complete benchmark runner support
- benchmark result serialization
- baseline comparison format

---

## REALM benchmark readiness

The project can now run small local REALM-style smoke cases.

The current REALM path is intentionally limited:

- local
- deterministic
- SQLite-only
- no Temporal server
- no LLM API
- no external provider API
- no full benchmark-wide claims yet

The current REALM smoke boundary validates that a benchmark-style scenario can be translated into Mnemosyne transactions and evaluated through CTL, StateView, outbox rows, and effectiveness metrics.

This is enough for early smoke testing.

It is not yet enough for serious benchmark claims.

---

## When to run REALM smoke cases

Initial REALM smoke cases can now be run with:

`python -m pytest -q -m realm`

Appropriate current use:

- verify adapter correctness
- test transaction translation
- test compensation/supersession behavior
- test StateView after benchmark-style transitions
- test simple metrics extraction
- prepare examples for book/research discussion

Inappropriate current use:

- full REALM benchmark claims
- performance claims
- comparison against published baselines
- distributed runtime claims
- Temporal orchestration claims
- LLM planning claims

---

## When to run serious REALM benchmark cases

Serious REALM benchmark runs should wait until after:

- benchmark adapter boundary is stable
- more case fixtures are added
- metrics are clearly defined
- result serialization is implemented
- baseline comparison format is defined
- benchmark runner CLI is available
- long-horizon and compensation tests remain green
- Claude Review Packet A findings are addressed

Temporal is not required for the first REALM benchmark smoke tests.

Temporal becomes relevant later when testing:

- long-running workflow orchestration
- signal handling
- retries
- timers
- worker recovery
- Continue-As-New policy
- distributed runtime behavior

---

## Review readiness

The project is now ready for the first external code review after Stage 1.2.

Recommended review:

### Claude Review Packet A

Scope:

- Stage 0 local correctness foundation
- Stage 1.1 optional Temporal boundary
- long-horizon transaction policy and test
- Stage 1.2 REALM smoke-test adapter boundary

Review focus:

- source-of-truth separation
- CTL/store correctness
- StateView semantics
- idempotency behavior
- effectiveness and supersession semantics
- compensation representation
- outbox side-effect boundary
- runtime protocol boundary
- Temporal isolation
- benchmark adapter boundary
- long-horizon test meaningfulness

The review should classify findings as:

- blocker
- important
- design question
- nit
- future work

---

## Recommended next milestone

Proceed to:

### Claude Review Packet A

Before starting the next engineering slice, prepare a focused code-review package for Claude.

The package should include:

- milestone boundary
- current status
- source-of-truth contract
- files to inspect first
- test commands and expected results
- known non-goals
- specific review questions
- red flags to search for

After Review Packet A is prepared, continue with the next engineering slice.

## Review A remediation status

Review A correctness remediation is complete on branch `review-a-claude-fixes`.

The remediation hardened the core correctness kernel around compensation, projection, idempotency, history APIs, and outbox-only batches.

Current verified results:

- Default suite: `51 passed, 2 skipped`
- Long-horizon suite: `1 passed, 52 deselected`
- REALM suite: `1 passed, 52 deselected`

The compensation policy is currently fail-closed:

- compensation targets must already exist;
- compensation targets must be effective;
- compensation must not orphan effective dependents;
- compensation must not break the effective state chain;
- every affected entity projection must be refreshed.

The history API now separates:

- full append-only entity history;
- current effective entity history.

The idempotency contract now treats `op_id` as the logical operation boundary.

--- 6/20/2026
Stage 1.2R complete — Review A correctness remediation merged

## Stage 1.3 status

Stage 1.3 fake Temporal client boundary is complete.

The runtime layer now supports an injected `TemporalClientLike` client. This allows `TemporalRuntimeDriver` to be tested locally with `FakeTemporalClient` while preserving the optional dependency guard for future real Temporal integration.

Current verified results:

- Default suite: `53 passed, 2 skipped`
- Long-horizon suite: `1 passed, 54 deselected`
- REALM suite: `1 passed, 54 deselected`

The fake Temporal client is intentionally orchestration-only. It does not expose `commit_batch`, `get_state_view`, `append_event`, or `enqueue_outbox`.

The source-of-truth contract remains:

- Temporal orchestrates workflows.
- CTL/store remains domain truth.
- StateView remains current effective truth.
- Outbox remains the external side-effect boundary.

Next expected Temporal work:

- define real temporalio-backed client adapter;
- enforce that store writes happen only through activity-like boundaries;
- keep workflow code deterministic and free of direct store mutation.

## Stage 1.5R status

Stage 1.5R REALM benchmark runner readiness is complete.

The benchmark layer now supports local deterministic execution of multiple REALM-style fixture files.

Current path:

`REALM fixture JSON -> BenchmarkCase -> CommitBatch -> Validator -> Store -> StateView -> BenchmarkRunResult -> JSON/JSONL`

Implemented components:

- benchmark result model;
- JSON/JSONL serialization helpers;
- single-case fixture loader;
- multi-case fixture loader;
- single-case REALM runner;
- multi-case REALM runner;
- local deterministic REALM fixture directory;
- two initial REALM-style fixtures.

Current fixture directory:

`benchmarks/realm/cases`

Current fixtures:

- `realm_smoke_confirm_001.json`
- `realm_smoke_correction_001.json`

The REALM runner remains opt-in through the `realm` pytest marker.

The benchmark runner is still local and deterministic. It does not require Temporal, Postgres, OR-Tools, LLM APIs, or external provider APIs.

This is sufficient for early local REALM-style fixture expansion, but not yet sufficient for publishable benchmark claims.

Remaining work before serious benchmark claims:

- add broader fixture coverage;
- define benchmark oracle format;
- define pass/fail metric contract;
- add result file output command;
- add summary report generation;
- add baseline comparison format;
- decide which REALM cases are representable in the current local model.

## Stage 1.6R-P1A status

Stage 1.6R-P1A REALM P1 Campus Tour oracle fixture is complete.

The project now has a P1-compatible Campus Tour fixture and can replay the supplied oracle trace through the Mnemosyne correctness kernel.

Current P1A result:

- cases run: `1`
- passed: `1`
- failed: `0`
- final state: `completed`
- total CTL records: `5`
- effective records: `5`
- ineffective records: `0`
- state version: `5`

This is an oracle-trace replay result, not a solver result.

Next P1 stage:

- P1B: derive the route from Campus Tour constraints using a planner/solver, then commit the discovered plan through Mnemosyne.

## Stage 1.6R-P1A-Verified status

Stage 1.6R-P1A-Verified is complete.

P1-compatible Campus Tour benchmark execution is now feasibility-gated inside the REALM runner.

The benchmark runner now distinguishes:

- feasible positive cases that should commit;
- infeasible expected-negative cases that should be rejected before commit.

Current P1-compatible local fixtures:

- `local-p1-compatible-campus-tour-static-001`
- `local-p1-compatible-campus-tour-time-window-violation-001`

Current P1A-Verified command:

`python -m mnemosyne.benchmarks.realm_runner --cases benchmarks/realm/p1 --out results/realm/p1_campus_tour_static_001.jsonl`

Current P1A-Verified result:

- cases run: `2`
- passed: `2`
- failed: `0`

Positive fixture result:

- feasible: `true`
- committed: `true`
- route: `S -> D -> A -> B -> L -> S`
- finish time: `12:10`
- total minutes: `190`
- final state: `completed`
- total records: `5`

Negative fixture result:

- feasible: `false`
- committed: `false`
- rejected before commit as expected
- violation: `TIME_WINDOW_EARLY:L:arrive=09:10:not_before=10:00`
- metrics: `null`

The P1-compatible fixtures are local and not official REALM-Bench scores.

They are marked with:

- `official_realm_bench: false`
- `benchmark_family: REALM-Bench-compatible-local`
- explicit provenance notes

This stage addresses Claude's P1A review findings by ensuring that feasibility and expected-negative behavior are part of the benchmark verdict, not merely side tests.

Next stage:

P1B — add a planner/solver boundary that derives the Campus Tour route from constraints before committing the discovered plan.

## Stage 1.6R-P1B status

Stage 1.6R-P1B Campus Tour solver boundary is complete.

The project now has a local deterministic solver for the P1-compatible Campus Tour fixture.

This stage demonstrates:

`constraints -> solver-derived route -> BenchmarkCase -> CommitBatch -> Validator -> Store -> CTL -> StateView -> result`

Current solver-derived route:

`S -> D -> A -> B -> L -> S`

Current solver-derived timing:

* start time: `09:00`
* finish time: `12:10`
* deadline: `17:00`
* travel minutes: `70`
* visit minutes: `120`
* total minutes: `190`

The solver respects:

* required visit locations;
* travel times;
* visit durations;
* time-window constraints;
* deadline constraint;
* FSM-compatible visit-order constraints.

The solver boundary preserves Mnemosyne’s source-of-truth contract:

* the solver proposes a route;
* Mnemosyne validates and commits the resulting plan;
* CTL/store remains committed domain truth;
* StateView remains current effective truth;
* benchmark results report observed outcomes but do not become truth.

This is stronger than P1A oracle replay because the route is now derived from constraints.

This remains a local P1-compatible fixture and not an official REALM-Bench score.

Next recommended step:

Add either a solver CLI/report path or a human-readable benchmark report so P1A/P1B results can be inspected without reading raw JSONL.


## R2.0 status — Solver protocol and certified proposal boundary

R2.0 is complete.

The project now has a general solver protocol and a solver-certificate data model.

Core path:

`Benchmark problem -> BenchmarkSolver -> SolverResult -> PlanProposal -> BenchmarkCase -> Mnemosyne commit -> JSONL -> Markdown report`

Implemented components:

- `SolverCertificate`
- `PlanProposal`
- `SolverResult`
- `BenchmarkSolver`
- `P1CampusTourSolverAdapter`

The P1 Campus Tour solver is now an adapter behind the general solver protocol.

Current P1 solver certificate:

- solver ID: `p1_campus_tour_bruteforce`
- solver version: `0.1`
- solver run ID: `solver-run:local-p1-compatible-campus-tour-solver-001`
- feasible: `true`
- optimality status: `optimal_for_enumerated_space`
- objective: `minimize_total_minutes = 190`
- route: `S -> D -> A -> B -> L -> S`
- finish time: `12:10`
- total minutes: `190`

The Markdown benchmark report now includes the solver certificate and plan proposal.

R2.0 establishes the following architectural rule:

Solvers may propose certified plans, but Mnemosyne remains the commit authority.

R2.0 is still local and dependency-free. External optimizer integration is deferred to R2.1.

## R2.1 status — Solver registry and selectable solver backend

R2.1 is complete.

The project now has a solver registry and selectable solver backend.

Current CLI path:

`python -m mnemosyne.benchmarks.p1_solver_runner --cases benchmarks/realm/p1_solver --solver p1-bruteforce --out results/realm/p1_campus_tour_solver_001.jsonl`

Current registered solver:

- solver name: `p1-bruteforce`
- solver adapter: `P1CampusTourSolverAdapter`
- solver ID: `p1_campus_tour_bruteforce`
- solver version: `0.1`

R2.1 establishes the following architectural rule:

Solver backends are selectable and pluggable, but all solver outputs remain certified proposals until admitted through Mnemosyne validation and commit.

R2.1 prepares the system for R2.2/R2.3 external optimizer adapters.

## R2.2 status — Proposal conflict semantics

R2.2 is complete.

The project now detects active proposal conflicts before commit admission.

Core path:

`solver proposals -> proposal conflict preflight -> Mnemosyne validation -> CTL commit -> StateView`

Implemented components:

- `ProposalConflict`
- `ProposalConflictReport`
- `detect_proposal_conflicts`
- `assert_no_proposal_conflicts`
- runner-level proposal conflict preflight

Current conflict rules:

- duplicate proposal IDs conflict;
- same tenant + same entity + different proposal IDs conflict;
- different tenants do not conflict;
- different entities do not conflict at this layer.

R2.2 establishes the following architectural rule:

A certified solver proposal is not automatically admissible. It must also be conflict-free with respect to active proposals.

This directly addresses concurrent or competing agent/solver proposals.

## R2.3 status — Stale-world reconciliation

R2.3 is complete.

The project now reconciles proposal world assumptions against observed world facts before commit admission.

Core path:

`solver proposal -> proposal conflict preflight -> world reconciliation preflight -> Mnemosyne validation -> CTL commit -> StateView`

Implemented components:

- `WorldAssumption`
- `ObservedWorldFact`
- `WorldReconciliationIssue`
- `WorldReconciliationReport`
- `extract_world_assumptions`
- `load_world_snapshot`
- `reconcile_world`
- `assert_world_reconciled`
- `--world-snapshot` runner option

The P1 solver proposal now carries a deadline world assumption.

A stale world snapshot rejects the proposal before commit.

R2.3 establishes the following architectural rule:

A certified and conflict-free solver proposal is still not admissible if its world assumptions disagree with the currently observed world.
