import importlib.util
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "benchmarks" / "realm" / "tier6_mnemosyne_adapter.py"

spec = importlib.util.spec_from_file_location("tier6_mnemosyne_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def synthetic_sequence(is_control=False):
    episodes = []
    for episode_id in range(1, 11):
        episodes.append({
            "sequence_id": "T6-synthetic",
            "episode_id": episode_id,
            "seed": 17,
            "base_instance_id": "synthetic:base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
            "is_control_sequence": is_control,
            "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
            "perturbation": {"operators": ["jitter", "rename", "resample"]},
        })

    return {
        "sequence_id": "T6-synthetic",
        "sequence_seed": 17,
        "episodes_per_sequence": 10,
        "base_instance": {
            "base_instance_id": "synthetic:base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
        },
        "is_control_sequence": is_control,
        "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
        "episodes": episodes,
    }


def test_e0_emits_recurrence_pattern():
    events = adapter.emit_events_for_sequence("E0", synthetic_sequence())
    assert any(event["delta"] == "failure_recurred" for event in events)
    assert all(event["invalid_commit_count"] == 0 for event in events)


def test_e2_blocks_recurrence_after_causal_repair():
    events = adapter.emit_events_for_sequence("E2", synthetic_sequence())
    assert any(event["delta"] == "corrected" for event in events)
    assert not any(event["delta"] == "failure_recurred" for event in events)


def test_e3_temporal_adapter_has_high_horizon_reward_but_can_recur():
    events = adapter.emit_events_for_sequence("E3", synthetic_sequence())
    assert any(event["delta"] == "failure_recurred" for event in events)
    assert all(event.get("horizon_reward", 0) == 0.75 for event in events)


def test_e7_full_stack_sets_grounded_admission_and_blocks_recurrence():
    events = adapter.emit_events_for_sequence("E7", synthetic_sequence())
    assert all(event.get("grounded_admission") is True for event in events)
    assert not any(event["delta"] == "failure_recurred" for event in events)


def test_control_sequence_emits_benign_observations():
    events = adapter.emit_events_for_sequence("E7", synthetic_sequence(is_control=True))
    assert len(events) == 10
    assert all(event["failure_signature"] == "" for event in events)
    assert all(event["is_control_sequence"] is True for event in events)


@pytest.mark.skipif(not os.environ.get("REALM_BENCH_ROOT"), reason="REALM_BENCH_ROOT not set")
def test_integration_emit_all_config_runs(tmp_path):
    realm_root = adapter.resolve_realm_root()
    results = adapter.emit_all_config_runs(realm_root=realm_root, output_base=tmp_path)

    assert set(results) == {"E0", "E2", "E3", "E7"}
    assert results["E0"]["safety_passed"] is True
    assert results["E2"]["safety_passed"] is True
    assert results["E7"]["safety_passed"] is True
    assert results["E2"]["repeated_failure_rate"] <= results["E0"]["repeated_failure_rate"]
    assert results["E7"]["horizon_reward_mean"] >= results["E0"]["horizon_reward_mean"]
