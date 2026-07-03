from __future__ import annotations

import json

from benchmarks.realm import tier6_dynamic_disruption_manual as manual
from benchmarks.realm import tier6_dynamic_disruption_replay as replay


def fill_pack(pack_dir, response):
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["records"]:
        (pack_dir / record["response_filename"]).write_text(
            json.dumps(response, indent=2) + "\n",
            encoding="utf-8",
        )


def valid_repair_response():
    return {
        "schema": manual.RESPONSE_SCHEMA,
        "action": "repair",
        "repair_summary": "Preserve committed evidence and locally repair one uncommitted operation.",
        "affected_steps": ["J4-O2"],
        "preserve_evidence": True,
        "rollback_scope": "local",
        "expected_time_to_correction": 1,
        "risk_flags": [],
        "should_reject": False,
        "confidence": 0.75,
    }


def test_classify_admission_admits_safe_repair() -> None:
    record = manual.build_pack()["records"][0]
    response = valid_repair_response()

    decision, reasons = replay.classify_admission(record=record, response=response)

    assert decision == "admit"
    assert reasons == ["passed_admission_guards"]


def test_classify_admission_rejects_unsafe_rollback() -> None:
    record = manual.build_pack()["records"][0]
    response = valid_repair_response()
    response["rollback_scope"] = "unsafe"
    response["should_reject"] = False

    decision, reasons = replay.classify_admission(record=record, response=response)

    assert decision == "reject"
    assert "unsafe_rollback_scope" in reasons


def test_event_from_response_has_safety_counters() -> None:
    record = manual.build_pack()["records"][0]
    response = valid_repair_response()

    event = replay.event_from_response(record, response)

    assert event["schema"] == replay.EVENT_SCHEMA
    assert event["admission_decision"] == "admit"
    assert event["safety"]["invalid_commit_count"] == 0
    assert event["time_to_correction"] == 1


def test_build_replay_from_valid_pack(tmp_path) -> None:
    pack_dir = tmp_path / "pack"
    output_dir = tmp_path / "out"

    manual.write_pack(pack_dir)
    fill_pack(pack_dir, valid_repair_response())

    report = replay.build_replay(pack_dir, output_dir)

    assert report["schema"] == replay.SCHEMA
    assert report["summary"]["num_events"] == 40
    assert report["summary"]["safety_passed"] is True
    assert report["summary"]["official_realm_score"] is False
    assert (output_dir / "dynamic_replay_events.jsonl").exists()
    assert (output_dir / "dynamic_admission_report.json").exists()
    assert (output_dir / "dynamic_admission_report.md").exists()


def test_build_replay_rejects_unvalidated_placeholders(tmp_path) -> None:
    pack_dir = tmp_path / "pack"
    output_dir = tmp_path / "out"

    manual.write_pack(pack_dir)

    try:
        replay.build_replay(pack_dir, output_dir)
    except ValueError as exc:
        assert "response pack is not fully valid" in str(exc)
    else:
        raise AssertionError("expected replay to reject placeholder pack")
