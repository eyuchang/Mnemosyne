from __future__ import annotations

import json
from pathlib import Path

from mnemosyne.benchmarks import p1_solver_runner
from mnemosyne.benchmarks.models import BenchmarkCase, BenchmarkStep
from mnemosyne.benchmarks.solver import (
    PlanProposal,
    SolverCertificate,
    SolverResult,
)
from mnemosyne.benchmarks.solver_registry import SolverRegistry


class LyingCampusTourSolver:
    def solve(self, data: dict) -> SolverResult:
        certificate = SolverCertificate(
            solver_id="lying-campus-tour-solver",
            solver_version="0.1",
            solver_run_id="run:lying-campus-tour",
            problem_family="p1_campus_tour",
            problem_id=data["case_id"],
            feasible=True,
            optimality_status="claimed_feasible",
            objective_name="minimize_total_minutes",
            objective_value=1,
            constraints_summary=["claims feasibility despite window violation"],
            violations=[],
            metrics={},
            provenance={"test": "domain_feasibility_admission"},
        )

        step = BenchmarkStep(
            step_id="visit_library_too_early",
            state_before="not_started",
            state_after="completed",
            action_type="visit_library",
            attrs_after={
                "location": "Library",
                "arrive": "09:00",
                "depart": "09:30",
                "window_not_before": "10:00",
                "finish_time": "09:30",
                "deadline": "17:00",
            },
        )

        benchmark_case = BenchmarkCase(
            case_id=data["case_id"],
            tenant_id="tenant:realm",
            workflow_id="workflow:lying_domain_feasibility",
            entity_id="entity:lying_domain_feasibility",
            binding_id="binding:lying_domain_feasibility",
            fsm="CampusTourFSM",
            app_id="campus_tour",
            schema_id="campus_tour.transition",
            steps=[step],
            metadata={"test": "lying feasible certificate"},
        )

        proposal = PlanProposal(
            proposal_id="proposal:lying-domain-feasibility",
            case_id=data["case_id"],
            tenant_id="tenant:realm",
            workflow_id="workflow:lying_domain_feasibility",
            entity_id="entity:lying_domain_feasibility",
            app_id="campus_tour",
            schema_id="campus_tour.transition",
            route=["S", "L"],
            steps=[
                {
                    "step_id": "visit_library_too_early",
                    "arrive": "09:00",
                    "depart": "09:30",
                    "window_not_before": "10:00",
                }
            ],
            attrs={
                "finish_time": "09:30",
                "deadline": "17:00",
            },
            certificate=certificate,
        )

        return SolverResult(
            ok=True,
            plan_proposal=proposal,
            benchmark_case=benchmark_case,
            certificate=certificate,
            error_message=None,
            details={},
        )


def test_runtime_rejects_lying_feasibility_certificate_before_commit(
    tmp_path: Path,
    monkeypatch,
):
    case_path = tmp_path / "lying_case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "lying_domain_feasibility_001",
                "realm_bench": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    registry = SolverRegistry()
    registry.register(
        name="lying-campus-tour",
        description="solver that lies about P1 domain feasibility",
        factory=LyingCampusTourSolver,
    )

    monkeypatch.setattr(
        p1_solver_runner,
        "default_solver_registry",
        lambda: registry,
    )

    output_path = tmp_path / "lying_result.jsonl"

    exit_code = p1_solver_runner.main(
        [
            "--cases",
            str(case_path),
            "--solver",
            "lying-campus-tour",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 1

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 1
    row = rows[0]

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert row["error_codes"] == ["DOMAIN_FEASIBILITY_REJECTED"]
    assert row["error_message"] == "domain feasibility rejected before commit"
    assert row["details"]["observed"]["committed"] is False

    report = row["details"]["domain_feasibility"]
    assert report["ok"] is False
    assert any(
        "TIME_WINDOW_EARLY" in violation
        for violation in report["violations"]
    )

    certificate = row["details"]["solver_certificate"]
    assert certificate["feasible"] is True
