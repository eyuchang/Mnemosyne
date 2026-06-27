from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_jssp_j2_recovery_baseline import (
    run_j2_recovery_baseline,
)


def test_j2_recovery_baseline_generates_feasible_repaired_schedule(tmp_path: Path):
    result = run_j2_recovery_baseline(tmp_path)

    assert result.affected_operation_count == 2
    assert result.feasible_after_repair is True
    assert result.initial_makespan == 11
    assert result.repaired_makespan == 14

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    solution = json.loads(result.files["solution_json"].read_text(encoding="utf-8"))

    assert solution["schema_version"] == "realm_jssp_j2_recovery_baseline.v1"
    assert solution["case_id"] == "J2"
    assert solution["disruption"] == {
        "machine": "MachineA",
        "type": "machine_breakdown",
        "unavailable_end": 6,
        "unavailable_start": 4,
    }

    assert [
        item["operation_id"]
        for item in solution["baseline"]["affected_operations"]
    ] == ["Job2:O1", "Job3:O2"]

    checks = solution["evaluation"]["constraint_checks"]
    assert checks == {
        "affected_operations_detected": True,
        "machine_capacity_satisfaction": True,
        "machine_downtime_satisfaction": True,
        "precedence_satisfaction": True,
        "repair_changes_makespan": True,
    }

    assert solution["claims"] == {
        "api_bound_recovery_claimed": False,
        "durable_logs_claimed": False,
        "executable_recovery_baseline": True,
        "j4_full_recovery_claimed": False,
        "production_runtime_claimed": False,
    }


def test_j2_recovery_baseline_report_is_human_readable(tmp_path: Path):
    result = run_j2_recovery_baseline(tmp_path)

    report = json.loads(result.files["evaluation_json"].read_text(encoding="utf-8"))
    assert report["schema_version"] == "realm_jssp_j2_recovery_evaluation.v1"
    assert report["affected_operation_count"] == 2
    assert report["feasible_after_repair"] is True
    assert report["optimality_status"] == "feasible_not_proven_optimal"

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM J2 JSSP Machine-Breakdown Recovery Baseline" in md
    assert "Machine unavailable: `MachineA`" in md
    assert "`Job2:O1`" in md
    assert "`Job3:O2`" in md
    assert "api_bound_recovery_claimed: False" in md
    assert "durable_logs_claimed: False" in md


def test_committed_j2_recovery_baseline_artifacts_are_current(tmp_path: Path):
    generated = run_j2_recovery_baseline(tmp_path)

    committed = {
        "solution_json": Path("benchmarks/realm/solutions/j2_jssp_machine_breakdown_recovery_baseline.json"),
        "evaluation_json": Path("benchmarks/realm/evaluations/j2_jssp_machine_breakdown_recovery_eval.json"),
        "report_json": Path("benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
