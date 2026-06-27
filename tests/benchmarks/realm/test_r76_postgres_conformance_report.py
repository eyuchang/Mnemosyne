from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r76_postgres_conformance_report import (
    POSTGRES_CONFORMANCE_ENV,
    run_r76_postgres_conformance_report,
)


def test_r76_postgres_conformance_report_generates_expected_summary(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(POSTGRES_CONFORMANCE_ENV, raising=False)

    result = run_r76_postgres_conformance_report(tmp_path)

    assert result.live_postgres_required is False
    assert result.default_ci_safe is True
    assert result.decision == "postgres_live_conformance_harness_defined_as_opt_in"

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r76_postgres_conformance_report.v1"
    assert report["summary"]["postgres_conformance_env"] == POSTGRES_CONFORMANCE_ENV
    assert report["summary"]["postgres_conformance_env_present"] is False
    assert report["claims"]["postgres_live_test_harness_defined"] is True
    assert report["claims"]["postgres_live_test_opt_in"] is True
    assert report["claims"]["postgres_adapter_implemented"] is False
    assert report["claims"]["postgres_live_conformance_claimed"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r76_postgres_conformance_report_is_human_readable(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(POSTGRES_CONFORMANCE_ENV, raising=False)

    result = run_r76_postgres_conformance_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.6 PostgreSQL Conformance Report" in md
    assert "Live PostgreSQL required: False" in md
    assert "Default CI safe: True" in md
    assert "postgres_adapter_implemented: False" in md


def test_committed_r76_postgres_conformance_report_is_current(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(POSTGRES_CONFORMANCE_ENV, raising=False)

    generated = run_r76_postgres_conformance_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r76_postgres_conformance_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r76_postgres_conformance_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
