from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_r74_validated_admission_report import (
    run_r74_validated_admission_report,
)


def test_r74_validated_admission_report_generates_expected_summary(tmp_path: Path):
    result = run_r74_validated_admission_report(tmp_path)

    assert result.missing_validator_rejected is True
    assert result.missing_store_rejected is True
    assert result.explicit_validator_accepted is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "r74_validated_admission_report.v1"
    assert report["summary"]["decision"] == "validated_public_admission_boundary_established"
    assert report["claims"]["validated_public_admission_boundary_claimed"] is True
    assert report["claims"]["missing_validator_fails_closed_claimed"] is True
    assert report["claims"]["invalid_store_fails_closed_claimed"] is True
    assert report["claims"]["low_level_substrate_removed_claimed"] is False
    assert report["claims"]["production_runtime_claimed"] is False


def test_r74_validated_admission_report_is_human_readable(tmp_path: Path):
    result = run_r74_validated_admission_report(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# R7.4 Validated Recovery Admission Report" in md
    assert "Missing validator rejected: True" in md
    assert "Missing store rejected: True" in md
    assert "low_level_substrate_removed_claimed: False" in md
    assert "production_runtime_claimed: False" in md


def test_committed_r74_validated_admission_report_is_current(tmp_path: Path):
    generated = run_r74_validated_admission_report(tmp_path)

    committed = {
        "report_json": Path("benchmarks/realm/reports/r74_validated_admission_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/r74_validated_admission_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
