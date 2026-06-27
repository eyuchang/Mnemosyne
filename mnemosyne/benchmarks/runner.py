# File: mnemosyne/benchmarks/runner.py
#
# Purpose:
#   Local deterministic benchmark runner for REALM-style cases.
#
# Stage:
#   Stage 1.6R-P1A-Verified wires P1 trace validation into runner verdicts.
#
# Current path:
#   BenchmarkCase -> optional oracle validation -> CommitBatch -> Validator
#   -> Store -> StateView -> metrics
#
# Rule:
#   REALM-style fixtures provide scenarios. Mnemosyne owns transactional truth.

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from mnemosyne.benchmarks.models import BenchmarkCase, BenchmarkMetrics, BenchmarkStep
from mnemosyne.benchmarks.p1_campus_tour import validate_p1_campus_tour_case
from mnemosyne.benchmarks.realm import collect_realm_case_metrics, realm_case_to_commit_batches
from mnemosyne.benchmarks.results import BenchmarkRunResult


_RESERVED_CASE_KEYS = {
    "case_id",
    "tenant_id",
    "workflow_id",
    "entity_id",
    "binding_id",
    "fsm",
    "app_id",
    "schema_id",
    "steps",
}


def benchmark_case_from_dict(data: dict[str, Any]) -> BenchmarkCase:
    steps = [
        BenchmarkStep(
            step_id=step["step_id"],
            state_before=step["state_before"],
            state_after=step["state_after"],
            action_type=step["action_type"],
            attrs_after=dict(step.get("attrs_after", {})),
            depends_on=list(step.get("depends_on", [])),
            compensates=list(step.get("compensates", [])),
            emit_outbox=bool(step.get("emit_outbox", False)),
            outbox_provider=step.get("outbox_provider", "benchmark"),
            outbox_effect_type=step.get("outbox_effect_type", "benchmark_effect"),
        )
        for step in data["steps"]
    ]

    metadata = {
        key: value
        for key, value in data.items()
        if key not in _RESERVED_CASE_KEYS
    }

    return BenchmarkCase(
        case_id=data["case_id"],
        tenant_id=data["tenant_id"],
        workflow_id=data["workflow_id"],
        entity_id=data["entity_id"],
        binding_id=data["binding_id"],
        fsm=data["fsm"],
        app_id=data["app_id"],
        schema_id=data["schema_id"],
        steps=steps,
        metadata=metadata,
    )


def load_benchmark_case(path: str | Path) -> BenchmarkCase:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    return benchmark_case_from_dict(data)


def load_benchmark_cases(case_dir: str | Path) -> list[BenchmarkCase]:
    root = Path(case_dir)

    return [
        load_benchmark_case(path)
        for path in sorted(root.glob("*.json"))
    ]


def _expected_violation_prefixes_match(
    *,
    expected_prefixes: list[str],
    actual_violations: list[str],
) -> bool:
    for prefix in expected_prefixes:
        if not any(violation.startswith(prefix) for violation in actual_violations):
            return False

    return True


def _p1_trace_details(case: BenchmarkCase) -> tuple[bool, list[str], dict[str, Any]]:
    realm_bench = case.metadata.get("realm_bench")

    if not isinstance(realm_bench, dict):
        return True, [], {}

    if realm_bench.get("problem_id") != "P1":
        return True, [], {}

    trace_metrics = validate_p1_campus_tour_case(case)
    trace_dict = asdict(trace_metrics)

    expected = dict(case.metadata.get("expected", {}))
    expected_feasible = expected.get("feasible")
    expected_violation_prefixes = list(expected.get("violation_prefixes", []))

    details = {
        "realm_bench": {
            "benchmark_family": realm_bench.get("benchmark_family"),
            "problem_id": realm_bench.get("problem_id"),
            "problem_name": realm_bench.get("problem_name"),
            "stage": realm_bench.get("stage"),
        },
        "official_realm_bench": bool(case.metadata.get("official_realm_bench", False)),
        "provenance": case.metadata.get("provenance"),
        "expected": expected,
        "p1_trace": trace_dict,
    }

    error_codes: list[str] = []

    if expected_feasible is not None and trace_metrics.feasible != bool(expected_feasible):
        error_codes.append("EXPECTED_FEASIBILITY_MISMATCH")

    if expected_violation_prefixes and not _expected_violation_prefixes_match(
        expected_prefixes=expected_violation_prefixes,
        actual_violations=trace_metrics.violations,
    ):
        error_codes.append("EXPECTED_VIOLATION_MISMATCH")

    if not trace_metrics.feasible:
        error_codes.append("P1_TRACE_INFEASIBLE")
        error_codes.extend(trace_metrics.violations)

    return not error_codes, error_codes, details


