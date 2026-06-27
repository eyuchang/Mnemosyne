# File: tests/benchmarks/test_realm_cli_runner.py
#
# Purpose:
#   Verify Stage 1.5R-CLI REALM command-line runner readiness.
#
# Policy:
#   Marked realm, so this remains opt-in and does not burden the default suite.
#
# Run explicitly with:
#   python -m pytest -q -m realm

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.realm_runner import main, run_realm_cli_async


CASE_DIR = Path("benchmarks/realm/cases")


@pytest.mark.realm
@pytest.mark.asyncio
async def test_realm_cli_async_runs_all_cases_and_writes_jsonl(tmp_path):
    output_path = tmp_path / "realm_run.jsonl"

    results, summary = await run_realm_cli_async(
        case_dir=CASE_DIR,
        output_path=output_path,
    )

    assert summary.cases == 2
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.output_path == str(output_path)

    assert [result.case_id for result in results] == [
        "realm-smoke-confirm-001",
        "realm-smoke-correction-001",
    ]
    assert all(result.ok for result in results)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2

    rows = [json.loads(line) for line in lines]

    assert [row["case_id"] for row in rows] == [
        "realm-smoke-confirm-001",
        "realm-smoke-correction-001",
    ]
    assert all(row["ok"] for row in rows)
    assert rows[0]["metrics"]["final_state"] == "confirmed"
    assert rows[1]["metrics"]["final_state"] == "cancelled"


@pytest.mark.realm
def test_realm_cli_main_returns_zero_and_writes_jsonl(tmp_path):
    output_path = tmp_path / "realm_run.jsonl"

    exit_code = main(
        [
            "--cases",
            str(CASE_DIR),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(rows) == 2
    assert all(row["ok"] for row in rows)