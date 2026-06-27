from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_thanksgiving_recovery_trace import run_recovery_trace


def test_thanksgiving_recovery_trace_generates_lifecycle_artifacts(tmp_path: Path):
    result = run_recovery_trace(tmp_path)

    assert result.trace_id == "p9_thanksgiving_recovery_trace"
    assert result.wakeup_count == 2
    assert result.proposal_count == 1
    assert result.admitted_repair_count == 1

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    trace = json.loads(result.files["trace_json"].read_text(encoding="utf-8"))

    assert trace["schema_version"] == "thanksgiving_recovery_trace.v1"
    assert trace["case_id"] == "P9"
    assert trace["source_case"] == "P6"

    assert trace["disruption_event"]["person"] == "James"
    assert trace["disruption_event"]["notice_time_est"] == "10:00"
    assert trace["disruption_event"]["original_arrival_time"] == "13:00"
    assert trace["disruption_event"]["new_arrival_time"] == "16:00"
    assert trace["disruption_event"]["delay_minutes"] == 180

    affected = [
        commitment["commitment_id"]
        for commitment in trace["commitments"]
        if commitment["affected_by_disruption"]
    ]
    assert affected == [
        "p9-pickup-grandma-by-james",
        "p9-dinner-ready-by-1800",
    ]

    assert [wakeup["commitment_id"] for wakeup in trace["wakeups"]] == [
        "p9-pickup-grandma-by-james",
        "p9-dinner-ready-by-1800",
    ]
    assert all(wakeup["wakeup_time"] == "10:00" for wakeup in trace["wakeups"])

    proposal = trace["proposals"][0]
    assert proposal["status"] == "selected"
    assert proposal["changes"][0] == {
        "after": "Sarah",
        "before": "James",
        "field": "Grandma pickup assignee",
    }

    admission = trace["admissions"][0]
    assert admission["admission_boundary"] == "domain_validated_repair"
    assert admission["status"] == "admitted"
    assert admission["admitted_at"] == "10:00"
    assert all(check["passed"] for check in admission["validation_checks"])

    assert trace["result"]["feasible_after_repair"] is True
    assert trace["result"]["latest_family_home_time"] == "17:30"
    assert trace["result"]["dinner_ready_time"] == "18:00"


def test_thanksgiving_recovery_trace_report_contains_lineage(tmp_path: Path):
    result = run_recovery_trace(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")

    assert "# Thanksgiving P9 Recovery Trace Report" in md
    assert "## Disruption" in md
    assert "## Commitment Wakeups" in md
    assert "## Repair Proposals" in md
    assert "## Repair Admission" in md
    assert "## Audit Lineage" in md
    assert "James flight delay notice received at 10:00" in md
    assert "Grandma pickup assignee: James -> Sarah" in md
    assert "Feasible after repair: True" in md


def test_committed_thanksgiving_recovery_trace_artifacts_are_current(tmp_path: Path):
    generated = run_recovery_trace(tmp_path)

    committed = {
        "trace_json": Path("benchmarks/realm/evaluations/p9_thanksgiving_recovery_trace.json"),
        "report_json": Path("benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
