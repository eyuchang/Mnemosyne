# File: mnemosyne/benchmarks/p1_campus_tour_solver.py
#
# Purpose:
#   Brute-force local solver boundary for P1-compatible Campus Tour cases.
#
# Stage:
#   Stage 1.6R-P1B and R2.0.
#
# Important:
#   This is a local deterministic solver boundary.
#   It does not claim official REALM-Bench scoring.
#
# R2.0 contract:
#   The solver produces a certified proposal.
#   Mnemosyne validates and commits only through:
#
#     BenchmarkCase -> CommitBatch -> Validator -> Store -> CTL -> StateView

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from itertools import permutations
from typing import Any

from mnemosyne.benchmarks.models import BenchmarkCase
from mnemosyne.benchmarks.p1_campus_tour import hhmm_to_minutes, minutes_to_hhmm
from mnemosyne.benchmarks.solver import (
    BenchmarkSolver,
    PlanProposal,
    SolverCertificate,
    SolverResult,
)


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class P1CampusTourStop:
    location_id: str
    arrive: str
    depart: str
    visit: bool


@dataclass(frozen=True)
class P1CampusTourPlan:
    route: list[str]
    stops: list[P1CampusTourStop]
    feasible: bool
    violations: list[str]
    start_time: str
    finish_time: str
    deadline: str
    total_travel_minutes: int
    total_visit_minutes: int
    total_minutes: int


def _travel_lookup(spec: JsonDict) -> dict[tuple[str, str], int]:
    bidirectional = bool(spec.get("bidirectional_travel_edges", False))
    travel: dict[tuple[str, str], int] = {}

    for edge in spec["travel_edges"]:
        src = edge["from"]
        dst = edge["to"]
        minutes = int(edge["minutes"])

        travel[(src, dst)] = minutes

        if bidirectional:
            travel[(dst, src)] = minutes

    return travel


def _time_windows(spec: JsonDict) -> dict[str, dict[str, str]]:
    return {
        location_id: dict(window)
        for location_id, window in spec.get("time_windows", {}).items()
    }


def _route_respects_order_constraints(
    *,
    ordering: tuple[str, ...],
    constraints: list[list[str]],
) -> bool:
    positions = {
        location_id: index
        for index, location_id in enumerate(ordering)
    }

    for constraint in constraints:
        if len(constraint) != 2:
            raise ValueError(f"invalid visit_order_constraint: {constraint}")

        before, after = constraint

        if positions[before] >= positions[after]:
            return False

    return True


def _schedule_route(
    *,
    spec: JsonDict,
    route: list[str],
    travel: dict[tuple[str, str], int],
) -> P1CampusTourPlan:
    start_time = spec["start_time"]
    deadline = spec["deadline"]
    start_minutes = hhmm_to_minutes(start_time)
    current_minutes = start_minutes
    visit_duration = int(spec["visit_duration_minutes"])
    must_visit = set(spec["must_visit_locations"])
    windows = _time_windows(spec)

    total_travel = 0
    total_visit = 0
    violations: list[str] = []

    stops: list[P1CampusTourStop] = [
        P1CampusTourStop(
            location_id=route[0],
            arrive=start_time,
            depart=start_time,
            visit=False,
        )
    ]

    for previous_location, current_location in zip(route, route[1:]):
        edge_minutes = travel.get((previous_location, current_location))

        if edge_minutes is None:
            violations.append(f"MISSING_TRAVEL_EDGE:{previous_location}->{current_location}")
            edge_minutes = 0

        total_travel += edge_minutes
        current_minutes += edge_minutes

        arrive_minutes = current_minutes
        visit = current_location in must_visit
        depart_minutes = arrive_minutes + visit_duration if visit else arrive_minutes

        if visit:
            total_visit += visit_duration

        window = windows.get(current_location, {})

        if "not_before" in window and arrive_minutes < hhmm_to_minutes(window["not_before"]):
            violations.append(
                f"TIME_WINDOW_EARLY:{current_location}:"
                f"arrive={minutes_to_hhmm(arrive_minutes)}:"
                f"not_before={window['not_before']}"
            )

        if "not_after" in window and depart_minutes > hhmm_to_minutes(window["not_after"]):
            violations.append(
                f"TIME_WINDOW_LATE:{current_location}:"
                f"depart={minutes_to_hhmm(depart_minutes)}:"
                f"not_after={window['not_after']}"
            )

        stops.append(
            P1CampusTourStop(
                location_id=current_location,
                arrive=minutes_to_hhmm(arrive_minutes),
                depart=minutes_to_hhmm(depart_minutes),
                visit=visit,
            )
        )

        current_minutes = depart_minutes

    finish_time = minutes_to_hhmm(current_minutes)

    if current_minutes > hhmm_to_minutes(deadline):
        violations.append(f"DEADLINE_MISSED:finish={finish_time}:deadline={deadline}")

    return P1CampusTourPlan(
        route=route,
        stops=stops,
        feasible=not violations,
        violations=violations,
        start_time=start_time,
        finish_time=finish_time,
        deadline=deadline,
        total_travel_minutes=total_travel,
        total_visit_minutes=total_visit,
        total_minutes=current_minutes - start_minutes,
    )


