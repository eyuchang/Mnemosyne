import importlib.util
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "benchmarks" / "realm" / "tier6_mnemosyne_runtime_adapter.py"

spec = importlib.util.spec_from_file_location("tier6_mnemosyne_runtime_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def synthetic_sequence(is_control=False):
    episodes = []
    for episode_id in range(1, 11):
        episodes.append({
            "sequence_id": "T6-runtime-synthetic",
            "episode_id": episode_id,
            "seed": 17,
            "base_instance_id": "synthetic:runtime-base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
            "is_control_sequence": is_control,
            "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
            "perturbation": {"operators": ["jitter", "rename", "resample"]},
        })

    return {
        "sequence_id": "T6-runtime-synthetic",
        "sequence_seed": 17,
        "episodes_per_sequence": 10,
        "base_instance": {
            "base_instance_id": "synthetic:runtime-base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
        },
        "is_control_sequence": is_control,
        "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
        "episodes": episodes,
    }


def test_runtime_e0_emits_runtime_decisions_and_recurrence():
    events = adapter.emit_runtime_events_for_sequence("E0", synthetic_sequence())
    assert any(event["delta"] == "failure_recurred" for event in events)
    assert all("runtime_surface" in event for event in events)
    assert all(event["runtime_surface"]["decision_id"] for event in events)


def test_runtime_e2_blocks_recurrence():
    events = adapter.emit_runtime_events_for_sequence("E2", synthetic_sequence())
    assert any(event["delta"] == "corrected" for event in events)
    assert not any(event["delta"] == "failure_recurred" for event in events)


def test_runtime_e7_rejection_records_runtime_reject_decision():
    events = adapter.emit_runtime_events_for_sequence("E7", synthetic_sequence())
    rejected = [event for event in events if event["event"] == "reject"]
    assert rejected
    assert rejected[0]["runtime_surface"]["accepted"] is False
    assert rejected[0]["runtime_surface"]["error_codes"] == ["CAUSAL_AUDIT_BLOCKS_KNOWN_SIGNATURE"]


def test_runtime_control_sequence_is_benign():
    events = adapter.emit_runtime_events_for_sequence("E7", synthetic_sequence(is_control=True))
    assert len(events) == 10
    assert all(event["failure_signature"] == "" for event in events)
    assert all(event["is_control_sequence"] is True for event in events)


@pytest.mark.skipif(not os.environ.get("REALM_BENCH_ROOT"), reason="REALM_BENCH_ROOT not set")
def test_integration_emit_all_runtime_config_runs(tmp_path):
    realm_root = adapter.resolve_realm_root()
    results = adapter.emit_all_runtime_config_runs(realm_root=realm_root, output_base=tmp_path)

    assert set(results) == {"E0", "E2", "E3", "E7"}
    assert results["E0"]["safety_passed"] is True
    assert results["E2"]["safety_passed"] is True
    assert results["E7"]["safety_passed"] is True
    assert results["E2"]["repeated_failure_rate"] <= results["E0"]["repeated_failure_rate"]
    assert results["E7"]["horizon_reward_mean"] >= results["E0"]["horizon_reward_mean"]

    for config_id in results:
        out = Path(results[config_id]["output_dir"])
        assert (out / "events.jsonl").exists()
        assert (out / "summary.json").exists()
        assert (out / "report.md").exists()
