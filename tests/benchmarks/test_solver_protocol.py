# File: tests/benchmarks/test_solver_protocol.py
#
# Purpose:
#   Verify R2.0 solver protocol data model.

from __future__ import annotations

from mnemosyne.benchmarks.solver import (
    PlanProposal,
    SolverCertificate,
    SolverResult,
)


def test_solver_certificate_and_plan_proposal_are_proposal_evidence_not_truth():
    certificate = SolverCertificate(
        solver_id="test-solver",
        solver_version="0.1",
        solver_run_id="solver-run:test-001",
        problem_family="REALM-Bench-compatible-local",
        problem_id="P1",
        feasible=True,
        optimality_status="optimal_for_enumerated_space",
        objective_name="minimize_total_minutes",
        objective_value=190,
        constraints_summary=[
            "required_visit_locations",
            "time_windows",
            "deadline",
        ],
        metrics={
            "total_minutes": 190,
        },
    )

    proposal = PlanProposal(
        proposal_id="proposal:test-001",
        case_id="case:test-001",
        tenant_id="tenant:test",
        workflow_id="workflow:test",
        entity_id="entity:test",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        route=["S", "D", "A", "B", "L", "S"],
        steps=[
            {
                "step_id": "visit_dorm",
                "action_type": "visit_dorm",
            }
        ],
        attrs={
            "note": "proposal only",
        },
        certificate=certificate,
    )

    result = SolverResult(
        ok=True,
        plan_proposal=proposal,
        benchmark_case=None,
        certificate=certificate,
    )

    assert result.ok is True
    assert result.plan_proposal is proposal
    assert result.benchmark_case is None
    assert result.certificate.feasible is True
    assert result.certificate.objective_value == 190
    assert result.plan_proposal.route == ["S", "D", "A", "B", "L", "S"]