def solve_p1_campus_tour(data: JsonDict) -> P1CampusTourPlan:
    """Derive the shortest feasible route for a local P1-compatible case.

    This is a brute-force solver over the must-visit locations. That is enough
    for the small local P1 fixture and keeps the solver deterministic and
    dependency-free.

    If visit_order_constraints are provided, the solver searches only orderings
    that satisfy those constraints.
    """
    spec = data["realm_bench"]
    start = spec["start_location"]
    end = spec["end_location"]
    must_visit = list(spec["must_visit_locations"])
    visit_order_constraints = list(spec.get("visit_order_constraints", []))
    travel = _travel_lookup(spec)

    best_feasible: P1CampusTourPlan | None = None
    best_infeasible: P1CampusTourPlan | None = None

    for ordering in permutations(must_visit):
        if visit_order_constraints and not _route_respects_order_constraints(
            ordering=ordering,
            constraints=visit_order_constraints,
        ):
            continue

        route = [start, *ordering, end]
        plan = _schedule_route(
            spec=spec,
            route=route,
            travel=travel,
        )

        if plan.feasible:
            if best_feasible is None:
                best_feasible = plan
            elif (plan.total_minutes, plan.total_travel_minutes, plan.route) < (
                best_feasible.total_minutes,
                best_feasible.total_travel_minutes,
                best_feasible.route,
            ):
                best_feasible = plan
        else:
            if best_infeasible is None:
                best_infeasible = plan
            elif (len(plan.violations), plan.total_minutes, plan.route) < (
                len(best_infeasible.violations),
                best_infeasible.total_minutes,
                best_infeasible.route,
            ):
                best_infeasible = plan

    if best_feasible is not None:
        return best_feasible

    if best_infeasible is not None:
        return best_infeasible

    raise ValueError("no route candidates generated")


def _steps_from_plan(
    *,
    data: JsonDict,
    plan: P1CampusTourPlan,
) -> list[JsonDict]:
    spec = data["realm_bench"]
    locations = dict(spec["locations"])
    action_templates = dict(spec["action_templates"])
    time_windows = _time_windows(spec)

    steps: list[JsonDict] = []
    previous_step_id: str | None = None

    for stop in plan.stops:
        if not stop.visit:
            continue

        template = dict(action_templates[stop.location_id])
        step_id = template["step_id"]

        attrs_after: JsonDict = {
            "location_id": stop.location_id,
            "location_name": locations[stop.location_id],
            "arrive": stop.arrive,
            "depart": stop.depart,
            "visit_minutes": int(spec["visit_duration_minutes"]),
        }

        window = time_windows.get(stop.location_id, {})

        if "not_before" in window:
            attrs_after["window_not_before"] = window["not_before"]

        if "not_after" in window:
            attrs_after["window_not_after"] = window["not_after"]

        step: JsonDict = {
            "step_id": step_id,
            "state_before": template["state_before"],
            "state_after": template["state_after"],
            "action_type": template["action_type"],
            "attrs_after": attrs_after,
        }

        if previous_step_id is not None:
            step["depends_on"] = [previous_step_id]

        steps.append(step)
        previous_step_id = step_id

    return_template = dict(action_templates["return"])
    return_stop = plan.stops[-1]
    return_step: JsonDict = {
        "step_id": return_template["step_id"],
        "state_before": return_template["state_before"],
        "state_after": return_template["state_after"],
        "action_type": return_template["action_type"],
        "depends_on": [previous_step_id] if previous_step_id is not None else [],
        "attrs_after": {
            "location_id": return_stop.location_id,
            "location_name": locations[return_stop.location_id],
            "arrive": return_stop.arrive,
            "depart": return_stop.depart,
            "finish_time": plan.finish_time,
            "deadline": plan.deadline,
            "total_minutes": plan.total_minutes,
        },
    }

    steps.append(return_step)

    return steps


def _constraints_summary(data: JsonDict) -> list[str]:
    spec = data["realm_bench"]
    constraints = [
        "required_visit_locations",
        "travel_edges",
        "visit_duration",
        "deadline",
    ]

    if spec.get("time_windows"):
        constraints.append("time_windows")

    if spec.get("visit_order_constraints"):
        constraints.append("visit_order_constraints")

    if spec.get("bidirectional_travel_edges"):
        constraints.append("bidirectional_travel_edges")

    return constraints


