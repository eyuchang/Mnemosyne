# File: tests/benchmarks/test_p1_solver_adapter.py
#
# Purpose:
#   Verify R2.0 P1 solver adapter implements the generic solver protocol.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.p1_campus_tour_solver import P1CampusTourSolverAdapter
from mnemosyne.benchmarks.solver import BenchmarkSolver


P1_SOLVER_CASE_PATH = Path("benchmarks/realm/p1_solver/campus_tour_solver_001.json")


@pytest.mark.realm
def test_p1_solver_adapter_returns_certified_plan_proposal():
    data = json.loads(P1_SOLVER_CASE_PATH.read_text(encoding="utf-8"))
    solver = P1CampusTourSolverAdapter()

    assert isinstance(solver, BenchmarkSolver)

    result = solver.solve(data)

    assert result.ok is True
    assert result.error_message is None
    assert result.benchmark_case is not None
    assert result.plan_proposal is not None

    certificate = result.certificate
    proposal = result.plan_proposal

    assert certificate.solver_id == "p1_campus_tour_bruteforce"
    assert certificate.solver_version == "0.1"
    assert certificate.solver_run_id == "solver-run:local-p1-compatible-campus-tour-solver-001"
    assert certificate.problem_family == "REALM-Bench-compatible-local"
    assert certificate.problem_id == "P1"
    assert certificate.feasible is True
    assert certificate.optimality_status == "optimal_for_enumerated_space"
    assert certificate.objective_name == "minimize_total_minutes"
    assert certificate.objective_value == 190
    assert certificate.violations == []

    assert "required_visit_locations" in certificate.constraints_summary
    assert "time_windows" in certificate.constraints_summary
    assert "deadline" in certificate.constraints_summary
    assert "visit_order_constraints" in certificate.constraints_summary

    assert proposal.proposal_id == "proposal:local-p1-compatible-campus-tour-solver-001"
    assert proposal.route == ["S", "D", "A", "B", "L", "S"]
    assert proposal.certificate is certificate
    assert proposal.attrs["finish_time"] == "12:10"
    assert proposal.attrs["total_minutes"] == 190
    assert proposal.attrs["world_assumptions"] == [
        {
            "key": "deadline",
            "value": "17:00",
            "source": "p1_campus_tour_solver",
        }
    ]
    assert len(proposal.steps) == 5
