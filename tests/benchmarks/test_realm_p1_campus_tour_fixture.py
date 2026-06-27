# File: tests/benchmarks/test_realm_p1_campus_tour_fixture.py
#
# Purpose:
#   Verify Stage 1.6R-P1A Campus Tour fixture replay and oracle validation.
#
# Important:
#   These tests validate representation and replay of P1-compatible local traces.
#   They do not claim that Mnemosyne has solved official REALM-Bench P1.
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
from mnemosyne.benchmarks import load_benchmark_case, run_realm_case
from mnemosyne.benchmarks.p1_campus_tour import validate_p1_campus_tour_trace
from mnemosyne.benchmarks.realm_runner import run_realm_cli_async
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore


P1_CASE_DIR = Path("benchmarks/realm/p1")
P1_POSITIVE_CASE_PATH = P1_CASE_DIR / "campus_tour_static_001.json"
P1_NEGATIVE_CASE_PATH = P1_CASE_DIR / "campus_tour_static_time_window_violation_001.json"


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
def test_p1_campus_tour_positive_oracle_trace_is_feasible():
    data = json.loads(P1_POSITIVE_CASE_PATH.read_text(encoding="utf-8"))

    assert data["case_id"] == "local-p1-compatible-campus-tour-static-001"
    assert data["official_realm_bench"] is False
    assert "Not an official REALM-Bench fixture" in data["provenance"]["note"]

    trace_metrics = validate_p1_campus_tour_trace(data)

    assert trace_metrics.feasible
    assert trace_metrics.violations == []
    assert trace_metrics.route == ["S", "D", "A", "B", "L", "S"]
    assert trace_metrics.start_time == "09:00"
    assert trace_metrics.finish_time == "12:10"
    assert trace_metrics.deadline == "17:00"
    assert trace_metrics.total_travel_minutes == 70
    assert trace_metrics.total_visit_minutes == 120
    assert trace_metrics.total_minutes == 190


@pytest.mark.realm
def test_p1_campus_tour_negative_oracle_trace_is_infeasible():
    data = json.loads(P1_NEGATIVE_CASE_PATH.read_text(encoding="utf-8"))

    assert data["case_id"] == "local-p1-compatible-campus-tour-time-window-violation-001"
    assert data["official_realm_bench"] is False
    assert "Not an official REALM-Bench fixture" in data["provenance"]["note"]

    trace_metrics = validate_p1_campus_tour_trace(data)

    assert not trace_metrics.feasible
    assert any(
        violation.startswith("TIME_WINDOW_EARLY:L")
        for violation in trace_metrics.violations
    )


@pytest.mark.realm
@pytest.mark.asyncio
async def test_p1_campus_tour_positive_fixture_replays_through_mnemosyne_kernel():
    case = load_benchmark_case(P1_POSITIVE_CASE_PATH)

    result = await run_realm_case(
        case=case,
        store=make_store(),
        validator=make_validator(),
    )

    assert result.ok
    assert result.error_codes == []
    assert result.error_message is None
    assert result.case_id == "local-p1-compatible-campus-tour-static-001"
    assert result.committed_rids == [
        "realm-local-p1-compatible-campus-tour-static-001-visit_dorm",
        "realm-local-p1-compatible-campus-tour-static-001-visit_auditorium",
        "realm-local-p1-compatible-campus-tour-static-001-visit_lab",
        "realm-local-p1-compatible-campus-tour-static-001-visit_library",
        "realm-local-p1-compatible-campus-tour-static-001-return_to_student_center",
    ]

    assert result.details["official_realm_bench"] is False
    assert result.details["p1_trace"]["feasible"] is True
    assert result.details["p1_trace"]["violations"] == []
    assert result.details["p1_trace"]["route"] == ["S", "D", "A", "B", "L", "S"]
    assert result.details["p1_trace"]["total_minutes"] == 190
    assert result.details["observed"]["committed"] is True

    assert result.metrics is not None
    assert result.metrics.total_records == 5
    assert result.metrics.effective_records == 5
    assert result.metrics.ineffective_records == 0
    assert result.metrics.outbox_rows == 0
    assert result.metrics.final_state == "completed"
    assert result.metrics.state_version == 5


@pytest.mark.realm
@pytest.mark.asyncio
async def test_p1_campus_tour_negative_fixture_is_expected_rejection_before_commit():
    case = load_benchmark_case(P1_NEGATIVE_CASE_PATH)

    result = await run_realm_case(
        case=case,
        store=make_store(),
        validator=make_validator(),
    )

    assert result.ok
    assert result.committed_rids == []
    assert result.metrics is None
    assert result.error_message == "expected negative case rejected before commit"
    assert "P1_TRACE_INFEASIBLE" in result.error_codes
    assert any(
        code.startswith("TIME_WINDOW_EARLY:L")
        for code in result.error_codes
    )

    assert result.details["official_realm_bench"] is False
    assert result.details["p1_trace"]["feasible"] is False
    assert any(
        violation.startswith("TIME_WINDOW_EARLY:L")
        for violation in result.details["p1_trace"]["violations"]
    )
    assert result.details["observed"]["committed"] is False


@pytest.mark.realm
@pytest.mark.asyncio
async def test_p1_campus_tour_cli_runner_writes_positive_and_negative_result_jsonl(tmp_path):
    output_path = tmp_path / "p1_campus_tour_static_001.jsonl"

    results, summary = await run_realm_cli_async(
        case_dir=P1_CASE_DIR,
        output_path=output_path,
    )

    assert summary.cases == 2
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.output_path == str(output_path)

    assert [result.case_id for result in results] == [
        "local-p1-compatible-campus-tour-static-001",
        "local-p1-compatible-campus-tour-time-window-violation-001",
    ]
    assert all(result.ok for result in results)

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(rows) == 2

    positive = rows[0]
    negative = rows[1]

    assert positive["case_id"] == "local-p1-compatible-campus-tour-static-001"
    assert positive["ok"] is True
    assert positive["metrics"]["final_state"] == "completed"
    assert positive["metrics"]["total_records"] == 5
    assert positive["details"]["p1_trace"]["feasible"] is True
    assert positive["details"]["p1_trace"]["route"] == ["S", "D", "A", "B", "L", "S"]
    assert positive["details"]["official_realm_bench"] is False
    assert positive["details"]["observed"]["committed"] is True

    assert negative["case_id"] == "local-p1-compatible-campus-tour-time-window-violation-001"
    assert negative["ok"] is True
    assert negative["metrics"] is None
    assert negative["committed_rids"] == []
    assert "P1_TRACE_INFEASIBLE" in negative["error_codes"]
    assert negative["details"]["p1_trace"]["feasible"] is False
    assert negative["details"]["official_realm_bench"] is False
    assert negative["details"]["observed"]["committed"] is False
