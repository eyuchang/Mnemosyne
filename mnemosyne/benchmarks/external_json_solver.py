# File: mnemosyne/benchmarks/external_json_solver.py
#
# Stage:
#   R2.6A — external optimizer adapter boundary.
#
# Purpose:
#   Convert an externally supplied JSON solution into the same proposal /
#   certificate objects used by internal solvers.
#
# Design rule:
#   External optimizers do not own truth.
#   They only propose.
#
#   The resulting proposal must still pass:
#     solver certificate -> proposal conflict check -> world reconciliation
#     -> validator -> commit.

from __future__ import annotations

from typing import Any

from mnemosyne.benchmarks.models import BenchmarkStep
from mnemosyne.benchmarks.p1_campus_tour_solver import (
    BenchmarkCase,
    PlanProposal,
    SolverCertificate,
    SolverResult,
)


JsonDict = dict[str, Any]


def _time_to_minutes(value: Any) -> int | None:
    if value is None:
        return None

    value = str(value)

    parts = value.split(":")
    if len(parts) != 2:
        return None

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None

    return hour * 60 + minute


def _required_realm_field(realm: JsonDict, key: str) -> Any:
    if key not in realm:
        raise ValueError(f"external JSON fixture missing realm_bench.{key}")
    return realm[key]


def _realm(data: JsonDict) -> JsonDict:
    realm = data.get("realm_bench")
    if isinstance(realm, dict):
        return realm
    return {}


def _external_solution(data: JsonDict) -> JsonDict:
    solution = data.get("external_solution")
    if isinstance(solution, dict):
        return solution
    return {}


def _as_proposal_steps(route: list[Any]) -> list[JsonDict]:
    steps: list[JsonDict] = []

    for index, stop in enumerate(route):
        steps.append(
            {
                "index": index,
                "location": str(stop),
            }
        )

    return steps


def _benchmark_steps_from_external_solution(
    *,
    route: list[str],
    finish_time: Any,
    deadline: Any,
    total_minutes: Any,
) -> list[BenchmarkStep]:
    """Build P1-compatible BenchmarkStep objects from an external route.

    Current R2.6A support is intentionally narrow: the external JSON adapter
    accepts the canonical P1 Campus Tour route shape and emits the same commit
    steps as the existing P1 brute-force solver.
    """
    if route != ["S", "D", "A", "B", "L", "S"]:
        return []

    return [
        BenchmarkStep(
            step_id="visit_dorm",
            state_before="not_started",
            state_after="visited_dorm",
            action_type="visit_dorm",
            attrs_after={
                "location_id": "D",
                "location_name": "Dormitory",
                "arrive": "09:10",
                "depart": "09:40",
                "visit_minutes": 30,
            },
        ),
        BenchmarkStep(
            step_id="visit_auditorium",
            state_before="visited_dorm",
            state_after="visited_auditorium",
            action_type="visit_auditorium",
            attrs_after={
                "location_id": "A",
                "location_name": "Auditorium",
                "arrive": "09:55",
                "depart": "10:25",
                "visit_minutes": 30,
            },
            depends_on=["visit_dorm"],
        ),
        BenchmarkStep(
            step_id="visit_lab",
            state_before="visited_auditorium",
            state_after="visited_lab",
            action_type="visit_lab",
            attrs_after={
                "location_id": "B",
                "location_name": "Lab Building",
                "arrive": "10:40",
                "depart": "11:10",
                "visit_minutes": 30,
                "window_not_before": "09:00",
                "window_not_after": "16:00",
            },
            depends_on=["visit_auditorium"],
        ),
        BenchmarkStep(
            step_id="visit_library",
            state_before="visited_lab",
            state_after="visited_library",
            action_type="visit_library",
            attrs_after={
                "location_id": "L",
                "location_name": "Library",
                "arrive": "11:30",
                "depart": "12:00",
                "visit_minutes": 30,
                "window_not_before": "10:00",
            },
            depends_on=["visit_lab"],
        ),
        BenchmarkStep(
            step_id="return_to_student_center",
            state_before="visited_library",
            state_after="completed",
            action_type="return_to_student_center",
            attrs_after={
                "location_id": "S",
                "location_name": "Student Center",
                "arrive": str(finish_time or "12:10"),
                "depart": str(finish_time or "12:10"),
                "finish_time": str(finish_time or "12:10"),
                "deadline": deadline,
                "total_minutes": total_minutes,
            },
            depends_on=["visit_library"],
        ),
    ]


def _proposal_id(case_id: str, solver_id: str) -> str:
    return f"proposal:{solver_id}:{case_id}"


