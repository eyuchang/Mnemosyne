
## R0.2 update — Solver-derived evidence loop

R0.2 is complete.

R0.1 established human-readable reports for benchmark JSONL.

R0.2 extends this to the P1 solver-derived path.

The current evidence loop is now:

`solver fixture -> solver-derived BenchmarkCase -> commit through Mnemosyne -> JSONL -> Markdown report`

This matters because the P1B result is no longer only a unit-test observation. It is now a reproducible command-line artifact with a readable report.

R0.2 strengthens the research/paper path without requiring R3 infrastructure.

No Postgres, cloud runtime, real Temporal workers, or hiring is needed for this milestone.

Current readiness interpretation:

- R0.1: benchmark reports exist.
- R0.2: solver-derived P1 result can be run and reported.
- R0 overall: still not complete until more normal P cases are represented.
- R1: disruption readiness still future.
- R2: optimization readiness remains partial and local for P1 only.
- R3/R4: operational maturity remains intentionally deferred.

The next natural research-path steps are:

1. add P2/P3/P5 normal-case skeletons;
2. add more P1-compatible fixtures;
3. define a general solver protocol;
4. add the first disruption fixture for R1.

## R2.0 update — Solver protocol and certified proposal boundary

R2.0 is complete.

R2.0 introduces the first general optimization boundary:

`solver proposes -> Mnemosyne validates -> CTL commits -> StateView reports`

This is the formal boundary between optimization and committed truth.

Implemented R2.0 artifacts:

- `SolverCertificate`
- `PlanProposal`
- `SolverResult`
- `BenchmarkSolver`
- `P1CampusTourSolverAdapter`

Readiness interpretation:

- R2.0 does not require Postgres, cloud runtime, real Temporal workers, or external OR solvers.
- R2.0 is compatible with the research path and can run on SQLite.
- R2.0 is not full optimization maturity; it is the protocol boundary for optimization.
- R2.1 should add a real external optimizer adapter, such as OR-Tools or another solver backend.

Why R2.0 matters:

Traditional transaction processing assumes that a transaction proposer is trusted or deterministic enough to be admitted directly into commit processing.

Agentic systems violate this assumption.

In Mnemosyne / ALAS, LLMs, solvers, planners, and agents produce proposals. These proposals must be certified, validated, and admitted before becoming committed truth.

R2.0 captures this distinction by making solver certificates first-class evidence attached to plan proposals.

R2.0 current status:

- P1-compatible local solver is behind the general solver protocol.
- P1 solver output includes a certificate.
- JSONL output includes solver certificate and plan proposal.
- Markdown report renders solver certificate and plan proposal.
- Mnemosyne remains the commit authority.

## R2.1 update — Solver registry and selectable backend

R2.1 is complete.

R2.1 extends R2.0 by making solver selection explicit and pluggable.

The current solver registry contains:

- `p1-bruteforce`

This allows benchmark execution to choose a solver backend by name:

`--solver p1-bruteforce`

Readiness interpretation:

- R2.0 introduced the solver protocol and certificate.
- R2.1 introduced solver registration and selection.
- R2.1 still uses a local deterministic solver.
- R2.1 does not yet add OR-Tools or external optimization.
- R2.1 prepares the adapter boundary for external solvers.

This strengthens the Agentic Transaction Processing thesis because the solver is no longer hardwired into the benchmark runner. A solver is now a registered proposer, not a commit authority.

## R2.2 update — Proposal conflict semantics

R2.2 is complete.

R2.2 extends the solver protocol with a proposal-admission preflight.

The system now distinguishes:

1. solver feasibility;
2. solver certificate;
3. active proposal conflict status;
4. validator acceptance;
5. committed truth.

This matters for agentic distributed systems because multiple LLMs, solvers, or agents may propose competing actions for the same workflow or entity.

Readiness interpretation:

- R2.0 introduced solver certificates.
- R2.1 made solver backends selectable.
- R2.2 introduced proposal conflict detection before commit admission.
- R2.2 remains local and SQLite-compatible.
- R2.2 does not require Postgres or real Temporal workers.

R2.2 strengthens the Agentic Transaction Processing thesis:

the proposer is untrusted, nondeterministic, and possibly optimizing; therefore the system must admit only validated, dependency-safe, conflict-free, and eventually externally confirmed proposals into committed truth.

Future extensions:

- dependency-scope proposal conflicts;
- optimistic retry semantics;
- stale-world reconciliation;
- external optimizer adapters.

## R2.3 update — Stale-world reconciliation

R2.3 is complete.

R2.3 extends proposal admission with stale-world reconciliation.

The system now distinguishes:

1. solver feasibility;
2. solver certificate;
3. active proposal conflict status;
4. world-assumption reconciliation;
5. validator acceptance;
6. committed truth.

This matters for agentic distributed systems because the external world can drift without a clean event entering the system.

Examples:

- deadline changed;
- route blocked;
- reservation expired;
- provider state changed;
- calendar availability changed;
- resource capacity changed.

R2.3 remains local and SQLite-compatible.

It does not require Postgres, real Temporal workers, or external APIs.

R2.3 strengthens the Agentic Transaction Processing thesis:

the proposer is untrusted, nondeterministic, possibly optimizing, and possibly stale; therefore the system must admit only proposals that are validated, conflict-free, and reconciled against observed world facts.

Future extensions:

- richer observed-world schemas;
- external provider polling;
- periodic reconciliation jobs;
- repair proposals after stale-world rejection;
- integration with real event sources.
