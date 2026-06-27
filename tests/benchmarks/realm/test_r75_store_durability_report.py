from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r75_store_durability_report import (
    run_r75_store_durability_report,
)


def test_r75_store_durability_report_generates_expected_summary(tmp_path: Path):
    result = run_r75_store_durability_report(tmp_path)

    assert result.restart_persistence_verified is True
    assert result.replay_after_reopen_verified is True
    assert result.idempotent_retry_after_reopen_verified is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r75_store_durability_report.v1"
    assert report["summary"]["decision"] == "sqlite_store_durability_and_migration_readiness_established"
    assert report["summary"]["reopened_event_ids"] == ["r75-event-1", "r75-event-2"]
    assert report["summary"]["replay_sequence"] == ["r75-event-1", "r75-event-2"]
    assert report["summary"]["event_count_after_duplicate_retry"] == 2
    assert report["summary"]["duplicate_result_event_id"] == "r75-event-1"

    assert report["claims"]["sqlite_restart_persistence_claimed"] is True
    assert report["claims"]["replay_after_reopen_claimed"] is True
    assert report["claims"]["postgres_claimed"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r75_store_durability_report_is_human_readable(tmp_path: Path):
    result = run_r75_store_durability_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.5 Store Durability and Migration Readiness Report" in md
    assert "Restart persistence verified: True" in md
    assert "Replay after reopen verified: True" in md
    assert "postgres_claimed: False" in md
    assert "production_runtime_claimed: False" in md


def test_committed_r75_store_durability_report_is_current(tmp_path: Path):
    generated = run_r75_store_durability_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r75_store_durability_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r75_store_durability_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