def _expected_metric_errors(
    *,
    expected: dict[str, Any],
    metrics: BenchmarkMetrics,
) -> list[str]:
    checks = {
        "final_state": metrics.final_state,
        "state_version": metrics.state_version,
        "total_records": metrics.total_records,
        "effective_records": metrics.effective_records,
        "ineffective_records": metrics.ineffective_records,
        "outbox_rows": metrics.outbox_rows,
    }

    errors: list[str] = []

    for key, actual_value in checks.items():
        if key in expected and expected[key] != actual_value:
            errors.append(
                f"EXPECTED_METRIC_MISMATCH:{key}:"
                f"expected={expected[key]}:actual={actual_value}"
            )

    return errors


async def run_realm_case(
    *,
    case: BenchmarkCase,
    store,
    validator,
) -> BenchmarkRunResult:
    committed_rids: list[str] = []
    expected = dict(case.metadata.get("expected", {}))
    should_commit = expected.get("should_commit")
    pre_ok, pre_error_codes, details = _p1_trace_details(case)

    if not pre_ok:
        expected_negative = should_commit is False

        details["observed"] = {
            "committed": False,
            "prevalidation_ok": False,
        }

        if expected_negative:
            return BenchmarkRunResult(
                case_id=case.case_id,
                ok=True,
                committed_rids=[],
                error_codes=pre_error_codes,
                error_message="expected negative case rejected before commit",
                details=details,
            )

        return BenchmarkRunResult(
            case_id=case.case_id,
            ok=False,
            committed_rids=[],
            error_codes=pre_error_codes,
            error_message="prevalidation failed before commit",
            details=details,
        )

    if should_commit is False:
        details["observed"] = {
            "committed": False,
            "prevalidation_ok": True,
        }

        return BenchmarkRunResult(
            case_id=case.case_id,
            ok=False,
            committed_rids=[],
            error_codes=["EXPECTED_NEGATIVE_BUT_PREVALIDATION_PASSED"],
            error_message="expected negative case passed prevalidation",
            details=details,
        )

    try:
        for batch in realm_case_to_commit_batches(case):
            validation_result = await validator.validate_batch(batch, store)

            if not validation_result.ok:
                return BenchmarkRunResult(
                    case_id=case.case_id,
                    ok=False,
                    committed_rids=committed_rids,
                    error_codes=[error.code for error in validation_result.errors],
                    error_message="validation failed",
                    details=details,
                )

            records = await validator.records_from_batch(batch, store)
            committed_records = await store.commit_batch(batch, records)
            committed_rids.extend(record.rid for record in committed_records)

        metrics = await collect_realm_case_metrics(store, case)
        metric_errors = _expected_metric_errors(
            expected=expected,
            metrics=metrics,
        )

        details["observed"] = {
            "committed": True,
            "prevalidation_ok": True,
            "committed_rids": list(committed_rids),
        }

        if metric_errors:
            return BenchmarkRunResult(
                case_id=case.case_id,
                ok=False,
                committed_rids=committed_rids,
                metrics=metrics,
                error_codes=metric_errors,
                error_message="expected metrics did not match observed metrics",
                details=details,
            )

        return BenchmarkRunResult(
            case_id=case.case_id,
            ok=True,
            committed_rids=committed_rids,
            metrics=metrics,
            details=details,
        )

    except Exception as exc:
        return BenchmarkRunResult(
            case_id=case.case_id,
            ok=False,
            committed_rids=committed_rids,
            error_message=str(exc),
            details=details,
        )


async def run_realm_cases(
    *,
    cases: list[BenchmarkCase],
    store_factory,
    validator_factory,
) -> list[BenchmarkRunResult]:
    results: list[BenchmarkRunResult] = []

    for case in cases:
        store = store_factory()
        validator = validator_factory()
        results.append(
            await run_realm_case(
                case=case,
                store=store,
                validator=validator,
            )
        )

    return results
