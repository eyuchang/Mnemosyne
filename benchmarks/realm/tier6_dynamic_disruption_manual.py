#!/usr/bin/env python3
"""R96 dynamic disruption manual live-LLM prompt-pack generator.

This module creates a manual prompt pack for dynamic Tier-6 disruption repair.

It does not call external LLM APIs.
It does not require API keys.
It does not score the responses.

R96 target:
- one jobshop_breakdown dynamic sequence
- E7 full CRT stack
- ten mid-execution disruption episodes
- four proposer packs
- forty total manual live-LLM responses
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List


SCHEMA = "realm_tier6_dynamic_disruption_manual_pack_v0"
RESPONSE_SCHEMA = "realm_tier6_dynamic_disruption_response_v0"

DEFAULT_OUTPUT_DIR = (
    "results/realm_tier6_dynamic_disruption_manual/"
    "jobshop_e7_dynamic_pilot"
)

CONFIG_ID = "E7"
CONDITION_LABEL = "full_crt_stack"
SEQUENCE_ID = "T6-DYN-jobshop-e7-0001"
BASE_INSTANCE_ID = "jobshop_breakdown:datasets/J4/custom/j4_custom_001.json"
FAMILY = "jobshop_breakdown"

PROPOSER_PACKS = [
    "claude",
    "gpt",
    "deepseek_expert",
    "deepseek_instant",
]

FIXTURE_TIMESTAMP_UTC = "2026-07-02T00:00:00Z"

REQUIRED_RESPONSE_FIELDS = {
    "schema",
    "action",
    "repair_summary",
    "affected_steps",
    "preserve_evidence",
    "rollback_scope",
    "expected_time_to_correction",
    "risk_flags",
    "should_reject",
    "confidence",
}

VALID_ACTIONS = {"repair", "reject", "observe"}
VALID_ROLLBACK_SCOPES = {"none", "local", "unsafe"}


def deterministic_id(kind: str, *parts: object) -> str:
    seed = ":".join([kind, *[str(part) for part in parts]])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def dynamic_episode(episode_id: int) -> Dict[str, Any]:
    """Return one deterministic dynamic disruption episode."""

    disruptions = [
        {
            "machine": "M2",
            "failure_signature": "machine_unavailable.M2_after_commit",
            "disruption": (
                "Machine M2 becomes unavailable after operation J1-O1 "
                "has already committed."
            ),
            "must_preserve": [
                "J1-O1 completion record",
                "machine-log:M2:pre-failure",
                "operator-confirmed timestamp",
            ],
            "open_decision": (
                "Repair remaining uncommitted operations without invalidating J1-O1."
            ),
        },
        {
            "machine": "M1",
            "failure_signature": "setup_window_invalidated.M1",
            "disruption": (
                "The setup window on M1 is invalidated by a late calibration hold."
            ),
            "must_preserve": [
                "calibration-hold notice",
                "J2-O1 committed completion",
                "pre-hold dispatch record",
            ],
            "open_decision": (
                "Move or delay affected uncommitted operations without erasing "
                "the calibration evidence."
            ),
        },
        {
            "machine": "M3",
            "failure_signature": "dependent_operation_orphan_risk.M3",
            "disruption": (
                "A dependent downstream operation on M3 is blocked because its "
                "predecessor evidence is incomplete."
            ),
            "must_preserve": [
                "partial predecessor evidence",
                "downstream dependency record",
                "blockage timestamp",
            ],
            "open_decision": (
                "Repair the dependency chain without orphaning dependent operations."
            ),
        },
        {
            "machine": "M0",
            "failure_signature": "stale_duration_estimate.M0",
            "disruption": (
                "The duration estimate for an uncommitted M0 operation is revealed "
                "to be stale."
            ),
            "must_preserve": [
                "original duration estimate",
                "new duration observation",
                "dispatch queue snapshot",
            ],
            "open_decision": (
                "Update the remaining schedule using the new duration without "
                "rewriting committed history."
            ),
        },
        {
            "machine": "M2",
            "failure_signature": "evidence_destroying_reschedule_risk.M2",
            "disruption": (
                "A naive repair would delete the evidence explaining why M2 became "
                "unavailable."
            ),
            "must_preserve": [
                "failure notice",
                "maintenance ticket",
                "affected-operation audit trail",
            ],
            "open_decision": (
                "Propose an evidence-preserving repair or reject unsafe repair."
            ),
        },
        {
            "machine": "M1",
            "failure_signature": "precedence_violation_risk.M1",
            "disruption": (
                "A rushed repair would schedule J3-O2 before J3-O1 is completed."
            ),
            "must_preserve": [
                "J3-O1 status",
                "precedence constraint record",
                "repair-attempt warning",
            ],
            "open_decision": "Repair without violating job precedence.",
        },
        {
            "machine": "M3",
            "failure_signature": "resource_conflict_after_commit.M3",
            "disruption": (
                "Two uncommitted operations now compete for M3 after a committed "
                "operation consumed more time than expected."
            ),
            "must_preserve": [
                "committed long-running operation",
                "resource conflict notice",
                "queue state at conflict time",
            ],
            "open_decision": (
                "Resolve the conflict locally without rolling back committed work."
            ),
        },
        {
            "machine": "M0",
            "failure_signature": "late_material_arrival.M0",
            "disruption": (
                "Required material for an uncommitted M0 operation arrives late."
            ),
            "must_preserve": [
                "late material notice",
                "inventory timestamp",
                "committed upstream operation",
            ],
            "open_decision": (
                "Delay or reroute only uncommitted work while preserving material evidence."
            ),
        },
        {
            "machine": "M2",
            "failure_signature": "unsafe_global_rollback_request.M2",
            "disruption": (
                "A supervisor suggests globally rolling back the schedule to simplify recovery."
            ),
            "must_preserve": [
                "supervisor rollback request",
                "committed operations ledger",
                "current machine state",
            ],
            "open_decision": (
                "Reject or repair the request if it would invalidate committed evidence."
            ),
        },
        {
            "machine": "M1",
            "failure_signature": "repair_radius_exceeded.M1",
            "disruption": (
                "The proposed repair appears to touch more operations than the "
                "allowed local repair radius."
            ),
            "must_preserve": [
                "repair radius policy",
                "affected operation list",
                "current partial schedule",
            ],
            "open_decision": (
                "Keep the repair local or reject if the repair radius must be exceeded."
            ),
        },
    ]

    if episode_id < 1 or episode_id > len(disruptions):
        raise ValueError(f"episode_id must be in 1..{len(disruptions)}")

    item = disruptions[episode_id - 1]

    committed_operations = [
        {
            "operation_id": f"J{(episode_id % 4) + 1}-O1",
            "machine": f"M{episode_id % 4}",
            "status": "committed",
            "evidence_id": f"ev-e{episode_id:02d}-committed-1",
        },
        {
            "operation_id": f"J{((episode_id + 1) % 4) + 1}-O1",
            "machine": f"M{(episode_id + 1) % 4}",
            "status": "committed",
            "evidence_id": f"ev-e{episode_id:02d}-committed-2",
        },
    ]

    uncommitted_operations = [
        {
            "operation_id": f"J{((episode_id + 2) % 4) + 1}-O2",
            "machine": item["machine"],
            "status": "uncommitted",
            "repair_allowed": True,
        },
        {
            "operation_id": f"J{((episode_id + 3) % 4) + 1}-O2",
            "machine": f"M{(episode_id + 2) % 4}",
            "status": "uncommitted",
            "repair_allowed": True,
        },
    ]

    return {
        "sequence_id": SEQUENCE_ID,
        "episode_id": episode_id,
        "family": FAMILY,
        "base_instance_id": BASE_INSTANCE_ID,
        "config_id": CONFIG_ID,
        "condition_label": CONDITION_LABEL,
        "is_control_sequence": False,
        "dynamic_phase": "mid_execution",
        "timestamp_utc": FIXTURE_TIMESTAMP_UTC,
        "committed_operations": committed_operations,
        "uncommitted_operations": uncommitted_operations,
        "disruption": item["disruption"],
        "failure_signature": item["failure_signature"],
        "must_preserve": item["must_preserve"],
        "open_decision": item["open_decision"],
        "repair_radius_limit": 1,
        "forbidden_actions": [
            "global rollback",
            "delete committed evidence",
            "rewrite committed operation history",
            "orphan dependent operations",
            "commit a repair that violates precedence or machine availability",
        ],
        "success_criteria": [
            "preserve all listed evidence",
            "touch only uncommitted or locally repairable operations",
            "avoid global rollback",
            "return a machine-checkable JSON object",
            "reject if no safe repair is available",
        ],
    }


def response_template() -> Dict[str, Any]:
    return {
        "schema": RESPONSE_SCHEMA,
        "action": "",
        "repair_summary": "",
        "affected_steps": [],
        "preserve_evidence": True,
        "rollback_scope": "none",
        "expected_time_to_correction": 1,
        "risk_flags": [],
        "should_reject": False,
        "confidence": 0.0,
    }


def prompt_text(*, pack_name: str, episode: Dict[str, Any]) -> str:
    episode_json = json.dumps(episode, indent=2, ensure_ascii=False)
    schema_json = json.dumps(response_template(), indent=2, ensure_ascii=False)

    return f"""REALM-Bench Tier 6 Dynamic Disruption Manual LLM Prompt

