# File: tests/benchmarks/test_realm_runner_readiness.py
#
# Purpose:
#   Verify Stage 1.5R REALM benchmark-runner readiness.
#
# Policy:
#   Marked realm, so this remains opt-in and does not burden the default suite.
#
# Run explicitly with:
#   python -m pytest -q -m realm

from __future__ import annotations

from pathlib import Path

import pytest

from mnemosyne.apps import AppRegistry
from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.apps.rideshare import RideshareApp
from mnemosyne.apps.travel import TravelApp
from mnemosyne.benchmarks import (
    benchmark_result_to_dict,
    benchmark_result_to_jsonl,
    load_benchmark_case,
    load_benchmark_cases,
    run_realm_case,
    run_realm_cases,
)
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore


CASE_DIR = Path("benchmarks/realm/cases")


def make_store() -> SQLiteStore:
    return SQLiteStore()


def make_validator() -> Validator:
    registry = AppRegistry()
    registry.register(RideshareApp())
    registry.register(TravelApp())
    registry.register(JSSPApp())

    return Validator(
        registry.build_fsm_registry(),
        registry.build_constraint_registry(),
    )


@pytest.mark.realm
@pytest.mark.asyncio
async def test_load_and_run_single_realm_fixture():
    case = load_benchmark_case(CASE_DIR / "realm_smoke_correction_001.json")
    result = await run_realm_case(
        case=case,
        store=make_store(),
        validator=make_validator(),
    )

    assert result.ok
    assert result.case_id == "realm-smoke-correction-001"
    assert result.error_codes == []
    assert result.error_message is None
    assert result.metrics is not None
    assert result.metrics.total_records == 2
    assert result.metrics.effective_records == 1
    assert result.metrics.ineffective_records == 1
    assert result.metrics.outbox_rows == 2
    assert result.metrics.final_state == "cancelled"
    assert result.metrics.state_version == 2

    result_dict = benchmark_result_to_dict(result)
    result_jsonl = benchmark_result_to_jsonl(result)

    assert result_dict["case_id"] == "realm-smoke-correction-001"
    assert '"case_id": "realm-smoke-correction-001"' in result_jsonl


@pytest.mark.realm
@pytest.mark.asyncio
async def test_run_all_local_realm_fixtures():
    cases = load_benchmark_cases(CASE_DIR)

    assert [case.case_id for case in cases] == [
        "realm-smoke-confirm-001",
        "realm-smoke-correction-001",
    ]

    results = await run_realm_cases(
        cases=cases,
        store_factory=make_store,
        validator_factory=make_validator,
    )

    assert [result.case_id for result in results] == [
        "realm-smoke-confirm-001",
        "realm-smoke-correction-001",
    ]
    assert all(result.ok for result in results)

    by_case = {result.case_id: result for result in results}

    confirm = by_case["realm-smoke-confirm-001"]
    correction = by_case["realm-smoke-correction-001"]

    assert confirm.metrics is not None
    assert confirm.metrics.total_records == 3
    assert confirm.metrics.effective_records == 3
    assert confirm.metrics.ineffective_records == 0
    assert confirm.metrics.outbox_rows == 2
    assert confirm.metrics.final_state == "confirmed"
    assert confirm.metrics.state_version == 3

    assert correction.metrics is not None
    assert correction.metrics.total_records == 2
    assert correction.metrics.effective_records == 1
    assert correction.metrics.ineffective_records == 1
    assert correction.metrics.outbox_rows == 2
    assert correction.metrics.final_state == "cancelled"
    assert correction.metrics.state_version == 2