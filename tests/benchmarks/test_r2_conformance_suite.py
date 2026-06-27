from __future__ import annotations

import json
from pathlib import Path


RESULTS = Path("results/r2")
REPORTS = Path("reports/r2")


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_r2_evidence_files_exist():
    required_results = [
        RESULTS / "external_json_solver_001.jsonl",
        RESULTS / "external_json_bad_deadline_001.jsonl",
        RESULTS / "stale_world_repair_1300.jsonl",
        RESULTS / "rejection_audit_fixture.jsonl",
        RESULTS / "skeleton_families.jsonl",
    ]

    required_reports = [
        REPORTS / "external_json_solver_001_audit.md",
        REPORTS / "external_json_bad_deadline_001_audit.md",
        REPORTS / "stale_world_repair_1300_audit.md",
        REPORTS / "rejection_audit_fixture_report.md",
        REPORTS / "skeleton_families_audit.md",
    ]

    for path in [*required_results, *required_reports]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path


def test_r2_external_json_good_proposal_commits():
    rows = read_jsonl(RESULTS / "external_json_solver_001.jsonl")

    assert len(rows) == 1

    row = rows[0]

    assert row["ok"] is True
    assert row["committed_rids"]
    assert row["error_codes"] == []
    assert row["error_message"] is None
    assert row["details"]["observed"]["committed"] is True
    assert row["metrics"]["final_state"] == "completed"


def test_r2_external_json_bad_deadline_rejects_before_commit():
    rows = read_jsonl(RESULTS / "external_json_bad_deadline_001.jsonl")

    assert len(rows) == 1

    row = rows[0]

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert row["error_codes"] == ["SOLVER_FAILED"]
    assert row["details"]["observed"]["committed"] is False

    certificate = row["details"]["solver_certificate"]
    assert certificate["feasible"] is False
    assert any(
        "finishes after deadline" in violation
        for violation in certificate["violations"]
    )


def test_r2_stale_world_repair_can_commit_after_repair():
    rows = read_jsonl(RESULTS / "stale_world_repair_1300.jsonl")

    assert len(rows) == 1

    row = rows[0]

    assert row["ok"] is True
    assert row["committed_rids"]
    assert row["error_codes"] == []
    assert row["error_message"] is None
    assert row["details"]["observed"]["committed"] is True
    assert row["metrics"]["final_state"] == "completed"


def test_r2_rejection_audit_fixture_contains_only_failed_rows():
    rows = read_jsonl(RESULTS / "rejection_audit_fixture.jsonl")

    assert len(rows) == 2

    for row in rows:
        assert row["ok"] is False
        assert row["committed_rids"] == []
        assert row["error_codes"]
        assert row["details"]["observed"]["committed"] is False


def test_r2_skeleton_families_are_report_only():
    rows = read_jsonl(RESULTS / "skeleton_families.jsonl")

    assert len(rows) == 6

    ok_rows = [row for row in rows if row["ok"] is True]
    failed_rows = [row for row in rows if row["ok"] is False]

    assert len(ok_rows) == 3
    assert len(failed_rows) == 3

    assert {
        row["details"]["family"]
        for row in ok_rows
    } == {"P2", "P3", "P5"}

    assert {
        row["details"]["family"]
        for row in failed_rows
    } == {"P2", "P3", "P5"}

    for row in rows:
        assert row["committed_rids"] == []
        assert row["details"]["observed"]["committed"] is False
        assert row["details"]["observed"]["report_only"] is True

    for row in failed_rows:
        assert row["error_codes"] == ["EXPECTED_NEGATIVE_SKELETON"]


def test_r2_audit_reports_render_key_outcomes():
    report_expectations = {
        REPORTS / "external_json_solver_001_audit.md": [
            "external json",
            "committed",
        ],
        REPORTS / "external_json_bad_deadline_001_audit.md": [
            "SOLVER_FAILED",
        ],
        REPORTS / "stale_world_repair_1300_audit.md": [
            "stale",
            "repair",
        ],
        REPORTS / "rejection_audit_fixture_report.md": [
            "rejected",
        ],
        REPORTS / "skeleton_families_audit.md": [
            "EXPECTED_NEGATIVE_SKELETON",
        ],
    }

    for path, needles in report_expectations.items():
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()

        for needle in needles:
            assert needle.lower() in lowered, (path, needle)
