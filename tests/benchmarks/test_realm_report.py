# File: tests/benchmarks/test_realm_report.py
#
# Purpose:
#   Verify R0.1 human-readable benchmark report generation.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.report import (
    build_markdown_report,
    load_jsonl,
    main,
    summarize_results,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


@pytest.mark.realm
def test_report_summarizes_positive_and_expected_negative_cases(tmp_path: Path):
    rows = [
        {
            "case_id": "local-p1-compatible-campus-tour-static-001",
            "ok": True,
            "committed_rids": ["rid-1", "rid-2", "rid-3", "rid-4", "rid-5"],
            "metrics": {
                "final_state": "completed",
                "total_records": 5,
                "effective_records": 5,
                "ineffective_records": 0,
                "outbox_rows": 0,
                "state_version": 5,
            },
            "error_codes": [],
            "error_message": None,
            "details": {
                "official_realm_bench": False,
                "provenance": {
                    "source": "local_p1_compatible_fixture",
                    "note": "Local P1-compatible oracle trace. Not official.",
                    "created_for_stage": "1.6R-P1A-Verified",
                },
                "realm_bench": {
                    "benchmark_family": "REALM-Bench-compatible-local",
                    "problem_id": "P1",
                    "problem_name": "Campus Tour",
                    "stage": "P1A oracle trace replay",
                },
                "expected": {
                    "feasible": True,
                    "should_commit": True,
                    "route": ["S", "D", "A", "B", "L", "S"],
                    "finish_time": "12:10",
                    "total_travel_minutes": 70,
                    "total_visit_minutes": 120,
                    "total_minutes": 190,
                    "final_state": "completed",
                    "total_records": 5,
                    "effective_records": 5,
                    "ineffective_records": 0,
                    "outbox_rows": 0,
                    "state_version": 5,
                },
                "observed": {
                    "committed": True,
                    "prevalidation_ok": True,
                },
                "p1_trace": {
                    "feasible": True,
                    "violations": [],
                    "route": ["S", "D", "A", "B", "L", "S"],
                    "finish_time": "12:10",
                    "deadline": "17:00",
                    "total_travel_minutes": 70,
                    "total_visit_minutes": 120,
                    "total_minutes": 190,
                },
            },
        },
        {
            "case_id": "local-p1-compatible-campus-tour-time-window-violation-001",
            "ok": True,
            "committed_rids": [],
            "metrics": None,
            "error_codes": [
                "P1_TRACE_INFEASIBLE",
                "TIME_WINDOW_EARLY:L:arrive=09:10:not_before=10:00",
            ],
            "error_message": "expected negative case rejected before commit",
            "details": {
                "official_realm_bench": False,
                "provenance": {
                    "source": "local_p1_compatible_negative_fixture",
                    "note": "Local P1-compatible expected-negative trace. Not official.",
                    "created_for_stage": "1.6R-P1A-Verified",
                },
                "realm_bench": {
                    "benchmark_family": "REALM-Bench-compatible-local",
                    "problem_id": "P1",
                    "problem_name": "Campus Tour",
                    "stage": "P1A expected-negative oracle trace",
                },
                "expected": {
                    "feasible": False,
                    "should_commit": False,
                    "violation_prefixes": ["TIME_WINDOW_EARLY:L"],
                },
                "observed": {
                    "committed": False,
                    "prevalidation_ok": False,
                },
                "p1_trace": {
                    "feasible": False,
                    "violations": [
                        "TIME_WINDOW_EARLY:L:arrive=09:10:not_before=10:00"
                    ],
                    "route": ["S", "L"],
                    "finish_time": "09:40",
                    "deadline": "17:00",
                    "total_travel_minutes": 10,
                    "total_visit_minutes": 30,
                    "total_minutes": 40,
                },
            },
        },
    ]

    input_path = tmp_path / "p1.jsonl"
    _write_jsonl(input_path, rows)

    loaded = load_jsonl(input_path)
    summary = summarize_results(loaded)

    assert summary == {
        "total": 2,
        "passed": 2,
        "failed": 0,
        "committed": 1,
        "expected_negative_rejections": 1,
    }

    report = build_markdown_report(
        results=loaded,
        title="REALM Local Benchmark Report — P1 Campus Tour",
    )

    assert "# REALM Local Benchmark Report — P1 Campus Tour" in report
    assert "| Total cases | 2 |" in report
    assert "| Passed | 2 |" in report
    assert "| Failed | 0 |" in report
    assert "| Committed cases | 1 |" in report
    assert "| Expected-negative rejections | 1 |" in report

    assert "local-p1-compatible-campus-tour-static-001" in report
    assert "local-p1-compatible-campus-tour-time-window-violation-001" in report

    assert "Route: `S -> D -> A -> B -> L -> S`" in report
    assert "Finish time: `12:10`" in report
    assert "TIME_WINDOW_EARLY:L" in report
    assert "The expected-negative case was correctly rejected before commit." in report


@pytest.mark.realm
def test_report_cli_writes_markdown_file(tmp_path: Path):
    input_path = tmp_path / "results.jsonl"
    output_path = tmp_path / "report.md"

    _write_jsonl(
        input_path,
        [
            {
                "case_id": "case-1",
                "ok": True,
                "committed_rids": [],
                "metrics": None,
                "error_codes": [],
                "error_message": None,
                "details": {
                    "official_realm_bench": False,
                    "realm_bench": {
                        "benchmark_family": "REALM-Bench-compatible-local",
                        "problem_id": "P1",
                        "problem_name": "Campus Tour",
                    },
                    "expected": {
                        "should_commit": False,
                    },
                    "observed": {
                        "committed": False,
                    },
                },
            }
        ],
    )

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--title",
            "Test Report",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    report = output_path.read_text(encoding="utf-8")

    assert "# Test Report" in report
    assert "case-1" in report