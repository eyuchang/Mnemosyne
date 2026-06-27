from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_r76_postgres_conformance_boundary import (
    inspect_r76_postgres_conformance_boundary,
)


def test_r76_postgres_conformance_boundary_inspection_generates_report(tmp_path: Path):
    result = inspect_r76_postgres_conformance_boundary(tmp_path)

    assert result.sqlite_table_count >= 2
    assert result.required_postgres_table_count == 2
    assert result.decision == "postgres_conformance_boundary_ready_for_contract_tests"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r76_postgres_conformance_boundary_inspection.v1"
    assert report["summary"]["decision"] == "postgres_conformance_boundary_ready_for_contract_tests"

    assert "store_schema_metadata" in report["required_postgres_tables"]
    assert "recovery_events" in report["required_postgres_tables"]

    requirement_ids = {
        item["id"] for item in report["postgres_conformance_requirements"]
    }
    assert "postgres_recovery_events_unique_event_id" in requirement_ids
    assert "postgres_recovery_events_unique_idempotency_key" in requirement_ids
    assert "postgres_recovery_events_unique_sequence_no" in requirement_ids
    assert "postgres_default_ci_skip" in requirement_ids

    assert report["claims"]["postgres_conformance_boundary_defined"] is True
    assert report["claims"]["postgres_schema_draft_defined"] is True
    assert report["claims"]["live_postgres_required"] is False
    assert report["claims"]["postgres_adapter_implemented"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r76_postgres_conformance_boundary_report_is_human_readable(tmp_path: Path):
    result = inspect_r76_postgres_conformance_boundary(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.6 PostgreSQL Conformance Boundary Inspection" in md
    assert "postgres_conformance_boundary_ready_for_contract_tests" in md
    assert "CREATE TABLE recovery_events" in md
    assert "live_postgres_required: False" in md
    assert "postgres_adapter_implemented: False" in md


def test_committed_r76_postgres_conformance_boundary_report_is_current(tmp_path: Path):
    generated = inspect_r76_postgres_conformance_boundary(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r76_postgres_conformance_boundary_inspection.json"),
        "report_markdown": Path("benchmarks/realm/reports/r76_postgres_conformance_boundary_inspection.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
