from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "realm"
    / "tier6_live_llm_kernel_trace.py"
)

spec = importlib.util.spec_from_file_location("tier6_live_llm_kernel_trace", MODULE_PATH)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def sample_comparison_report() -> dict:
    return {
        "schema": "realm_tier6_live_llm_kernel_import_report_v0",
        "sequence_id": "T6-7e17ef0cc5f3",
        "config_id": "E7",
        "condition_label": "full_crt_stack",
        "packs": [
            {
                "pack_name": "test_pack",
                "responses": [
                    {
                        "key": "E7__T6-7e17ef0cc5f3__e01",
                        "episode_id": 1,
                        "response_path": "responses/e01.txt",
                        "response_sha256": "abc",
                        "should_reject": False,
                        "confidence": 0.7,
                        "policy_style": "observation_first",
                        "active_score": 0,
                        "observation_score": 3,
                        "unsupported_specificity_count": 0,
                        "deterministic_admission_recommendation": "admit_parseable_proposal",
                        "proposal_summary": "Observe state before acting.",
                    },
                    {
                        "key": "E7__T6-7ef0cc5f3__e02",
                        "episode_id": 2,
                        "response_path": "responses/e02.txt",
                        "response_sha256": "def",
                        "should_reject": False,
                        "confidence": 0.8,
                        "policy_style": "mixed",
                        "active_score": 2,
                        "observation_score": 2,
                        "unsupported_specificity_count": 8,
                        "deterministic_admission_recommendation": "admit_with_grounding_flags",
                        "proposal_summary": "Repair with grounding flags.",
                    },
                    {
                        "key": "E7__T6-7e17ef0cc5f3__e03",
                        "episode_id": 3,
                        "response_path": "responses/e03.txt",
                        "response_sha256": "ghi",
                        "should_reject": True,
                        "confidence": 0.9,
                        "policy_style": "observation_first",
                        "active_score": 0,
                        "observation_score": 4,
                        "unsupported_specificity_count": 1,
                        "deterministic_admission_recommendation": "model_requests_rejection",
                        "proposal_summary": "Reject unsupported action.",
                    },
                ],
            }
        ],
    }


def test_deterministic_id_is_stable() -> None:
    a = module.deterministic_id("x", "a", 1)
    b = module.deterministic_id("x", "a", 1)
    c = module.deterministic_id("x", "a", 2)
    assert a == b
    assert a != c


def test_recommendation_maps_to_kernel_method() -> None:
    assert module.kernel_method_for_recommendation("admit_parseable_proposal") == "accept_via_kernel"
    assert module.kernel_method_for_recommendation("admit_with_grounding_flags") == "accept_via_kernel_with_flags"
    assert module.kernel_method_for_recommendation("model_requests_rejection") == "reject_before_commit"
    assert module.kernel_method_for_recommendation("review_high_unsupported_specificity") == "reject_before_commit"


def test_grounding_flags() -> None:
    response = {
        "should_reject": True,
        "unsupported_specificity_count": 12,
        "deterministic_admission_recommendation": "review_high_unsupported_specificity",
    }
    flags = module.grounding_flags(response)
    assert "high_unsupported_specificity" in flags
    assert "model_requested_rejection" in flags
    assert "requires_human_review" in flags


def test_build_trace_report_counts_records() -> None:
    report = module.build_trace_report(sample_comparison_report())
    assert report["num_records"] == 3
    assert report["num_admitted"] == 2
    assert report["num_rejected"] == 1
    assert report["kernel_method_counts"]["accept_via_kernel"] == 1
    assert report["kernel_method_counts"]["accept_via_kernel_with_flags"] == 1
    assert report["kernel_method_counts"]["reject_before_commit"] == 1
    assert len(report["records"]) == 3


def test_trace_record_has_deterministic_time_and_record_id() -> None:
    report_a = module.build_trace_report(sample_comparison_report())
    report_b = module.build_trace_report(sample_comparison_report())

    first_a = report_a["records"][0]
    first_b = report_b["records"][0]

    assert first_a["record_id"] == first_b["record_id"]
    assert first_a["event_time"] == "2000-01-01T00:00:01Z"
    assert first_a["kernel_admission_record"]["method"] == "accept_via_kernel"
