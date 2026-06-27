from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_jssp_readiness import run_readiness_report


def test_jssp_j1_j4_readiness_report_detects_cases_and_substrate(tmp_path: Path):
    result = run_readiness_report(tmp_path)

    assert result.case_count == 4
    assert result.available_case_count == 4
    assert result.available_module_count == 8
    assert result.readiness_decision == "ready_for_executable_j1_j4_baselines"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "realm_jssp_readiness.v1"
    assert [case["case_id"] for case in report["cases"]] == ["J1", "J2", "J3", "J4"]
    assert all(case["ready_for_baseline"] for case in report["cases"])

    modules = {module["module"]: module for module in report["modules"]}
    for module_name in [
        "mnemosyne.benchmarks.jssp_disruptions",
        "mnemosyne.benchmarks.jssp_schedule_admission",
        "mnemosyne.benchmarks.jssp_disruption_commitments",
        "mnemosyne.benchmarks.jssp_recovery_proposals",
        "mnemosyne.benchmarks.jssp_repair_admission",
        "mnemosyne.api.commitments",
        "mnemosyne.api.proposal_packages",
        "mnemosyne.api.audit",
    ]:
        assert modules[module_name]["available"] is True
        assert modules[module_name]["public_callables"]

    md = result.files["markdown"].read_text(encoding="utf-8")
    assert "# REALM J1-J4 JSSP Readiness Report" in md
    assert "ready_for_executable_j1_j4_baselines" in md
    assert "Build J1/J3 static executable schedule baselines first." in md
    assert "Do not claim durable production recovery in R6.8." in md


def test_committed_jssp_j1_j4_readiness_report_is_current(tmp_path: Path):
    generated = run_readiness_report(tmp_path)

    committed = {
        "json": Path("benchmarks/realm/reports/jssp_j1_j4_readiness.json"),
        "markdown": Path("benchmarks/realm/reports/jssp_j1_j4_readiness.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