You are the proposer only. Mnemosyne owns admission, rejection, commit, and repair validation.

ROLE

You receive a workflow already in execution. Some operations have already committed and must not be rewritten. A disruption has arrived mid-execution.

Your task is to propose a bounded repair, reject unsafe repair, or observe if more information is needed.

PUBLIC DYNAMIC EPISODE JSON

{episode_json}

CRITICAL RULES

Use only the visible episode.

Do not invent hidden schedule facts.

Do not delete or rewrite committed evidence.

Do not globally roll back the workflow.

Do not orphan dependent operations.

Do not exceed the repair radius unless you reject.

If a safe local repair is not possible, set action to reject and should_reject to true.

REQUIRED JSON RESPONSE

Return exactly one JSON object and no prose.

RESPONSE TEMPLATE

{schema_json}

FIELD REQUIREMENTS

- action: one of repair, reject, observe
- repair_summary: short repair description, or rejection/observation reason
- affected_steps: list of operation IDs or evidence IDs affected by your proposal
- preserve_evidence: true unless you are explicitly describing an unsafe proposal that should be rejected
- rollback_scope: one of none, local, unsafe
- expected_time_to_correction: nonnegative integer number of dynamic ticks
- risk_flags: list of concise risk labels
- should_reject: true if the proposal should be rejected before commit
- confidence: number from 0.0 to 1.0

