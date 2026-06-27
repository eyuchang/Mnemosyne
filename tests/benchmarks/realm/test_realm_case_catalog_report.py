from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.generate_case_catalog_report import run_report


def test_realm_case_catalog_report_exports_problems_disruptions_and_readiness(
    tmp_path: Path,
):
    result = run_report(tmp_path)

    assert result.case_count == 14
    assert result.dynamic_case_ids == ["P4", "P7", "P8", "P9", "P10", "J2", "J4"]
    assert result.thanksgiving_static_case_id == "P6"
    assert result.thanksgiving_dynamic_case_id == "P9"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "realm_case_catalog_report.v1"
    assert report["case_count"] == 14
    assert len(report["cases"]) == 14

    assert report["thanksgiving"]["static"]["case_id"] == "P6"
    assert report["thanksgiving"]["dynamic"]["case_id"] == "P9"

    disruption = report["thanksgiving"]["dynamic"]["disruption"]
    assert disruption == {
        "delay_minutes": 180,
        "early_notice_minutes": 180,
        "new_arrival_time": "16:00",
        "notice_time_est": "10:00",
        "original_arrival_time": "13:00",
        "person": "James",
    }

    readiness = report["thanksgiving"]["readiness_result"]
    assert readiness == {
        "evaluation_available": False,
        "executable_solver_result": "not_run_in_r6.4",
        "next_step": "R6.5 executable Thanksgiving P6/P9 benchmark",
        "problem_extracted": True,
        "solution_available": False,
        "typed_adapter_loaded": True,
    }

    md = result.files["markdown"].read_text(encoding="utf-8")
    assert "# REALM-Bench Case Catalog Report" in md
    assert "## Case Index" in md
    assert "## Dynamic Disruptions" in md
    assert "## Thanksgiving Static Case: P6" in md
    assert "## Thanksgiving Dynamic Case: P9" in md
    assert "Person delayed: James" in md
    assert "Early notice window: 180 minutes" in md


def test_committed_realm_case_catalog_report_is_current(tmp_path: Path):
    generated = run_report(tmp_path)

    committed_dir = Path("benchmarks/realm/reports")
    committed_json = committed_dir / "realm_case_catalog_report.json"
    committed_md = committed_dir / "realm_case_catalog_report.md"

    run_report(committed_dir)

    assert committed_json.exists()
    assert committed_md.exists()
    assert committed_json.read_text(encoding="utf-8") == generated.files["json"].read_text(
        encoding="utf-8"
    )
    assert committed_md.read_text(encoding="utf-8") == generated.files["markdown"].read_text(
        encoding="utf-8"
    )
