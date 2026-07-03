from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "realm"
    / "tier6_live_llm_kernel_import.py"
)

spec = importlib.util.spec_from_file_location("tier6_live_llm_kernel_import", MODULE_PATH)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None

# Required for dataclasses when loading a module via importlib.util.
# Without this, dataclasses may fail resolving cls.__module__.
sys.modules[spec.name] = module

spec.loader.exec_module(module)


def test_policy_classifies_observation_first() -> None:
    data = {
        "action": "Observe current state and request machine status before repair.",
        "proposal_summary": "Observe before acting.",
        "predicted_outcome": "State snapshot.",
        "horizon_rationale": "Observation preserves evidence.",
        "evidence_to_preserve": [],
        "risk_factors": [],
        "confidence": 0.8,
        "should_reject": False,
    }

    policy = module.classify_policy(data)
    assert policy["style"] in {"observation_first", "mixed"}
    assert policy["observation_score"] >= 2


def test_policy_classifies_active_repair() -> None:
    data = {
        "action": "Repair M2 and reschedule affected operations with right-shift.",
        "proposal_summary": "Repair and reschedule.",
        "predicted_outcome": "Reduced delay.",
        "horizon_rationale": "Repair prevents cascade.",
        "evidence_to_preserve": [],
        "risk_factors": [],
        "confidence": 0.8,
        "should_reject": False,
    }

    policy = module.classify_policy(data)
    assert policy["style"] in {"active_repair", "mixed"}
    assert policy["active_score"] >= 2


def test_unsupported_specificity_detects_concrete_details() -> None:
    data = {
        "action": "Repair Machine M2 during Job J3 Operation 2 at t=12.",
        "proposal_summary": "Use SPT after temperature spike.",
        "predicted_outcome": "Makespan improves 15-25%.",
        "horizon_rationale": "M2 is bottleneck.",
        "evidence_to_preserve": ["temperature +5°C", "J3 at 40% completion"],
        "risk_factors": [],
        "confidence": 0.78,
        "should_reject": False,
    }

    unsupported = module.unsupported_specificity(data)
    assert unsupported["count"] >= 4


def test_deterministic_admission_recommendation_respects_model_reject() -> None:
    data = {"should_reject": True}
    assert module.deterministic_admission_recommendation(data, 0) == "model_requests_rejection"
