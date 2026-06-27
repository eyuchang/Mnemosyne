from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r77_postgres_adapter_skeleton_report import (
    run_r77_postgres_adapter_skeleton_report,
)


def test_r77_postgres_adapter_skeleton_report_generates_expected_summary(tmp_path: Path):
    result = run_r77_postgres_adapter_skeleton_report(tmp_path)

    assert result.default_store_type == "SQLiteStore"
    assert result.postgres_store_type == "PostgresStore"
    assert result.default_ci_safe is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r77_postgres_adapter_skeleton_report.v1"
    assert report["summary"]["decision"] == "optional_postgres_adapter_skeleton_and_factory_established"
    assert report["summary"]["default_backend"] == "sqlite"
    assert report["summary"]["postgres_backend"] == "postgres"
    assert report["summary"]["postgres_configured"] is True
    assert report["summary"]["postgres_redacted_database_url"] == "postgresql://***:***@localhost:5432/mnemosyne"

    assert report["claims"]["postgres_adapter_skeleton_claimed"] is True
    assert report["claims"]["store_factory_claimed"] is True
    assert report["claims"]["live_postgres_persistence_claimed"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r77_postgres_adapter_skeleton_report_is_human_readable(tmp_path: Path):
    result = run_r77_postgres_adapter_skeleton_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.7 Optional PostgreSQL Adapter Skeleton Report" in md
    assert "Default store type: `SQLiteStore`" in md
    assert "PostgreSQL store type: `PostgresStore`" in md
    assert "live_postgres_persistence_claimed: False" in md


def test_committed_r77_postgres_adapter_skeleton_report_is_current(tmp_path: Path):
    generated = run_r77_postgres_adapter_skeleton_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r77_postgres_adapter_skeleton_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r77_postgres_adapter_skeleton_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
