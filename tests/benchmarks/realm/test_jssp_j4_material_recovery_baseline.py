from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_jssp_j4_material_recovery_baseline import (
    run_j4_material_recovery_baseline,
)


def test_j4_material_recovery_baseline_generates_feasible_repair(tmp_path: Path):
    result = run_j4_material_recovery_baseline(tmp_path)

    assert result.operation_count == 20
    assert result.affected_operation_count > 0
    assert result.feasible_after_repair is True
    assert result.repaired_makespan >= result.initial_makespan

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["solution_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "realm_jssp_j4_material_recovery_baseline.v1"
    assert report["case_id"] == "J4"
    assert report["baseline_kind"] == "deterministic_material_resource_recovery"

    material_events = {
        event["material"]: event for event in report["material_events"]
    }
    assert set(material_events) == {"C-X", "F"}
    assert material_events["C-X"]["unavailable_start"] == 4
    assert material_events["C-X"]["unavailable_end"] == 8
    assert material_events["F"]["unavailable_start"] == 6
    assert material_events["F"]["unavailable_end"] == 10

    checks = report["evaluation"]["constraint_checks"]
    assert checks["operation_templates_expanded"] is True
    assert checks["material_events_realized"] is True
    assert checks["affected_operations_detected"] is True
    assert checks["precedence_satisfaction"] is True
    assert checks["machine_capacity_satisfaction"] is True
    assert checks["material_availability_satisfaction"] is True


def test_j4_material_recovery_claims_are_precise(tmp_path: Path):
    result = run_j4_material_recovery_baseline(tmp_path)

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["claims"] == {
        "active_commitment_memory_claimed": False,
        "api_bound_recovery_claimed": False,
        "benchmark_local_recovery_claimed": True,
        "durable_logs_claimed": False,
        "global_optimality_claimed": False,
        "j4_material_recovery_claimed": True,
        "material_resource_substrate_claimed": True,
        "production_runtime_claimed": False,
    }

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM J4 Material Recovery Baseline" in md
    assert "J4 names material-unavailability examples" in md
    assert "api_bound_recovery_claimed: False" in md
    assert "production_runtime_claimed: False" in md


def test_committed_j4_material_recovery_artifacts_are_current(tmp_path: Path):
    generated = run_j4_material_recovery_baseline(tmp_path)

    committed = {
        "solution_json": Path("benchmarks/realm/solutions/j4_jssp_material_recovery_baseline.json"),
        "evaluation_json": Path("benchmarks/realm/evaluations/j4_jssp_material_recovery_eval.json"),
        "report_json": Path("benchmarks/realm/reports/j4_jssp_material_recovery_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/j4_jssp_material_recovery_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
