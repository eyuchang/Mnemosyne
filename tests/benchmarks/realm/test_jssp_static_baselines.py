from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_jssp_static_baselines import run_static_baselines


def test_jssp_static_baselines_generate_j1_j3_artifacts(tmp_path: Path):
    result = run_static_baselines(tmp_path)

    assert result.case_count == 2
    assert result.feasible_count == 2
    assert result.optimality_status == "feasible_not_proven_optimal"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    j1 = json.loads(result.files["j1_baseline_json"].read_text(encoding="utf-8"))
    j3 = json.loads(result.files["j3_baseline_json"].read_text(encoding="utf-8"))

    assert j1["case_id"] == "J1"
    assert j1["case_type"] == "jssp_static"
    assert j1["complexity"] == "simple"
    assert j1["schedule_summary"]["feasible"] is True
    assert j1["schedule_summary"]["requires_recovery"] is False
    assert j1["evaluation"]["optimality_status"] == "feasible_not_proven_optimal"

    assert j3["case_id"] == "J3"
    assert j3["case_type"] == "jssp_static"
    assert j3["complexity"] == "complex"
    assert j3["schedule_summary"]["feasible"] is True
    assert j3["schedule_summary"]["requires_recovery"] is False
    assert j3["evaluation"]["optimality_status"] == "feasible_not_proven_optimal"

    assert j1["case_digest"] != j3["case_digest"]


def test_jssp_static_baselines_report_is_human_readable(tmp_path: Path):
    result = run_static_baselines(tmp_path)

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))
    assert report["schema_version"] == "realm_jssp_static_baselines_report.v1"
    assert report["summary"] == {
        "case_count": 2,
        "feasible_count": 2,
        "optimality_status": "feasible_not_proven_optimal",
    }

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM JSSP Static Baselines Report" in md
    assert "J1 and J3 static JSSP case files are executable benchmark inputs." in md
    assert "Do not claim J2/J4 dynamic recovery." in md


def test_committed_jssp_static_baseline_artifacts_are_current(tmp_path: Path):
    generated = run_static_baselines(tmp_path)

    committed = {
        "j1_baseline_json": Path("benchmarks/realm/solutions/j1_jssp_static_baseline.json"),
        "j3_baseline_json": Path("benchmarks/realm/solutions/j3_jssp_static_baseline.json"),
        "report_json": Path("benchmarks/realm/reports/jssp_static_baselines_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/jssp_static_baselines_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
