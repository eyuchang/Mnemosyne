from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_jssp_j1_j4_suite import run_jssp_j1_j4_suite


def test_jssp_j1_j4_suite_summarizes_r6_boundaries(tmp_path: Path):
    result = run_jssp_j1_j4_suite(tmp_path)

    assert result.readiness_decision == "ready_for_executable_j1_j4_baselines"
    assert result.static_case_count == 2
    assert result.dynamic_contract_case_count == 2
    assert result.j2_api_bound is True
    assert result.j4_material_recovery is True
    assert result.j4_api_bound is False

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "realm_jssp_j1_j4_suite_report.v2"
    assert report["summary"]["j2_api_bound_recovery"] is True
    assert report["summary"]["j4_material_recovery_baseline"] is True
    assert report["summary"]["j4_api_bound_recovery"] is False
    assert report["summary"]["production_runtime_claimed"] is False
    assert report["summary"]["durable_logs_claimed"] is False
    assert report["summary"]["r6_j1_j4_executable_layer_complete"] is True

    coverage = {row["case_id"]: row for row in report["case_coverage"]}
    assert coverage["J1"]["r6_status"] == "deterministic_static_baseline"
    assert coverage["J2"]["r6_status"] == "deterministic_recovery_and_api_bound_commitment_recovery"
    assert coverage["J3"]["r6_status"] == "deterministic_static_baseline"
    assert coverage["J4"]["r6_status"] == "deterministic_material_resource_recovery_baseline"
    assert coverage["J4"]["claim_boundary"] == "benchmark_local_material_recovery_not_api_bound"


def test_jssp_j1_j4_suite_report_is_human_readable(tmp_path: Path):
    result = run_jssp_j1_j4_suite(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM J1-J4 JSSP Suite Report" in md
    assert "J2 has deterministic recovery plus API-bound recovery" in md
    assert "J4 now has deterministic benchmark-local material/resource recovery." in md
    assert "J4 is not yet API-bound to active commitment memory." in md
    assert "without claiming production-runtime durable recovery" in md


def test_committed_jssp_j1_j4_suite_report_is_current(tmp_path: Path):
    generated = run_jssp_j1_j4_suite(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/jssp_j1_j4_suite_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/jssp_j1_j4_suite_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
