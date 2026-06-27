from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_r74_validated_admission_boundary import (
    inspect_r74_validated_admission_boundary,
)


def test_r74_validated_admission_boundary_inspection_generates_report(tmp_path: Path):
    result = inspect_r74_validated_admission_boundary(tmp_path)

    assert result.inspected_file_count > 0
    assert result.mutation_site_count > 0
    assert result.validator_site_count > 0
    assert result.decision == "ready_for_validated_admission_boundary_hardening"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r74_validated_admission_boundary_inspection.v1"
    assert report["summary"]["decision"] == "ready_for_validated_admission_boundary_hardening"
    assert report["claims"] == {
        "inspection_only": True,
        "kubernetes_claimed": False,
        "mutation_bypass_prevented_claimed": False,
        "postgres_claimed": False,
        "production_runtime_claimed": False,
        "temporal_claimed": False,
        "validated_admission_hardening_claimed": False,
    }

    targets = "\n".join(report["recommended_hardening_targets"])
    assert "validator" in targets
    assert "Fail closed" in targets
    assert "invalid repairs cannot be admitted" in targets


def test_r74_validated_admission_boundary_report_is_human_readable(tmp_path: Path):
    result = inspect_r74_validated_admission_boundary(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.4 Validated Recovery Admission Boundary Inspection" in md
    assert "R7.4 hardens recovery admission" in md
    assert "ready_for_validated_admission_boundary_hardening" in md
    assert "production_runtime_claimed: False" in md


def test_committed_r74_validated_admission_boundary_report_is_current(tmp_path: Path):
    generated = inspect_r74_validated_admission_boundary(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r74_validated_admission_boundary_inspection.json"),
        "report_markdown": Path("benchmarks/realm/reports/r74_validated_admission_boundary_inspection.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
