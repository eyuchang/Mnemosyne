# R2 Readiness Summary

## Status

R2 is complete.

R2 establishes the proposal-admission boundary for Mnemosyne/ALAS runtime experiments, including runtime-side P1 deadline/time-window feasibility checks.

The central contract is:

> Solvers, agents, and external tools may propose.  
> Mnemosyne validates, commits, rejects, audits, and repairs.

## Completed milestones

- R2.0 — Solver protocol / certified proposal boundary
- R2.1 — Solver registry / selectable backend
- R2.2 — Proposal conflict preflight
- R2.3 — Stale-world reconciliation
- R2.4 — Audit reporting for failed and rejected rows
- R2.5 — Deterministic stale-world repair
- R2.6A — External JSON solver good-path commit
- R2.6B — External JSON solver expected-negative rejection
- R2.7A — Benchmark-family skeleton fixtures
- R2.7B — Report-only skeleton family rows
- R2.8 — R2 conformance suite
- R2.9 — Documentation freeze / readiness summary

## Evidence artifacts

- `results/r2/external_json_solver_001.jsonl`
- `results/r2/external_json_bad_deadline_001.jsonl`
- `results/r2/stale_world_repair_1300.jsonl`
- `results/r2/rejection_audit_fixture.jsonl`
- `results/r2/skeleton_families.jsonl`
- `tests/benchmarks/test_r2_conformance_suite.py`

## What R2 proves

R2 proves that the runtime can support a controlled proposal-admission path:

1. A solver or external adapter produces a certified proposal.
2. The proposal can be checked for conflicts before commit.
3. The proposal can be checked against world assumptions.
4. Stale-world proposals can be rejected.
5. Some stale-world proposals can be repaired deterministically.
6. Bad P1 deadline/time-window feasibility claims can be rejected before commit independent of the solver certificate.
7. Successful proposals commit through the kernel path.
8. Failed and rejected rows are preserved as audit evidence.
9. Future benchmark families can be represented without pretending they are executable.

## What R2 does not yet prove

R2 does not yet prove:

- general user-created workflow authoring
- general agent creation and lifecycle management
- production-grade runtime orchestration
- multi-agent coordination
- persistent production deployment
- complete P2/P3/P5 solvers
- general domain-feasibility validators for all future apps
- general external optimizer adapters beyond the canonical P1 boundary probe
- production benchmark scoring
- concurrent workflow execution at scale

## Design boundary

Benchmarks in R2 are controlled probes, not the product.

The architectural center remains:

- workflow creation
- agent proposal
- runtime validation
- commit / reject authority
- auditability
- repair and recovery

## Readiness conclusion

R2 is ready to freeze.

Recommended next stage:

> R3 — Workflow and Agent Runtime Substrate

## Post-review clarification

A code review identified an important distinction:

- R2 was already clean at the transactional boundary.
- R2 needed an explicit runtime-side check for P1 domain feasibility so a solver certificate could not be treated as truth.

The post-review patch adds a P1 admission check for deadline and time-window feasibility. A regression test now verifies that a solver claiming `feasible=true` is still rejected before commit when the proposed schedule violates a P1 time window.

The external JSON adapter remains a canonical P1 boundary probe, not a general external optimizer adapter.

