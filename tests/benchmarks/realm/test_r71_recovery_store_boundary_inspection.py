from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_r7_recovery_store_boundary import (
    inspect_r7_recovery_store_boundary,
)


def test_r71_recovery_store_boundary_inspection_generates_report(tmp_path: Path):
    result = inspect_r7_recovery_store_boundary(tmp_path)

    assert result.inspected_file_count > 0
    assert result.recovery_related_file_count > 0
    assert result.decision == "ready_for_store_protocol_refactor"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r7_recovery_store_boundary_inspection.v1"
    assert report["summary"]["decision"] == "ready_for_store_protocol_refactor"
    assert report["claims"] == {
        "inspection_only": True,
        "kubernetes_claimed": False,
        "postgres_claimed": False,
        "production_runtime_claimed": False,
        "store_protocol_refactor_claimed": False,
        "temporal_claimed": False,
    }

    targets = "\n".join(report["recommended_refactor_targets"])
    assert "RecoveryStore protocol" in targets
    assert "SQLiteStore" in targets
    assert "PostgreSQL" in targets


def test_r71_recovery_store_boundary_report_is_human_readable(tmp_path: Path):
    result = inspect_r7_recovery_store_boundary(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.1 Recovery Store Boundary Inspection" in md
    assert "R7 begins by identifying recovery" in md
    assert "R7.1 does not claim Postgres support" in md
    assert "ready_for_store_protocol_refactor" in md


def test_committed_r71_recovery_store_boundary_report_is_current(tmp_path: Path):
    generated = inspect_r7_recovery_store_boundary(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r71_recovery_store_boundary_inspection.json"),
        "report_markdown": Path("benchmarks/realm/reports/r71_recovery_store_boundary_inspection.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
