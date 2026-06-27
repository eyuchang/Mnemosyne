from __future__ import annotations

import json
from pathlib import Path

from mnemosyne.benchmarks.models import BenchmarkStep


SKELETON_DIRS = [
    Path("benchmarks/realm/p2_skeleton"),
    Path("benchmarks/realm/p3_skeleton"),
    Path("benchmarks/realm/p5_skeleton"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_realm_family_skeleton_directories_exist():
    for directory in SKELETON_DIRS:
        assert directory.exists(), directory
        assert any(directory.glob("*.json")), directory


def test_realm_family_skeletons_have_required_case_metadata():
    for directory in SKELETON_DIRS:
        for path in directory.glob("*.json"):
            data = load_json(path)

            assert data["case_id"]
            assert data["family"] in {"P2", "P3", "P5"}
            assert isinstance(data["expected_negative"], bool)
            assert data["app_id"]
            assert data["schema_id"]

            realm = data["realm_bench"]
            assert realm["tenant_id"]
            assert realm["workflow_id"]
            assert realm["entity_id"]
            assert realm["binding_id"]
            assert realm["fsm"]


def test_realm_family_skeleton_steps_are_structurally_valid():
    for directory in SKELETON_DIRS:
        for path in directory.glob("*.json"):
            data = load_json(path)

            seen: set[str] = set()

            for step in data["steps"]:
                obj = BenchmarkStep(
                    step_id=step["step_id"],
                    state_before=step["state_before"],
                    state_after=step["state_after"],
                    action_type=step["action_type"],
                    attrs_after=step.get("attrs_after", {}),
                    depends_on=step.get("depends_on", []),
                    compensates=step.get("compensates", []),
                    emit_outbox=step.get("emit_outbox", False),
                    outbox_provider=step.get("outbox_provider", "benchmark"),
                    outbox_effect_type=step.get(
                        "outbox_effect_type",
                        "benchmark_effect",
                    ),
                )

                assert obj.step_id not in seen
                seen.add(obj.step_id)

                for dependency in obj.depends_on:
                    assert dependency in seen, (
                        f"{path}: step {obj.step_id} depends on unknown or later step "
                        f"{dependency}"
                    )


def test_each_skeleton_family_has_feasible_and_expected_negative_cases():
    by_family: dict[str, list[bool]] = {}

    for directory in SKELETON_DIRS:
        for path in directory.glob("*.json"):
            data = load_json(path)
            by_family.setdefault(data["family"], []).append(data["expected_negative"])

    for family in ["P2", "P3", "P5"]:
        assert family in by_family
        assert False in by_family[family], f"{family} has no feasible skeleton"
        assert True in by_family[family], f"{family} has no expected-negative skeleton"
