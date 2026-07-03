#!/usr/bin/env python3
"""R98 dynamic disruption admission/runtime replay.

This module consumes the R97 validated manual dynamic responses and emits a
deterministic admission/replay report.

It does not call external APIs.
It does not require API keys.
It does not claim official REALM-Bench scoring.

R98 claim boundary:
- consumes validated R97 responses
- applies deterministic admission guards
- emits dynamic repair/rejection/observe events
- reports safety counters and time-to-correction proxies
- prepares R99 REALM-Bench scorer handoff
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCHEMA = "realm_tier6_dynamic_disruption_replay_v0"
EVENT_SCHEMA = "realm_tier6_dynamic_disruption_event_v0"

DEFAULT_PACK_DIR = (
    "results/realm_tier6_dynamic_disruption_manual/"
    "jobshop_e7_dynamic_pilot"
)
DEFAULT_OUTPUT_DIR = "results/realm_tier6_dynamic_disruption_replay/jobshop_e7_dynamic_pilot"

THIS_PATH = Path(__file__).resolve()
MNEMOSYNE_ROOT = THIS_PATH.parents[2]
MANUAL_MODULE_PATH = MNEMOSYNE_ROOT / "benchmarks" / "realm" / "tier6_dynamic_disruption_manual.py"


def load_manual_module():
    spec = importlib.util.spec_from_file_location(
        "tier6_dynamic_disruption_manual_for_replay",
        MANUAL_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load manual module from {MANUAL_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


manual = load_manual_module()


def read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def operation_ids(items: List[Dict[str, Any]]) -> List[str]:
    return [str(item["operation_id"]) for item in items]


def lower_text(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return " ".join(lower_text(item) for item in value)
    return ""


def detect_global_rollback(response: Dict[str, Any]) -> bool:
    text = " ".join(
        [
            lower_text(response.get("repair_summary", "")),
            lower_text(response.get("risk_flags", [])),
        ]
    )
    phrases = [
        "global rollback",
        "roll back the whole",
        "rollback the whole",
        "rewrite committed",
        "delete committed",
        "erase committed",
    ]
    return any(phrase in text for phrase in phrases)


def classify_admission(
    *,
    record: Dict[str, Any],
    response: Dict[str, Any],
) -> Tuple[str, List[str]]:
    """Return admission decision and reasons.

    Decisions:
    - admit
    - reject
    - observe
    """

    episode = record["episode"]
    action = response.get("action")
    reasons: List[str] = []

    committed_ops = set(operation_ids(episode.get("committed_operations", [])))
    uncommitted_ops = set(operation_ids(episode.get("uncommitted_operations", [])))
    affected = set(str(item) for item in response.get("affected_steps", []))

    touched_committed_ops = sorted(affected & committed_ops)
    touched_uncommitted_ops = sorted(affected & uncommitted_ops)

    if action == "observe":
        return "observe", ["model_requested_observation"]

    if action == "reject" or response.get("should_reject") is True:
        return "reject", ["model_requested_rejection"]

    if response.get("rollback_scope") == "unsafe":
        reasons.append("unsafe_rollback_scope")

    if response.get("preserve_evidence") is not True:
        reasons.append("evidence_not_preserved")

    if detect_global_rollback(response):
        reasons.append("global_rollback_or_committed_rewrite_language")

    if touched_committed_ops:
        reasons.append("committed_operation_touched:" + ",".join(touched_committed_ops))

    repair_radius_limit = int(episode.get("repair_radius_limit", 1))
    if len(touched_uncommitted_ops) > repair_radius_limit:
        reasons.append(
            "repair_radius_exceeded:"
            + str(len(touched_uncommitted_ops))
            + ">"
            + str(repair_radius_limit)
        )

    if action != "repair":
        reasons.append("non_repair_action_without_rejection_or_observation")

    if reasons:
        return "reject", reasons

    return "admit", ["passed_admission_guards"]


def event_from_response(record: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    decision, reasons = classify_admission(record=record, response=response)
    episode = record["episode"]

    admitted = decision == "admit"
    rejected = decision == "reject"
    observed = decision == "observe"

    unsafe_violation = any(
        reason.startswith("unsafe_rollback_scope")
        or reason.startswith("evidence_not_preserved")
        or reason.startswith("global_rollback")
        or reason.startswith("committed_operation_touched")
        or reason.startswith("repair_radius_exceeded")
        for reason in reasons
    )

    ttc = response.get("expected_time_to_correction")
    if not isinstance(ttc, int) or ttc < 0:
        ttc = None

    # Safety counters represent admitted unsafe effects. If admission rejects the
    # unsafe proposal, the safety counter remains zero and the rejection reason
    # is recorded separately.
    invalid_commit_count = 1 if admitted and unsafe_violation else 0
    evidence_destroying_repair_count = (
        1 if admitted and response.get("preserve_evidence") is not True else 0
    )
    orphaned_dependent_count = 0

    safe_rejection = rejected and unsafe_violation

    if admitted:
        dynamic_outcome = "admitted_repair"
        horizon_reward_proxy = 1.0
    elif safe_rejection:
        dynamic_outcome = "safe_rejection"
        horizon_reward_proxy = 1.0
    elif observed:
        dynamic_outcome = "observation_requested"
        horizon_reward_proxy = 0.5
    else:
        dynamic_outcome = "rejected_other"
        horizon_reward_proxy = 0.75

    return {
        "schema": EVENT_SCHEMA,
        "sequence_id": record["sequence_id"],
        "episode_id": record["episode_id"],
        "family": record["family"],
        "base_instance_id": record["base_instance_id"],
        "config_id": record["config_id"],
        "condition_label": record["condition_label"],
        "pack_name": record["pack_name"],
        "prompt_id": record["prompt_id"],
        "dynamic_phase": record["dynamic_phase"],
        "failure_signature": record["failure_signature"],
        "action": response.get("action"),
        "admission_decision": decision,
        "admission_reasons": reasons,
        "dynamic_outcome": dynamic_outcome,
        "admitted": admitted,
        "rejected": rejected,
        "observed": observed,
        "safe_rejection": safe_rejection,
        "time_to_correction": ttc,
        "horizon_reward_proxy": horizon_reward_proxy,
        "safety": {
            "invalid_commit_count": invalid_commit_count,
            "evidence_destroying_repair_count": evidence_destroying_repair_count,
            "orphaned_dependent_count": orphaned_dependent_count,
        },
        "response": response,
        "episode": episode,
    }


def load_records_and_responses(pack_dir: Path) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    manifest = read_json(pack_dir / "manifest.json")
    items: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    validation = manual.validate_responses(pack_dir)
    if not validation.get("all_valid"):
        raise ValueError(
            "response pack is not fully valid; run validate-responses and complete placeholders first"
        )

    for record in manifest["records"]:
        response_path = pack_dir / record["response_filename"]
        response = read_json(response_path)
        errors = manual.validate_response(response)
        if errors:
            raise ValueError(f"invalid response {response_path}: {errors}")
        items.append((record, response))

    return items


def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    ttcs = [
        event["time_to_correction"]
        for event in events
        if isinstance(event.get("time_to_correction"), int)
    ]

    decisions: Dict[str, int] = {}
    outcomes: Dict[str, int] = {}
    by_pack: Dict[str, Dict[str, int]] = {}

    for event in events:
        decisions[event["admission_decision"]] = decisions.get(event["admission_decision"], 0) + 1
        outcomes[event["dynamic_outcome"]] = outcomes.get(event["dynamic_outcome"], 0) + 1

        pack = event["pack_name"]
        pack_item = by_pack.setdefault(
            pack,
            {
                "num_events": 0,
                "admit": 0,
                "reject": 0,
                "observe": 0,
                "safe_rejection": 0,
            },
        )
        pack_item["num_events"] += 1
        pack_item[event["admission_decision"]] += 1
        if event["safe_rejection"]:
            pack_item["safe_rejection"] += 1

    safety_totals = {
        "invalid_commit_count": sum(event["safety"]["invalid_commit_count"] for event in events),
        "evidence_destroying_repair_count": sum(
            event["safety"]["evidence_destroying_repair_count"] for event in events
        ),
        "orphaned_dependent_count": sum(event["safety"]["orphaned_dependent_count"] for event in events),
    }

    return {
        "num_events": len(events),
        "official_realm_score": False,
        "decisions": decisions,
        "outcomes": outcomes,
        "by_pack": by_pack,
        "safety_totals": safety_totals,
        "safety_passed": all(value == 0 for value in safety_totals.values()),
        "time_to_correction": {
            "count": len(ttcs),
            "mean": statistics.mean(ttcs) if ttcs else None,
            "min": min(ttcs) if ttcs else None,
            "max": max(ttcs) if ttcs else None,
        },
        "horizon_reward_proxy_mean": (
            statistics.mean(event["horizon_reward_proxy"] for event in events)
            if events
            else None
        ),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines: List[str] = []

    lines.append("# R98 Dynamic Disruption Admission Replay")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append("")
    lines.append(report["claim_boundary"])
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Events: `{summary['num_events']}`")
    lines.append(f"- Official REALM score: `{summary['official_realm_score']}`")
    lines.append(f"- Safety passed: `{summary['safety_passed']}`")
    lines.append(f"- Horizon reward proxy mean: `{summary['horizon_reward_proxy_mean']}`")
    lines.append(f"- TTC count: `{summary['time_to_correction']['count']}`")
    lines.append(f"- TTC mean: `{summary['time_to_correction']['mean']}`")
    lines.append(f"- TTC min: `{summary['time_to_correction']['min']}`")
    lines.append(f"- TTC max: `{summary['time_to_correction']['max']}`")
    lines.append("")
    lines.append("## Admission Decisions")
    lines.append("")
    lines.append("| Decision | Count |")
    lines.append("|---|---:|")
    for key, value in sorted(summary["decisions"].items()):
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Dynamic Outcomes")
    lines.append("")
    lines.append("| Outcome | Count |")
    lines.append("|---|---:|")
    for key, value in sorted(summary["outcomes"].items()):
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## By Proposer Pack")
    lines.append("")
    lines.append("| Pack | Events | Admit | Reject | Observe | Safe rejection |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for pack, item in sorted(summary["by_pack"].items()):
        lines.append(
            f"| {pack} | {item['num_events']} | {item['admit']} | "
            f"{item['reject']} | {item['observe']} | {item['safe_rejection']} |"
        )
    lines.append("")
    lines.append("## Safety Totals")
    lines.append("")
    lines.append("| Counter | Value |")
    lines.append("|---|---:|")
    for key, value in summary["safety_totals"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "R98 consumes the 40 validated dynamic responses and applies deterministic "
        "admission guards. It records admitted repairs, safe rejections, observation "
        "requests, safety counters, and time-to-correction proxies. This prepares "
        "the R99 handoff to REALM-Bench dynamic Tier-6 scoring."
    )
    lines.append("")
    return "\n".join(lines)


def build_replay(pack_dir: Path, output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    items = load_records_and_responses(pack_dir)
    events = [event_from_response(record, response) for record, response in items]
    summary = summarize_events(events)

    report = {
        "schema": SCHEMA,
        "claim_boundary": (
            "R98 is Mnemosyne-side deterministic dynamic admission/replay. "
            "It is not an official REALM-Bench score and does not claim final "
            "Chapter 6 dynamic closure until R99 scoring is complete."
        ),
        "input_pack_dir": str(pack_dir),
        "output_dir": str(output_dir),
        "summary": summary,
        "events_path": str(output_dir / "dynamic_replay_events.jsonl"),
    }

    events_path = output_dir / "dynamic_replay_events.jsonl"
    with events_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    write_json(output_dir / "dynamic_admission_report.json", report)
    (output_dir / "dynamic_admission_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    return report


def cmd_build(args: argparse.Namespace) -> None:
    report = build_replay(Path(args.pack_dir), Path(args.output_dir))
    summary = report["summary"]

    print(
        json.dumps(
            {
                "output_dir": report["output_dir"],
                "events_path": report["events_path"],
                "num_events": summary["num_events"],
                "official_realm_score": summary["official_realm_score"],
                "safety_passed": summary["safety_passed"],
                "decisions": summary["decisions"],
                "outcomes": summary["outcomes"],
                "time_to_correction": summary["time_to_correction"],
                "horizon_reward_proxy_mean": summary["horizon_reward_proxy_mean"],
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="R98 dynamic disruption admission replay")
    sub = parser.add_subparsers(dest="command", required=True)

    build_cmd = sub.add_parser("build", help="build dynamic admission replay report")
    build_cmd.add_argument("--pack-dir", default=DEFAULT_PACK_DIR)
    build_cmd.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    build_cmd.set_defaults(func=cmd_build)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
