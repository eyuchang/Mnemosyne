from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r78_postgres_live_adapter_report import (
    run_r78_postgres_live_adapter_report,
)


def test_r78_postgres_live_adapter_report_generates_expected_summary(tmp_path: Path):
    result = run_r78_postgres_live_adapter_report(tmp_path)

    assert result.adapter_event_count == 2
    assert result.conformance_passed is True
    assert result.default_ci_safe is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r78_postgres_live_adapter_report.v1"
    assert report["summary"]["decision"] == "opt_in_postgres_recovery_event_adapter_established"
    assert report["summary"]["event_ids"] == ["r78-event-1", "r78-event-2"]
    assert report["summary"]["replay_event_ids"] == ["r78-event-1", "r78-event-2"]
    assert report["summary"]["duplicate_result_event_id"] == "r78-event-1"

    assert report["claims"]["postgres_recovery_event_adapter_claimed"] is True
    assert report["claims"]["postgres_idempotent_retry_claimed"] is True
    assert report["claims"]["real_postgres_service_required_in_default_ci"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r78_postgres_live_adapter_report_is_human_readable(tmp_path: Path):
    result = run_r78_postgres_live_adapter_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.8 PostgreSQL Live Adapter Report" in md
    assert "Conformance passed: True" in md
    assert "Default CI safe: True" in md
    assert "production_runtime_claimed: False" in md


def test_committed_r78_postgres_live_adapter_report_is_current(tmp_path: Path):
    generated = run_r78_postgres_live_adapter_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r78_postgres_live_adapter_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r78_postgres_live_adapter_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
