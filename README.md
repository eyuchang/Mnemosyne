# Mnemosyne Production

Mnemosyne is the production runtime for ALAS-style transactional agent memory.

The current system is built around a correctness kernel:

    CommitBatch -> Validator -> Store -> CTL -> StateView

The core design rule is:

    Solvers, agents, runtimes, and workflows may propose or orchestrate.
    CTL/store remains committed truth.
    StateView remains current effective truth.

## Current milestone

Current verified milestone:

    R4.8: Temporal active recovery boundary

The project has now completed the following checkpoints:

    r4.5-active-commitments
    r4.6-runtime-active-recovery
    r4.7-recovery-proposal-packages
    r4.8-temporal-active-recovery-boundary

Current full local suite:

    179 passed, 24 skipped

## Implemented architecture

### Local correctness kernel

Implemented:

- CommitBatch
- TransitionCandidate
- CTLRecord
- Validator
- SQLite-backed Store
- CTL append
- StateView projection
- effective-history view
- full-history view
- compensation handling
- fail-closed compensation invariants
- op_id logical idempotency
- inbox/event-log idempotency
- outbox staging

Current source-of-truth rule:

    CTL/store owns committed truth.
    StateView owns current effective truth.
    Inbox deduplicates external events.
    Event log records observed causes.
    Outbox stages external side effects.

### Active commitment memory

R4.5 added CTL-resident active commitments.

Implemented:

- ActiveCommitment
- CommitmentEvent
- commitment lifecycle records
- CTL serialization through extension fields
- replay-derived active commitment index
- store-backed active commitment index
- bounded recursive recovery loop
- recovery policy
- recovery orchestration
- recovery admission boundary

Core invariant:

    A fired commitment may wake recovery,
    but it cannot mutate domain state directly.

    Only separately admitted domain CTL records mutate domain state.

### Runtime active recovery

R4.6 added runtime-level active recovery.

Implemented:

- LocalActiveRecoveryExecutor
- runtime planning from CTL-derived active commitment index
- commitment-FSM-only recovery execution
- admission-validated recovery execution through Validator
- R4.6 runtime recovery demo

Core invariant:

    Runtime recovery may update commitment state,
    but it may not mutate domain state directly.

### Recovery proposal packages

R4.7 added first-class recovery proposal packages.

Implemented:

- RecoveryProposalPackage
- package serialization helpers
- package references in commitment event payloads
- package-backed commitment proposal candidates
- package admission-boundary tests
- R4.7 proposal package demo

Core invariant:

    A recovery proposal package may contain proposed domain candidates,
    but those candidates are not committed truth.

    Commitment events record package references.
    Domain state changes still require separate domain CTL admission.

### Temporal active recovery boundary

R4.8 added a Temporal-style active recovery activity boundary.

Implemented:

- Temporal active recovery activity boundary
- ActiveRecoveryActivityResult
- commitment-FSM-only recovery commits through activity boundary
- validation and CTL commit behind activity boundary
- retry/idempotency tests
- R4.8 Temporal active recovery demo

Core invariant:

    Temporal workflow code remains orchestration-only.

    Active recovery planning, validation, and CTL commit happen through an
    activity boundary.

    Temporal active recovery may update commitment state,
    but it may not mutate domain state directly.

## Benchmark and solver path

The repository also includes local deterministic benchmark and solver infrastructure.

Implemented:

- REALM-style local fixture runner
- BenchmarkCase
- BenchmarkRunResult
- JSON/JSONL result serialization
- P1-compatible Campus Tour fixtures
- P1 brute-force Campus Tour solver
- SolverCertificate
- PlanProposal
- SolverResult
- BenchmarkSolver protocol
- solver registry
- proposal conflict preflight
- stale-world reconciliation preflight

Architectural rule:

    Solvers may propose certified plans.
    Mnemosyne validates and commits admitted truth.

## Not yet production-complete

Important future production work remains:

- real Temporal SDK adapter
- real Temporal workers
- PostgresStore behind the Store protocol
- migrations
- worker-safe inbox processing
- worker-safe outbox claiming
- provider adapters
- external OR solver adapters
- observability and audit reports
- deployment documentation
- integration and stress tests

## Development status

The repository is currently best described as:

    A local, deterministic Mnemosyne / ALAS product kernel with CTL-resident
    active memory, validated runtime recovery, inert recovery proposal packages,
    and Temporal-safe activity boundaries.

It is not yet a deployed production system.

## Current recommended next stage

Next recommended stage:

    R5.0 product API and audit surface

Purpose:

    expose stable product-facing APIs for commitments, recovery, proposal
    packages, and audit views without requiring application code to touch
    internal CTL/recovery modules directly.

## User guide

For running J1-J4 experiments, choosing SQLite or PostgreSQL, placing experiment code, and finding results, see:

- `docs/user_guide_j1_j4_experiments.md`

## Current readiness

- R7 PostgreSQL runtime adapter path is complete: see `docs/release_notes/r7_postgres_runtime_adapter_completion.md`.
- J1-J4 benchmark/user workflow is runnable in the default suite: see `docs/benchmark_readiness_matrix.md`.
- P1-P10 should not yet be claimed as fully runnable or certified.
