import importlib.util
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "benchmarks" / "realm" / "tier6_mnemosyne_kernel_adapter.py"

spec = importlib.util.spec_from_file_location("tier6_mnemosyne_kernel_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def synthetic_sequence(is_control=False):
    episodes = []
    for episode_id in range(1, 11):
        episodes.append({
            "sequence_id": "T6-kernel-synthetic",
            "episode_id": episode_id,
            "seed": 17,
            "base_instance_id": "synthetic:kernel-base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
            "is_control_sequence": is_control,
            "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
            "perturbation": {"operators": ["jitter", "rename", "resample"]},
        })

    return {
        "sequence_id": "T6-kernel-synthetic",
        "sequence_seed": 17,
        "episodes_per_sequence": 10,
        "base_instance": {
            "base_instance_id": "synthetic:kernel-base",
            "family": "synthetic_family",
            "source_path": "datasets/synthetic.json",
            "source_sha256": "0" * 64,
        },
        "is_control_sequence": is_control,
        "hazard_signatures": [] if is_control else ["stale_world.route_time_underestimated"],
        "episodes": episodes,
    }


def test_kernel_e0_has_kernel_surface_and_recurrence():
    events = adapter.emit_kernel_events_for_sequence("E0", synthetic_sequence())
    assert any(event["delta"] == "failure_recurred" for event in events)
    assert all("kernel_surface" in event for event in events)

    accepted = [event for event in events if event["kernel_surface"]["decision"]["runtime_decision"] == "accepted"]
    assert accepted
    assert all(event["kernel_surface"]["decision"]["kernel_commit_performed"] is True for event in accepted)


def test_kernel_reject_before_commit_does_not_call_kernel():
    events = adapter.emit_kernel_events_for_sequence("E7", synthetic_sequence())
    rejected = [event for event in events if event["event"] == "reject"]
    assert rejected
    reject = rejected[0]
    assert reject["kernel_surface"]["decision"]["runtime_decision"] == "rejected"
    assert reject["kernel_surface"]["decision"]["kernel_commit_performed"] is False
    assert reject["kernel_surface"]["kernel_calls"] == []


def test_kernel_e2_blocks_recurrence():
    events = adapter.emit_kernel_events_for_sequence("E2", synthetic_sequence())
    assert any(event["delta"] == "corrected" for event in events)
    assert not any(event["delta"] == "failure_recurred" for event in events)


def test_kernel_events_include_recovery_and_stateview_evidence():
    events = adapter.emit_kernel_events_for_sequence("E7", synthetic_sequence())
    for event in events:
        surface = event["kernel_surface"]
        assert surface["recovery_event"]["event_id"]
        assert surface["recovery_event"]["schema_id"] == "core.recovery_event"
        assert surface["stateview_snapshot"]["tenant_id"]
        assert "effective_records" in surface["stateview_snapshot"]


def test_kernel_control_sequence_is_benign():
    events = adapter.emit_kernel_events_for_sequence("E7", synthetic_sequence(is_control=True))
    assert len(events) == 10
    assert all(event["failure_signature"] == "" for event in events)
    assert all(event["is_control_sequence"] is True for event in events)


@pytest.mark.skipif(not os.environ.get("REALM_BENCH_ROOT"), reason="REALM_BENCH_ROOT not set")
def test_integration_emit_all_kernel_config_runs(tmp_path):
    realm_root = adapter.resolve_realm_root()
    results = adapter.emit_all_kernel_config_runs(realm_root=realm_root, output_base=tmp_path)

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