def _certificate_from_plan(
    *,
    data: JsonDict,
    plan: P1CampusTourPlan,
    solver_id: str,
    solver_version: str,
) -> SolverCertificate:
    spec = data["realm_bench"]
    case_id = data["case_id"]

    return SolverCertificate(
        solver_id=solver_id,
        solver_version=solver_version,
        solver_run_id=f"solver-run:{case_id}",
        problem_family=str(spec.get("benchmark_family", "REALM-Bench-compatible-local")),
        problem_id=str(spec.get("problem_id", "P1")),
        feasible=plan.feasible,
        optimality_status=(
            "optimal_for_enumerated_space"
            if plan.feasible
            else "no_feasible_plan_in_enumerated_space"
        ),
        objective_name="minimize_total_minutes",
        objective_value=plan.total_minutes if plan.feasible else None,
        constraints_summary=_constraints_summary(data),
        violations=list(plan.violations),
        metrics={
            "route": list(plan.route),
            "finish_time": plan.finish_time,
            "deadline": plan.deadline,
            "total_travel_minutes": plan.total_travel_minutes,
            "total_visit_minutes": plan.total_visit_minutes,
            "total_minutes": plan.total_minutes,
        },
        provenance={
            "claim": "local deterministic brute-force solver over enumerated visit permutations",
            "official_realm_bench": bool(data.get("official_realm_bench", False)),
        },
    )


def _solved_case_data_from_plan(
    *,
    data: JsonDict,
    plan: P1CampusTourPlan,
    certificate: SolverCertificate,
) -> JsonDict:
    solved = deepcopy(data)

    solved["realm_bench"]["route"] = [
        asdict(stop)
        for stop in plan.stops
    ]
    solved["realm_bench"]["oracle"] = {
        "route": list(plan.route),
        "finish_time": plan.finish_time,
        "total_travel_minutes": plan.total_travel_minutes,
        "total_visit_minutes": plan.total_visit_minutes,
        "total_minutes": plan.total_minutes,
    }
    solved["expected"] = {
        "feasible": plan.feasible,
        "should_commit": plan.feasible,
        "route": list(plan.route),
        "finish_time": plan.finish_time,
        "total_travel_minutes": plan.total_travel_minutes,
        "total_visit_minutes": plan.total_visit_minutes,
        "total_minutes": plan.total_minutes,
        "final_state": "completed",
        "total_records": 5,
        "effective_records": 5,
        "ineffective_records": 0,
        "outbox_rows": 0,
        "state_version": 5,
    }
    solved["solver_certificate"] = asdict(certificate)
    solved["steps"] = _steps_from_plan(
        data=solved,
        plan=plan,
    )

    return solved


def p1_solved_benchmark_case_from_dict(data: JsonDict) -> BenchmarkCase:
    """Solve a local P1-compatible fixture and return a BenchmarkCase.

    This compatibility helper remains for older tests and direct callers.
    R2.0 users should prefer P1CampusTourSolverAdapter.solve(...).
    """
    from mnemosyne.benchmarks.runner import benchmark_case_from_dict

    plan = solve_p1_campus_tour(data)
    certificate = _certificate_from_plan(
        data=data,
        plan=plan,
        solver_id=P1CampusTourSolverAdapter.solver_id,
        solver_version=P1CampusTourSolverAdapter.solver_version,
    )
    solved = _solved_case_data_from_plan(
        data=data,
        plan=plan,
        certificate=certificate,
    )

    return benchmark_case_from_dict(solved)


class P1CampusTourSolverAdapter(BenchmarkSolver):
    """R2.0 solver adapter for local P1-compatible Campus Tour cases."""

    solver_id = "p1_campus_tour_bruteforce"
    solver_version = "0.1"

    def solve(self, data: JsonDict) -> SolverResult:
        from mnemosyne.benchmarks.runner import benchmark_case_from_dict

        plan = solve_p1_campus_tour(data)
        certificate = _certificate_from_plan(
            data=data,
            plan=plan,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
        )

        if not plan.feasible:
            return SolverResult(
                ok=False,
                plan_proposal=None,
                benchmark_case=None,
                certificate=certificate,
                error_message="no feasible P1 Campus Tour plan found",
                details={
                    "violations": list(plan.violations),
                },
            )

        solved = _solved_case_data_from_plan(
            data=data,
            plan=plan,
            certificate=certificate,
        )
        benchmark_case = benchmark_case_from_dict(solved)

        proposal = PlanProposal(
            proposal_id=f"proposal:{data['case_id']}",
            case_id=data["case_id"],
            tenant_id=data["tenant_id"],
            workflow_id=data["workflow_id"],
            entity_id=data["entity_id"],
            app_id=data["app_id"],
            schema_id=data["schema_id"],
            route=list(plan.route),
            steps=list(solved["steps"]),
            attrs={
                "start_time": plan.start_time,
                "finish_time": plan.finish_time,
                "deadline": plan.deadline,
                "total_travel_minutes": plan.total_travel_minutes,
                "total_visit_minutes": plan.total_visit_minutes,
                "total_minutes": plan.total_minutes,
                "world_assumptions": [
                    {
                        "key": "deadline",
                        "value": plan.deadline,
                        "source": "p1_campus_tour_solver",
                    }
                ],
            },
            certificate=certificate,
        )

        return SolverResult(
            ok=True,
            plan_proposal=proposal,
            benchmark_case=benchmark_case,
            certificate=certificate,
            details={
                "route": list(plan.route),
                "finish_time": plan.finish_time,
                "total_minutes": plan.total_minutes,
            },
        )
