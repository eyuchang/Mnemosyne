from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r73_recovery_replay_report import (
    run_r73_recovery_replay_report,
)


def test_r73_recovery_replay_report_generates_expected_summary(tmp_path: Path):
    result = run_r73_recovery_replay_report(tmp_path)

    assert result.replayed_event_count == 3
    assert result.duplicate_event_count == 2
    assert result.terminal_event_seen is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r73_recovery_replay_report.v1"
    assert report["summary"]["deterministic_sequence_order"] == [
        "r73-event-1",
        "r73-event-2",
        "r73-event-3",
    ]
    assert report["summary"]["duplicate_replay_tolerance_checked"] is True
    assert report["summary"]["duplicate_replay_duplicate_count"] == 2
    assert report["claims"]["durable_event_log_replay_claimed"] is True
    assert report["claims"]["production_runtime_claimed"] is False


def test_r73_recovery_replay_report_is_human_readable(tmp_path: Path):
    result = run_r73_recovery_replay_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.3 Recovery Replay and Idempotency Report" in md
    assert "Duplicate replay tolerance checked: True" in md
    assert "production_runtime_claimed: False" in md


def test_committed_r73_recovery_replay_report_is_current(tmp_path: Path):
    generated = run_r73_recovery_replay_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r73_recovery_replay_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r73_recovery_replay_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
