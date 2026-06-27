# File: mnemosyne/benchmarks/solver.py
#
# Purpose:
#   General solver protocol and solver-certificate data model.
#
# Stage:
#   R2.0 — Solver protocol and certified proposal boundary.
#
# Core thesis:
#   Solvers produce certified proposals.
#   Mnemosyne validates and commits only proposals that satisfy application,
#   workflow, and transaction constraints.
#
# Important:
#   A solver result is not committed truth.
#   It is proposal evidence that may be admitted into the Mnemosyne commit path.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from mnemosyne.benchmarks.models import BenchmarkCase


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class SolverCertificate:
    """Evidence produced by a solver.

    The certificate describes what the solver claims, not what Mnemosyne has
    committed. Mnemosyne still validates and commits through its normal path.
    """

    solver_id: str
    solver_version: str
    solver_run_id: str
    problem_family: str
    problem_id: str
    feasible: bool
    optimality_status: str
    objective_name: str
    objective_value: int | float | str | None
    constraints_summary: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    metrics: JsonDict = field(default_factory=dict)
    provenance: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class PlanProposal:
    """A proposed plan derived by a solver.

    This is still not truth. It becomes committed truth only if converted into
    a BenchmarkCase / CommitBatch and accepted by Mnemosyne validation.
    """

    proposal_id: str
    case_id: str
    tenant_id: str
    workflow_id: str
    entity_id: str
    app_id: str
    schema_id: str
    route: list[str] = field(default_factory=list)
    steps: list[JsonDict] = field(default_factory=list)
    attrs: JsonDict = field(default_factory=dict)
    certificate: SolverCertificate | None = None


@dataclass(frozen=True)
class SolverResult:
    """Output of a BenchmarkSolver."""

    ok: bool
    plan_proposal: PlanProposal | None
    benchmark_case: BenchmarkCase | None
    certificate: SolverCertificate
    error_message: str | None = None
    details: JsonDict = field(default_factory=dict)


@runtime_checkable
class BenchmarkSolver(Protocol):
    """Protocol implemented by benchmark solver adapters."""

    solver_id: str
    solver_version: str

    def solve(self, data: JsonDict) -> SolverResult:
        """Solve a benchmark problem and return a certified proposal."""
        ...