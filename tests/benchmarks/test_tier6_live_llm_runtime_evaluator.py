from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "realm"
    / "tier6_live_llm_runtime_evaluator.py"
)

spec = importlib.util.spec_from_file_location("tier6_live_llm_runtime_evaluator", MODULE_PATH)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def sample_trace_report() -> dict:
    return {
        "schema": "realm_tier6_live_llm_kernel_trace_report_v0",
        "sequence_id": "T6-7e17ef0cc5f3",
        "config_id": "E7",
        "condition_label": "full_crt_stack",
        "records": [
            {
                "trace_id": "trace-a",
                "record_id": "record-a",
                "event_index": 0,
                "event_time": "2000-01-01T00:00:01Z",
                "sequence_id": "T6-7e17ef0cc5f3",
                "config_id": "E7",
                "condition_label": "full_crt_stack",
                "pack_name": "claude",
                "episode_id": 1,
                "kernel_admission_record": {
                    "method": "accept_via_kernel",
                    "admitted": True,
                    "grounding_flags": [],
                    "input_summary": {
                        "policy_style": "mixed",
                        "unsupported_specificity_count": 0,
                    },
                    "proposal_summary": "Observe and repair locally.",
                },
            },
            {
                "trace_id": "trace-b",
                "record_id": "record-b",
                "event_index": 1,
                "event_time": "2000-01-01T00:00:02Z",
                "sequence_id": "T6-7e17ef0cc5f3",
                "config_id": "E7",
                "condition_label": "full_crt_stack",
                "pack_name": "deepseek_expert",
                "episode_id": 2,
                "kernel_admission_record": {
                    "method": "accept_via_kernel_with_flags",
                    "admitted": True,
                    "grounding_flags": ["moderate_unsupported_specificity"],
                    "input_summary": {
                        "policy_style": "mixed",
                        "unsupported_specificity_count": 8,
                    },
                    "proposal_summary": "Repair with grounding flags.",
                },
            },
            {
                "trace_id": "trace-c",
                "record_id": "record-c",
                "event_index": 2,
                "event_time": "2000-01-01T00:00:03Z",
                "sequence_id": "T6-7e17ef0cc5f3",
                "config_id": "E7",
                "condition_label": "full_crt_stack",
                "pack_name": "gpt",
                "episode_id": 3,
                "kernel_admission_record": {
                    "method": "reject_before_commit",
                    "admitted": False,
                    "grounding_flags": ["model_requested_rejection"],
                    "input_summary": {
                        "policy_style": "observation_first",
                        "unsupported_specificity_count": 1,
                    },
                    "proposal_summary": "Reject unsupported mutation.",
                },
            },
        ],
    }


def test_deterministic_id_is_stable() -> None:
    a = module.deterministic_id("runtime", "a", 1)
    b = module.deterministic_id("runtime", "a", 1)
    c = module.deterministic_id("runtime", "a", 2)

    assert a == b
    assert a != c


def test_method_expected_admitted() -> None:
    assert module.method_expected_admitted("accept_via_kernel") is True
    assert module.method_expected_admitted("accept_via_kernel_with_flags") is True
    assert module.method_expected_admitted("reject_before_commit") is False
    assert module.method_expected_admitted("unknown") is False


def test_evaluate_record_passes_consistent_record() -> None:
    record = sample_trace_report()["records"][0]
    evaluated = module.evaluate_record(record)

    assert evaluated["passed"] is True
    assert evaluated["runtime_replay"]["admitted"] is True
    assert evaluated["runtime_replay"]["store_mutation"] is False
    assert evaluated["runtime_replay"]["events_jsonl_emitted"] is False


def test_global_invariants_pass() -> None:
    checks = module.validate_global_invariants(sample_trace_report()["records"])
    assert all(check["passed"] for check in checks)


def test_build_runtime_evaluator_report_counts() -> None:
    report = module.build_runtime_evaluator_report(sample_trace_report())

    assert report["num_records"] == 3
    assert report["num_passed"] == 3
    assert report["num_failed"] == 0
    assert report["num_admitted"] == 2
    assert report["num_rejected"] == 1
    assert report["num_flagged"] == 2
    assert report["global_passed"] is True


def test_inconsistent_method_admission_fails() -> None:
    trace = sample_trace_report()
    trace["records"][0]["kernel_admission_record"]["admitted"] = False

    report = module.build_runtime_evaluator_report(trace)

    assert report["num_failed"] == 1
    assert report["global_passed"] is False


def test_duplicate_record_ids_fail_global_check() -> None:
    trace = sample_trace_report()
    trace["records"][1]["record_id"] = "record-a"

    report = module.build_runtime_evaluator_report(trace)
    global_checks = {check["name"]: check for check in report["global_checks"]}

    assert global_checks["record_ids_unique"]["passed"] is False
    assert report["global_passed"] is False
