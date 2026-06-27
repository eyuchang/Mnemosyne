# File: mnemosyne/benchmarks/p1_campus_tour.py
#
# Purpose:
#   Helpers for validating a P1-compatible Campus Tour oracle trace.
#
# Stage:
#   Stage 1.6R-P1A-Verified.
#
# Important:
#   This validates a supplied oracle trace. It does not solve the route.
#   A later P1B stage should add planner/solver support.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mnemosyne.benchmarks.models import BenchmarkCase


@dataclass(frozen=True)
class P1CampusTourTraceMetrics:
    route: list[str]
    feasible: bool
    violations: list[str]
    start_time: str
    finish_time: str
    deadline: str
    total_travel_minutes: int
    total_visit_minutes: int
    total_minutes: int


def p1_trace_metrics_to_dict(metrics: P1CampusTourTraceMetrics) -> dict[str, Any]:
    return asdict(metrics)


def hhmm_to_minutes(value: str) -> int:
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text) * 60 + int(minute_text)


def minutes_to_hhmm(value: int) -> str:
    hour = value // 60
    minute = value % 60
    return f"{hour:02d}:{minute:02d}"


def _travel_lookup(data: dict[str, Any]) -> dict[tuple[str, str], int]:
    spec = data["realm_bench"]
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


def _time_windows(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        location_id: dict(window)
        for location_id, window in data["realm_bench"].get("time_windows", {}).items()
    }


def validate_p1_campus_tour_case(case: BenchmarkCase) -> P1CampusTourTraceMetrics:
    return validate_p1_campus_tour_trace(
        {
            "realm_bench": dict(case.metadata["realm_bench"]),
        }
    )


def validate_p1_campus_tour_trace(data: dict[str, Any]) -> P1CampusTourTraceMetrics:
    """Validate a supplied P1-compatible Campus Tour trace.

    Checks:
        - travel time consistency between consecutive route points;
        - fixed visit duration for visit stops;
        - declared time windows;
        - final deadline;
        - oracle summary fields.
    """
    spec = data["realm_bench"]
    route_rows = spec["route"]
    travel = _travel_lookup(data)
    windows = _time_windows(data)

    violations: list[str] = []

    route = [row["location_id"] for row in route_rows]
    start_time = route_rows[0]["depart"]
    finish_time = route_rows[-1]["arrive"]
    deadline = spec["deadline"]

    total_travel = 0
    total_visit = 0
    visit_duration = int(spec["visit_duration_minutes"])

    for previous, current in zip(route_rows, route_rows[1:]):
        previous_location = previous["location_id"]
        current_location = current["location_id"]
        expected_travel = travel.get((previous_location, current_location))

        if expected_travel is None:
            violations.append(
                f"MISSING_TRAVEL_EDGE:{previous_location}->{current_location}"
            )
            continue

        actual_travel = (
            hhmm_to_minutes(current["arrive"])
            - hhmm_to_minutes(previous["depart"])
        )

        if actual_travel != expected_travel:
            violations.append(
                "TRAVEL_TIME_MISMATCH:"
                f"{previous_location}->{current_location}:"
                f"expected={expected_travel}:actual={actual_travel}"
            )

        total_travel += expected_travel

    for row in route_rows:
        location_id = row["location_id"]

        if row.get("visit", False):
            actual_visit = hhmm_to_minutes(row["depart"]) - hhmm_to_minutes(row["arrive"])

            if actual_visit != visit_duration:
                violations.append(
                    f"VISIT_DURATION_MISMATCH:{location_id}:"
                    f"expected={visit_duration}:actual={actual_visit}"
                )

            total_visit += actual_visit

        if location_id in windows:
            arrive = hhmm_to_minutes(row["arrive"])
            depart = hhmm_to_minutes(row["depart"])
            window = windows[location_id]

            if "not_before" in window and arrive < hhmm_to_minutes(window["not_before"]):
                violations.append(
                    f"TIME_WINDOW_EARLY:{location_id}:"
                    f"arrive={row['arrive']}:not_before={window['not_before']}"
                )

            if "not_after" in window and depart > hhmm_to_minutes(window["not_after"]):
                violations.append(
                    f"TIME_WINDOW_LATE:{location_id}:"
                    f"depart={row['depart']}:not_after={window['not_after']}"
                )

    if hhmm_to_minutes(finish_time) > hhmm_to_minutes(deadline):
        violations.append(
            f"DEADLINE_MISSED:finish={finish_time}:deadline={deadline}"
        )

    oracle = spec.get("oracle", {})

    if oracle:
        if route != list(oracle.get("route", [])):
            violations.append("ORACLE_ROUTE_MISMATCH")

        if finish_time != oracle.get("finish_time"):
            violations.append("ORACLE_FINISH_TIME_MISMATCH")

        if total_travel != int(oracle.get("total_travel_minutes", total_travel)):
            violations.append("ORACLE_TRAVEL_TIME_MISMATCH")

        if total_visit != int(oracle.get("total_visit_minutes", total_visit)):
            violations.append("ORACLE_VISIT_TIME_MISMATCH")

        total_minutes = total_travel + total_visit

        if total_minutes != int(oracle.get("total_minutes", total_minutes)):
            violations.append("ORACLE_TOTAL_TIME_MISMATCH")

    return P1CampusTourTraceMetrics(
        route=route,
        feasible=not violations,
        violations=violations,
        start_time=start_time,
        finish_time=finish_time,
        deadline=deadline,
        total_travel_minutes=total_travel,
        total_visit_minutes=total_visit,
        total_minutes=total_travel + total_visit,
    )

    