from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_thanksgiving_suite import run_suite


def test_thanksgiving_suite_generates_index_report(tmp_path: Path):
    result = run_suite(tmp_path)

    assert result.p6_feasible is True
    assert result.p9_feasible is True
    assert result.wakeup_count == 2
    assert result.proposal_count == 1
    assert result.admitted_repair_count == 1
    assert result.api_bound_registered_commitments == 4
    assert result.api_bound_fired_commitments == 2
    assert result.api_bound_proposal_packages == 1
    assert result.api_bound_admitted_repairs == 1

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["suite_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "thanksgiving_suite_report.v1"
    assert report["suite_id"] == "thanksgiving_p6_p9_suite"
    assert report["summary"] == {
        "admitted_repair_count": 1,
        "api_bound_admitted_repairs": 1,
        "api_bound_fired_commitments": 2,
        "api_bound_proposal_packages": 1,
        "api_bound_registered_commitments": 4,
        "optimality_status": "feasible_not_proven_optimal",
        "p6_feasible": True,
        "p9_feasible_after_repair": True,
        "proposal_count": 1,
        "wakeup_count": 2,
    }

    assert [
        item["path"]
        for item in report["generated_reports"]
    ] == [
        "benchmarks/realm/reports/thanksgiving_p6_p9_report.md",
        "benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md",
        "benchmarks/realm/reports/thanksgiving_suite_report.md",
        "benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.md",
    ]

    md = result.files["suite_markdown"].read_text(encoding="utf-8")
    assert "# Thanksgiving Benchmark Suite Report" in md
    assert "P6 feasible: True" in md
    assert "P9 feasible after repair: True" in md
    assert "Recovery wakeups: 2" in md
    assert "P9 recovery lineage" in md
    assert "P9 API-bound recovery report" in md
    assert "API-bound registered commitments: 4" in md


def test_thanksgiving_suite_committed_report_is_current(tmp_path: Path):
    generated = run_suite(tmp_path)

    committed = {
        "suite_json": Path("benchmarks/realm/reports/thanksgiving_suite_report.json"),
        "suite_markdown": Path("benchmarks/realm/reports/thanksgiving_suite_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )



def test_thanksgiving_suite_includes_api_bound_recovery_artifacts(tmp_path: Path):
    result = run_suite(tmp_path)

    suite = json.loads(result.files["suite_json"].read_text(encoding="utf-8"))

    assert suite["generated_api_bound_artifacts"] == [
        {
            "name": "P9 API-bound recovery",
            "path": "benchmarks/realm/api_bound/p9_thanksgiving_api_bound_recovery.json",
        }
    ]

    assert (
        tmp_path / "api_bound" / "p9_thanksgiving_api_bound_recovery.json"
    ).exists()
    assert (
        tmp_path / "reports" / "thanksgiving_api_bound_recovery_report.md"
    ).exists()