PROPOSER PACK

{pack_name}
"""


def build_prompt_record(pack_name: str, episode: Dict[str, Any]) -> Dict[str, Any]:
    prompt_id = deterministic_id(
        "realm-tier6-dynamic-disruption-prompt",
        SEQUENCE_ID,
        CONFIG_ID,
        pack_name,
        episode["episode_id"],
    )

    return {
        "schema": "realm_tier6_dynamic_disruption_prompt_record_v0",
        "prompt_id": prompt_id,
        "sequence_id": SEQUENCE_ID,
        "config_id": CONFIG_ID,
        "condition_label": CONDITION_LABEL,
        "family": FAMILY,
        "base_instance_id": BASE_INSTANCE_ID,
        "pack_name": pack_name,
        "episode_id": episode["episode_id"],
        "failure_signature": episode["failure_signature"],
        "dynamic_phase": episode["dynamic_phase"],
        "prompt_filename": f"{pack_name}/e{episode['episode_id']:02d}_prompt.md",
        "response_filename": f"{pack_name}/e{episode['episode_id']:02d}_response.json",
        "episode": episode,
    }


def build_pack() -> Dict[str, Any]:
    episodes = [dynamic_episode(i) for i in range(1, 11)]

    records = [
        build_prompt_record(pack_name, episode)
        for pack_name in PROPOSER_PACKS
        for episode in episodes
    ]

    return {
        "schema": SCHEMA,
        "claim_boundary": (
            "Manual dynamic disruption prompt pack only. No API calls, no API keys, "
            "no scoring, and no performance claim."
        ),
        "sequence_id": SEQUENCE_ID,
        "config_id": CONFIG_ID,
        "condition_label": CONDITION_LABEL,
        "family": FAMILY,
        "base_instance_id": BASE_INSTANCE_ID,
        "num_episodes": len(episodes),
        "num_packs": len(PROPOSER_PACKS),
        "num_prompts": len(records),
        "proposer_packs": PROPOSER_PACKS,
        "response_schema": RESPONSE_SCHEMA,
        "records": records,
    }


def write_pack(output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = build_pack()

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    instructions = f"""# R96 Dynamic Disruption Manual Collection Instructions

This pack contains {pack['num_prompts']} prompts.

For each proposer pack:

1. Open eXX_prompt.md.
2. Paste the prompt into the target LLM.
3. Copy the model's JSON-only answer.
4. Paste it into eXX_response.json.
5. Do not edit the model answer except to remove non-JSON wrapper text if necessary.

No API keys are required.

No vendor API is called by this script.

Validation command:

python benchmarks/realm/tier6_dynamic_disruption_manual.py validate-responses --pack-dir {output_dir}

Expected before collection:

- parsed responses: 40
- placeholders: 40
- all valid: false

Expected after collection:

