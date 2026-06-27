# Mnemosyne / ALAS Project Status

## Current checkpoint

The repository is clean through the R5.1 product reporting and CLI surface milestone.

Current verified state:

- full local test suite passes
- working tree clean after commit
- R4.5 active commitment memory complete
- R4.6 runtime active recovery complete
- R4.7 recovery proposal packages complete
- R4.8 Temporal active recovery boundary complete
- R5.0 product API and audit surface complete
- R5.1 product reporting and CLI surface complete

Current full local suite:

`248 passed, 24 skipped`

Completed product milestone tags:

- `r4.5-active-commitments`
- `r4.6-runtime-active-recovery`
- `r4.7-recovery-proposal-packages`
- `r4.8-temporal-active-recovery-boundary`
- R5.0 branch milestone: product API and audit surface
- R5.1 branch milestone: product reporting and CLI surface

The project now has a stable local foundation for deterministic CTL, StateView, inbox/outbox, compensation, supersession, solver proposals, stale-world reconciliation, active commitments, runtime recovery, recovery proposal packages, and Temporal-safe active recovery boundaries, product-facing APIs for commitments, recovery, proposal packages, audit lineage, and product report export.

---

## Current architectural center

The core correctness path remains:

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

This contract applies to the local runtime, the future Temporal runtime, the benchmark path, the solver path, and the recovery path.

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
- full entity history retrieval
- effective entity history retrieval

### Runtime foundation

Implemented and tested:

- `LocalRuntimeDriver`
- runtime protocol alignment
- local runtime end-to-end demo
- Temporal runtime stub
- Temporal dependency guard
- Temporal import isolation
- fake Temporal client boundary
- Temporal activity boundary for durable commit operations

### Compensation and supersession foundation

Implemented and tested:

- compensation metadata
- supersession/effectiveness projection
- ineffective dependency rejection
- compensated dependency behavior
- fail-closed compensation invariants
- current StateView after correction

### Active commitment foundation

R4.5 added CTL-resident active commitments.

Implemented and tested:

- `ActiveCommitment`
- `CommitmentEvent`
- active commitment lifecycle states
- CTL serialization through extension fields
- replay-derived active commitment index
- store-backed active commitment index
- recovery policy
- bounded recursive recovery loop
- recovery orchestration
- active commitment recovery demo

Core rule:

Active commitments are durable CTL-resident obligations. A fired commitment may wake recovery, but it may not mutate domain state directly.

### Runtime active recovery foundation

R4.6 added runtime-level active recovery.

Implemented and tested:

- `LocalActiveRecoveryExecutor`
- runtime planning from CTL-derived active commitment index
- commitment-FSM-only recovery execution
- admission-validated recovery execution through `Validator`
- commitment FSM helper and registry builder
- validated runtime recovery demo

Core rule:

Runtime recovery may update commitment state, but it may not mutate domain state directly.

### Recovery proposal package foundation

R4.7 added first-class recovery proposal packages.

Implemented and tested:

- `RecoveryProposalPackage`
- package serialization helpers
- package references in commitment event payloads
- package-backed commitment proposal candidates
- admission-boundary tests
- recovery proposal package demo

Core rule:

A recovery proposal package may contain proposed domain candidates, but those candidates are not committed truth. Domain state changes still require separately admitted domain CTL records.

### Temporal active recovery boundary

R4.8 added a Temporal-style active recovery activity boundary.

Implemented and tested:

- Temporal active recovery activity boundary
- `ActiveRecoveryActivityResult`
- activity-safe active recovery summaries
- commitment-FSM-only recovery commits through activity boundary
- validation and CTL commit behind activity boundary
- retry/idempotency tests
- validation-failure tests
- Temporal active recovery demo

Core rule:

Temporal workflow code remains orchestration-only. Active recovery planning, validation, and CTL commit happen through an activity boundary.

Temporal active recovery may update commitment state, but it may not mutate domain state directly.

---

## Benchmark and solver readiness

The local deterministic benchmark and solver path is implemented.

Current benchmark path:

`fixture JSON -> BenchmarkCase -> CommitBatch -> Validator -> Store -> StateView -> BenchmarkRunResult -> JSONL`

Implemented components:

