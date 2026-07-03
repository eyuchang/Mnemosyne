from __future__ import annotations

import json

from benchmarks.realm import tier6_dynamic_disruption_manual as module


def test_build_pack_has_forty_prompts() -> None:
    pack = module.build_pack()

    assert pack["schema"] == module.SCHEMA
    assert pack["num_episodes"] == 10
    assert pack["num_packs"] == 4
    assert pack["num_prompts"] == 40
    assert len(pack["records"]) == 40


def test_dynamic_episode_contains_mid_execution_disruption() -> None:
    episode = module.dynamic_episode(1)

    assert episode["dynamic_phase"] == "mid_execution"
    assert episode["committed_operations"]
    assert episode["uncommitted_operations"]
    assert episode["failure_signature"]
    assert episode["must_preserve"]
    assert "global rollback" in episode["forbidden_actions"]


def test_response_template_is_placeholder() -> None:
    value = module.response_template()
    errors = module.validate_response(value)

    assert "invalid action" in errors
    assert "repair_summary must be nonempty string" in errors


def test_valid_response_passes() -> None:
    value = {
        "schema": module.RESPONSE_SCHEMA,
        "action": "repair",
        "repair_summary": (
            "Delay the affected uncommitted operation and preserve committed evidence."
        ),
        "affected_steps": ["J1-O2", "ev-e01-committed-1"],
        "preserve_evidence": True,
        "rollback_scope": "local",
        "expected_time_to_correction": 1,
        "risk_flags": ["machine_unavailable"],
        "should_reject": False,
        "confidence": 0.72,
    }

    assert module.validate_response(value) == []


def test_export_and_validate_placeholders(tmp_path) -> None:
    pack_dir = tmp_path / "pack"
    module.write_pack(pack_dir)

    assert (pack_dir / "manifest.json").exists()
    assert (pack_dir / "INSTRUCTIONS.md").exists()
    assert (pack_dir / "claude" / "e01_prompt.md").exists()
    assert (pack_dir / "claude" / "e01_response.json").exists()

    report = module.validate_responses(pack_dir)

    assert report["num_expected"] == 40
    assert report["num_parsed"] == 40
    assert report["num_placeholders"] == 40
    assert report["all_valid"] is False


def test_validate_collected_response(tmp_path) -> None:
    pack_dir = tmp_path / "pack"
    module.write_pack(pack_dir)

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))

    for record in manifest["records"]:
        response = {
            "schema": module.RESPONSE_SCHEMA,
            "action": "repair",
            "repair_summary": (
                "Preserve committed evidence and locally reschedule the affected "
                "uncommitted operation."
            ),
            "affected_steps": ["J1-O2"],
            "preserve_evidence": True,
            "rollback_scope": "local",
            "expected_time_to_correction": 1,
            "risk_flags": [],
            "should_reject": False,
            "confidence": 0.7,
        }
        (pack_dir / record["response_filename"]).write_text(
            json.dumps(response, indent=2) + "\n",
            encoding="utf-8",
        )

    report = module.validate_responses(pack_dir)

    assert report["num_expected"] == 40
    assert report["num_parsed"] == 40
    assert report["num_placeholders"] == 0
    assert report["num_errors"] == 0
    assert report["all_valid"] is True