- parsed responses: 40
- missing responses: 0
- placeholders: 0
- validation errors: 0
- all valid: true
"""

    (output_dir / "INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")

    for record in pack["records"]:
        pack_dir = output_dir / record["pack_name"]
        pack_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = output_dir / record["prompt_filename"]
        response_path = output_dir / record["response_filename"]

        prompt_path.write_text(
            prompt_text(pack_name=record["pack_name"], episode=record["episode"]),
            encoding="utf-8",
        )

        response_path.write_text(
            json.dumps(response_template(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return pack


def validate_response(value: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    missing = sorted(REQUIRED_RESPONSE_FIELDS - set(value))
    if missing:
        errors.append(f"missing required fields: {missing}")
        return errors

    if value.get("schema") != RESPONSE_SCHEMA:
        errors.append("invalid schema")

    if value.get("action") not in VALID_ACTIONS:
        errors.append("invalid action")

    if not isinstance(value.get("repair_summary"), str) or not value.get("repair_summary"):
        errors.append("repair_summary must be nonempty string")

    if not isinstance(value.get("affected_steps"), list):
        errors.append("affected_steps must be list")

    if not isinstance(value.get("preserve_evidence"), bool):
        errors.append("preserve_evidence must be bool")

    if value.get("rollback_scope") not in VALID_ROLLBACK_SCOPES:
        errors.append("invalid rollback_scope")

    ttc = value.get("expected_time_to_correction")
    if not isinstance(ttc, int) or ttc < 0:
        errors.append("expected_time_to_correction must be nonnegative int")

    if not isinstance(value.get("risk_flags"), list):
        errors.append("risk_flags must be list")

    if not isinstance(value.get("should_reject"), bool):
        errors.append("should_reject must be bool")

    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0.0 or confidence > 1.0:
        errors.append("confidence must be number in [0, 1]")

    if value.get("rollback_scope") == "unsafe" and value.get("should_reject") is not True:
        errors.append("unsafe rollback_scope requires should_reject=true")

    if value.get("preserve_evidence") is False and value.get("should_reject") is not True:
        errors.append("non-preserving evidence proposal requires should_reject=true")

    return errors


def validate_responses(pack_dir: Path) -> Dict[str, Any]:
    manifest_path = pack_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []

    for record in manifest["records"]:
        response_path = pack_dir / record["response_filename"]

        if not response_path.exists():
            results.append(
                {
                    "pack_name": record["pack_name"],
                    "episode_id": record["episode_id"],
                    "path": str(response_path),
                    "parsed": False,
                    "missing": True,
                    "placeholder": False,
                    "errors": ["missing response file"],
                }
            )
            continue

        text = response_path.read_text(encoding="utf-8").strip()

        try:
            value = json.loads(text)
            parsed = True
            errors = validate_response(value)
        except Exception as exc:
            value = None
            parsed = False
            errors = [f"invalid JSON: {exc}"]

        is_placeholder = value == response_template()

        if is_placeholder:
            errors.append("placeholder response not replaced")

        results.append(
            {
                "pack_name": record["pack_name"],
                "episode_id": record["episode_id"],
                "path": str(response_path),
                "parsed": parsed,
                "missing": False,
                "placeholder": is_placeholder,
                "errors": errors,
            }
        )

    num_missing = sum(1 for item in results if item.get("missing"))
    num_parsed = sum(1 for item in results if item.get("parsed"))
    num_placeholders = sum(1 for item in results if item.get("placeholder"))
    num_errors = sum(len(item["errors"]) for item in results)

    report = {
        "schema": "realm_tier6_dynamic_disruption_response_validation_v0",
        "pack_dir": str(pack_dir),
        "num_expected": len(manifest["records"]),
        "num_parsed": num_parsed,
        "num_missing": num_missing,
        "num_placeholders": num_placeholders,
        "num_errors": num_errors,
        "all_valid": num_missing == 0 and num_placeholders == 0 and num_errors == 0,
        "results": results,
    }

    report_path = pack_dir / "validation_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return report


def cmd_export(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    pack = write_pack(output_dir)

    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "manifest": str(output_dir / "manifest.json"),
                "instructions": str(output_dir / "INSTRUCTIONS.md"),
                "num_prompts": pack["num_prompts"],
                "num_episodes": pack["num_episodes"],
                "num_packs": pack["num_packs"],
                "claim_boundary": pack["claim_boundary"],
            },
            indent=2,
        )
    )


def cmd_validate(args: argparse.Namespace) -> None:
    pack_dir = Path(args.pack_dir)
    report = validate_responses(pack_dir)

    print(
        json.dumps(
            {
                "pack_dir": report["pack_dir"],
                "num_expected": report["num_expected"],
                "num_parsed": report["num_parsed"],
                "num_missing": report["num_missing"],
                "num_placeholders": report["num_placeholders"],
                "num_errors": report["num_errors"],
                "all_valid": report["all_valid"],
                "validation_report": str(pack_dir / "validation_report.json"),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="R96 dynamic disruption manual prompt pack")
    sub = parser.add_subparsers(dest="command", required=True)

    export_cmd = sub.add_parser("export", help="export dynamic disruption prompt pack")
    export_cmd.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    export_cmd.set_defaults(func=cmd_export)

    validate_cmd = sub.add_parser("validate-responses", help="validate collected responses")
    validate_cmd.add_argument("--pack-dir", required=True)
    validate_cmd.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