- benchmark-neutral case models
- REALM-style adapter boundary
- JSON/JSONL result serialization
- local deterministic fixture directory
- positive and expected-negative fixture support
- P1-compatible Campus Tour fixtures
- feasibility-gated benchmark execution
- Markdown benchmark report support

Current solver path:

`constraints -> solver-derived route -> certified proposal -> BenchmarkCase -> Mnemosyne commit path`

Implemented components:

- `SolverCertificate`
- `PlanProposal`
- `SolverResult`
- `BenchmarkSolver`
- P1 Campus Tour brute-force solver adapter
- solver registry
- selectable solver backend
- proposal conflict preflight
- stale-world reconciliation preflight

Current architectural rule:

Solvers may propose certified plans, but Mnemosyne remains the commit authority.

A certified and conflict-free solver proposal is still not admissible if its world assumptions disagree with currently observed world facts.

---

## Current architectural status

The repository is currently best described as:

A local, deterministic Mnemosyne / ALAS product kernel with durable CTL, event memory, inbox/outbox boundaries, StateView projection, compensation/supersession representation, solver proposal preflight, stale-world reconciliation, CTL-resident active commitment memory, validated runtime recovery, inert recovery proposal packages, and Temporal-safe active recovery activity boundaries.

It is not production-deployed yet.

Production readiness still requires:

- real Temporal SDK adapter
- real Temporal workers
- production Postgres store implementation
- migrations
- worker-safe inbox processing
- worker-safe outbox claiming
- provider adapters
- real compensation execution
- observability and audit reports
- deployment documentation
- integration and stress tests
- external OR solver adapters
- complete benchmark suite support
- official benchmark fixture alignment
- baseline comparison format

---

## What is still intentionally local

The current implementation remains local and deterministic.

It does not require:

- Temporal server
- Temporal Cloud
- Postgres
- Redis
- Kafka
- Kubernetes
- LLM APIs
- external provider APIs
- OR-Tools
- commercial solvers

This is intentional. The project has built the correctness kernel and recovery semantics before adding scale infrastructure.

---

## Current completion picture

Approximate current completion:

- local correctness kernel: `95%+`
- active commitment and recovery semantics: `85-90%`
- Temporal boundary readiness: `70-75%`
- REALM local benchmark readiness: `60-65%`
- P1-compatible local benchmark path: `75-80%`
- full production system: `40-45%`

The production percentage remains lower because deployment-scale components are not yet connected.

---

## Recommended next milestone

Proceed to:

### R6.0 — Disruptive planning benchmark layer

Purpose:

Expose stable product-facing APIs and audit views so applications can use active commitments, recovery planning, proposal packages, and recovery lineage without touching internal CTL/recovery modules directly.

Recommended near-term tasks:

1. Add product-facing APIs for commitments.
2. Add product-facing APIs for recovery.
3. Add product-facing APIs for proposal packages.
4. Add active commitment audit reports.
5. Add recovery lineage reports.
6. Add unresolved commitment reports.
7. Add domain-repair lineage reports.

The next step should likely be:

`R6.0 disruptive planning benchmark layer`


---

## R6.0 JSSP disruptive planning benchmark layer complete

R6.0 adds the first disruptive-planning benchmark path for JSSP.

The implemented path is:

    baseline schedule
    -> admitted CTL schedule records
    -> active commitments
    -> machine breakdown
    -> affected commitments fired
    -> concrete repair candidates packaged
    -> recovery lineage audited
    -> schedule StateView remains unchanged

Core invariant:

    A disruption does not directly rewrite the plan.
    A disruption wakes commitments.
    Recovery proposes repair.
    Audit explains lineage.
    Only a separately admitted domain CTL record may mutate schedule truth.

Validation:

    248 passed, 24 skipped

Next recommended milestones:

    R6.1 selected JSSP repair admission
    R7.0 production runtime hardening
    R8.0 external solver/provider integration


---

## R6.1 JSSP selected repair admission complete

R6.1 closes the selected-repair semantic loop after R6.0 disruptive planning.

Implemented path:

    baseline schedule
    -> admitted CTL schedule records
    -> active commitments
    -> machine breakdown
    -> affected commitments fired
    -> concrete repair candidates packaged
    -> selected repair candidates admitted through domain CTL
    -> selected schedule StateViews mutate
    -> corresponding commitments finalized as admitted

