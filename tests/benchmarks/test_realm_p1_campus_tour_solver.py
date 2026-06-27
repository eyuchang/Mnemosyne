# File: tests/benchmarks/test_realm_p1_campus_tour_solver.py
#
# Purpose:
#   Verify Stage 1.6R-P1B Campus Tour solver/planner boundary.
#
# Important:
#   This is a local P1-compatible solver boundary.
#   It does not claim official REALM-Bench scoring.
#
# Run explicitly with:
#   python -m pytest -q -m realm

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.apps import AppRegistry
from mnemosyne.apps.campus_tour import CampusTourApp
from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.apps.rideshare import RideshareApp
from mnemosyne.apps.travel import TravelApp
from mnemosyne.benchmarks import run_realm_case
from mnemosyne.benchmarks.p1_campus_tour_solver import (
    p1_solved_benchmark_case_from_dict,
    solve_p1_campus_tour,
)
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore


P1_SOLVER_CASE_PATH = Path("benchmarks/realm/p1_solver/campus_tour_solver_001.json")


def make_store() -> SQLiteStore:
    return SQLiteStore()


def make_validator() -> Validator:
    registry = AppRegistry()
    registry.register(RideshareApp())
    registry.register(TravelApp())
    registry.register(JSSPApp())
    registry.register(CampusTourApp())

    return Validator(
        registry.build_fsm_registry(),
        registry.build_constraint_registry(),
    )


@pytest.mark.realm
def test_p1_solver_derives_shortest_feasible_route_from_constraints():
    data = json.loads(P1_SOLVER_CASE_PATH.read_text(encoding="utf-8"))

    assert data["official_realm_bench"] is False
    assert "route" not in data["realm_bench"]
    assert "oracle" not in data["realm_bench"]

    plan = solve_p1_campus_tour(data)

    assert plan.feasible
    assert plan.violations == []
    assert plan.route == ["S", "D", "A", "B", "L", "S"]
    assert plan.start_time == "09:00"
    assert plan.finish_time == "12:10"
    assert plan.deadline == "17:00"
    assert plan.total_travel_minutes == 70
    assert plan.total_visit_minutes == 120
    assert plan.total_minutes == 190


@pytest.mark.realm
@pytest.mark.asyncio
async def test_p1_solver_discovered_plan_commits_through_mnemosyne_kernel():
    data = json.loads(P1_SOLVER_CASE_PATH.read_text(encoding="utf-8"))
    case = p1_solved_benchmark_case_from_dict(data)

    result = await run_realm_case(
        case=case,
        store=make_store(),
        validator=make_validator(),
    )

    assert result.ok
    assert result.case_id == "local-p1-compatible-campus-tour-solver-001"
    assert result.error_codes == []
    assert result.error_message is None

    assert result.details["official_realm_bench"] is False
    assert result.details["p1_trace"]["feasible"] is True
    assert result.details["p1_trace"]["violations"] == []
    assert result.details["p1_trace"]["route"] == ["S", "D", "A", "B", "L", "S"]
    assert result.details["p1_trace"]["finish_time"] == "12:10"
    assert result.details["observed"]["committed"] is True

    assert result.metrics is not None
    assert result.metrics.final_state == "completed"
    assert result.metrics.total_records == 5
    assert result.metrics.effective_records == 5
    assert result.metrics.ineffective_records == 0
    assert result.metrics.outbox_rows == 0
    assert result.metrics.state_version == 5