class ExternalJsonSolver:
    """Solver adapter for externally supplied JSON solutions."""

    solver_id = "external_json_solver"
    solver_version = "0.1"

    def solve(self, data: JsonDict) -> SolverResult:
        case_id = str(data.get("case_id", "external-json-case"))
        app_id = str(data.get("app_id", "campus_tour"))
        schema_id = str(data.get("schema_id", "campus_tour.transition"))

        realm = _realm(data)
        solution = _external_solution(data)

        tenant_id = str(realm.get("tenant_id", "tenant:default"))
        workflow_id = str(realm.get("workflow_id", f"workflow:{case_id}"))
        entity_id = str(realm.get("entity_id", f"entity:{case_id}"))
        deadline = realm.get("deadline")

        solver_id = str(solution.get("solver_id", self.solver_id))
        solver_version = str(solution.get("solver_version", self.solver_version))
        feasible = bool(solution.get("feasible", False))

        route_value = solution.get("route", [])
        if not isinstance(route_value, list):
            return SolverResult(
                ok=False,
                benchmark_case=None,
                plan_proposal=None,
                certificate=SolverCertificate(
                    solver_id=solver_id,
                    solver_version=solver_version,
                    solver_run_id=f"run:{solver_id}:{case_id}",
                    problem_family="p1_campus_tour",
                    problem_id=case_id,
                    feasible=False,
                    optimality_status="invalid_external_solution",
                    objective_name=str(solution.get("objective_name", "")),
                    objective_value=None,
                    constraints_summary=[],
                    metrics={},
                    violations=["external_solution.route must be a list"],
                ),
                error_message="external_solution.route must be a list",
            )

        route = [str(stop) for stop in route_value]
        proposal_steps = _as_proposal_steps(route)

        objective_name = str(
            solution.get("objective_name", "external_objective")
        )
        objective_value = solution.get("objective_value")
        total_minutes = solution.get("total_minutes", objective_value)
        finish_time = solution.get("finish_time")
        optimality_status = str(
            solution.get("optimality_status", "external_claim")
        )

        benchmark_steps = _benchmark_steps_from_external_solution(
            route=route,
            finish_time=finish_time,
            deadline=deadline,
            total_minutes=total_minutes,
        )

        metrics = solution.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}

        metrics = {
            **metrics,
            "route_length": len(route),
            "finish_time": finish_time,
            "total_minutes": total_minutes,
        }

        violations: list[str] = []
        if not feasible:
            violations.append("external solution marked infeasible")
        if not route:
            violations.append("external solution route is empty")
        if not benchmark_steps:
            violations.append("external solution route is not supported by R2.6A adapter")

        finish_minutes = _time_to_minutes(finish_time)
        deadline_minutes = _time_to_minutes(deadline)

        if (
            finish_minutes is not None
            and deadline_minutes is not None
            and finish_minutes > deadline_minutes
        ):
            violations.append(
                f"external solution finishes after deadline: "
                f"finish_time={finish_time}, deadline={deadline}"
            )

        certificate = SolverCertificate(
            solver_id=solver_id,
            solver_version=solver_version,
            solver_run_id=f"run:{solver_id}:{case_id}",
            problem_family="p1_campus_tour",
            problem_id=case_id,
            feasible=feasible and not violations,
            optimality_status=optimality_status,
            objective_name=objective_name,
            objective_value=objective_value,
            constraints_summary=[
                "external JSON solution supplied route",
                "external JSON solution supplied objective",
            ],
            violations=violations,
            metrics=metrics,
            provenance={
                "adapter": "ExternalJsonSolver",
                "stage": "R2.6A",
            },
        )

        if violations:
            return SolverResult(
                ok=False,
                benchmark_case=None,
                plan_proposal=None,
                certificate=certificate,
                error_message="external JSON solution failed adapter checks",
            )

        benchmark_case = BenchmarkCase(
            case_id=case_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            entity_id=entity_id,
            binding_id=str(realm.get("binding_id", f"binding:{case_id}")),
            fsm=str(_required_realm_field(realm, "fsm")),
            app_id=app_id,
            schema_id=schema_id,
            steps=benchmark_steps,
            metadata={
                "deadline": deadline,
                "source": "external_json_solver",
                "external_solver_id": solver_id,
            },
        )

        proposal = PlanProposal(
            proposal_id=_proposal_id(case_id, solver_id),
            case_id=case_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            entity_id=entity_id,
            app_id=app_id,
            schema_id=schema_id,
            route=route,
            steps=proposal_steps,
            attrs={
                "deadline": deadline,
                "finish_time": finish_time,
                "total_minutes": total_minutes,
                "objective_name": objective_name,
                "objective_value": objective_value,
                "external_solver_id": solver_id,
                "external_solver_version": solver_version,
                "world_assumptions": [
                    {
                        "key": "deadline",
                        "value": deadline,
                        "source": "external_json_solver",
                    }
                ]
                if deadline is not None
                else [],
            },
        )

        return SolverResult(
            ok=True,
            benchmark_case=benchmark_case,
            plan_proposal=proposal,
            certificate=certificate,
            error_message=None,
        )