Core invariant:

    Recovery may propose.
    Product or policy may select.
    Domain CTL must admit.
    Only admitted domain CTL records mutate schedule truth.
    Commitment finalization is a separate commitment-FSM transition.

Observed R6.1 state:

    J3:O2 changes from 4-7 to 9-12
    J2:O3 changes from 7-11 to 12-16
    7 commitments remain live
    2 commitments become admitted
    unresolved commitment count drops from 9 to 7
    recovery lineage contains 4 rows

Validation:

    248 passed, 24 skipped

Next required checkpoint:

    Code review before starting R7.0 production runtime hardening.


---

## R6.2 review hardening complete

R6.2 records the post-R6.1 external code review and adds targeted negative coverage.

External review result:

    Critical issues: none
    Primary source-of-truth invariant: holds
    Architecture: ready for R7.0 after documented hardening blockers are addressed

R6.2 test additions:

    invalid selected repair candidate fails closed
    invalid repair admission commits no records
    affected StateViews remain unchanged after failed repair admission
    unresolved commitment count remains 9 after failed repair admission
    empty selected repair candidate set is a no-op

R6.2 demo correction:

    R6.1 repair admission demo now measures the intermediate state directly:
        9 unresolved before domain repair
        9 unresolved after domain repair
        7 unresolved after commitment finalization

Validation:

    248 passed, 24 skipped

R7.0 must start with:

    audit/report portability behind store protocol
    enforced validated admission as the public mutation boundary


---

## R6.3 REALM-Bench case fixtures complete

R6.3 extracts REALM-Bench cases into deterministic reusable test fixtures.

Added:

    tests/benchmarks/fixtures/realm_bench_cases.json
    tests/benchmarks/realm_case_loader.py
    tests/benchmarks/realm_thanksgiving_cases.py

The fixture contains all 14 REALM-Bench cases:

    P1-P10
    J1-J4

Thanksgiving cases are now directly reusable:

    P6 Thanksgiving Dinner Planning / TD-static
    P9 Thanksgiving with Disruptions / TD-dynamic

P9 models James's flight delay:

    original arrival: 13:00
    new arrival: 16:00
    notice time: 10:00
    delay: 180 minutes
    early notice window: 180 minutes

Validation:

    248 passed, 24 skipped

R6.3 remains benchmark fixture work only.
It does not start R7.0 infrastructure hardening.


---

## R6.4 REALM-Bench repository layout and reports complete

R6.4 moves REALM-Bench assets from test-only fixtures into a public researcher-facing benchmark tree.

Added public layout:

    benchmarks/realm/cases/
    benchmarks/realm/adapters/
    benchmarks/realm/reports/
    benchmarks/realm/solutions/
    benchmarks/realm/evaluations/
    benchmarks/realm/scripts/

The benchmark now exposes:

    all 14 REALM-Bench cases as committed JSON artifacts
    per-case files for P1-P10 and J1-J4
    reusable case loader and Thanksgiving adapter
    committed Markdown and JSON case catalog reports
    documented solution and evaluation directories

Researcher-facing report:

    benchmarks/realm/reports/realm_case_catalog_report.md

Validation:

    251 passed, 24 skipped

R6.4 remains repository organization and report work.
Executable Thanksgiving solving and evaluation start in R6.5.


---

## R6.5 Thanksgiving executable benchmark complete

R6.5 adds the first executable REALM-Bench benchmark report.

Added runner:

    benchmarks/realm/scripts/run_thanksgiving_benchmark.py

Generated solutions:

    benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json
    benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json

Generated evaluations:

    benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json
    benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json

Generated report:

    benchmarks/realm/reports/thanksgiving_p6_p9_report.md
    benchmarks/realm/reports/thanksgiving_p6_p9_report.json

Current result:

    P6 feasible: True
    P9 feasible after repair: True
    P6 optimality: feasible_not_proven_optimal
    P9 optimality: feasible_not_proven_optimal

P9 repair:

    James flight delay notice arrives at 10:00.
    James original arrival is 13:00.
    James new arrival is 16:00.
    Grandma pickup is reassigned from James to Sarah.
    Dinner remains feasible by 18:00.

Validation:

    253 passed, 24 skipped
