from __future__ import annotations

import json
from pathlib import Path

from mnemosyne.benchmarks.skeleton_family_runner import (
    discover_case_paths,
    main,
    row_from_skeleton,
)


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_skeleton_family_runner_discovers_default_fixture_families():
    paths = discover_case_paths(
        [
            Path("benchmarks/realm/p2_skeleton"),
            Path("benchmarks/realm/p3_skeleton"),
            Path("benchmarks/realm/p5_skeleton"),
        ]
    )

    case_names = {path.name for path in paths}

    assert "multi_group_tour_001.json" in case_names
    assert "multi_group_tour_expected_negative_001.json" in case_names
    assert "urban_rideshare_001.json" in case_names
    assert "urban_rideshare_expected_negative_001.json" in case_names
    assert "event_logistics_001.json" in case_names
    assert "event_logistics_expected_negative_001.json" in case_names


def test_skeleton_family_runner_marks_feasible_case_as_report_only_ok():
    row = row_from_skeleton(
        Path("benchmarks/realm/p2_skeleton/multi_group_tour_001.json")
    )

    assert row["ok"] is True
    assert row["committed_rids"] == []
    assert row["error_codes"] == []
    assert row["metrics"]["report_only"] is True
    assert row["details"]["observed"]["committed"] is False
    assert row["details"]["observed"]["report_only"] is True


def test_skeleton_family_runner_marks_expected_negative_case_as_report_only_failure():
    row = row_from_skeleton(
        Path("benchmarks/realm/p3_skeleton/urban_rideshare_expected_negative_001.json")
    )

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert row["error_codes"] == ["EXPECTED_NEGATIVE_SKELETON"]
    assert row["error_message"] == "expected-negative skeleton fixture"
    assert row["details"]["expected_rejection_reason"] == "VEHICLE_CAPACITY_EXCEEDED"
    assert row["details"]["observed"]["committed"] is False
    assert row["details"]["observed"]["report_only"] is True


def test_skeleton_family_runner_writes_reportable_rows(tmp_path: Path):
    output_path = tmp_path / "skeleton_families.jsonl"

    exit_code = main(
        [
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    rows = read_jsonl(output_path)

    assert len(rows) == 6

    ok_rows = [row for row in rows if row["ok"]]
    failed_rows = [row for row in rows if not row["ok"]]

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

    assert all(row["committed_rids"] == [] for row in rows)
    assert all(row["details"]["observed"]["committed"] is False for row in rows)
    assert all(row["details"]["observed"]["report_only"] is True for row in rows)
