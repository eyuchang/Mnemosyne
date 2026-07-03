#!/usr/bin/env python3
"""R86 deterministic REALM scorer handoff bundle for live-LLM Tier-6 records.

This script reads the R85 deterministic REALM score-bridge report and exports a
stable REALM-facing scorer handoff bundle.

It does not run the official REALM scorer yet.
It does not mutate runtime stores.
It does not emit nondeterministic events.jsonl files.

Claim boundary:
R86 phase 1 creates an official-scorer handoff bundle only. It is not official
REALM scoring, not API automation, not production CTL-domain StateView
realization, and not confirmatory Chapter 6 evidence.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any


DEFAULT_SCORE_BRIDGE_REPORT = (
    "results/realm_tier6_live_llm_manual/realm_score_bridge_report/"
    "realm_score_bridge_report.json"
)

DEFAULT_OUTPUT_DIR = (
    "results/realm_tier6_live_llm_manual/realm_scorer_handoff"
)

SCHEMA = "realm_tier6_live_llm_realm_scorer_handoff_bundle_v0"
CASE_SCHEMA = "realm_tier6_live_llm_realm_scorer_case_v0"


def deterministic_id(kind: str, *parts: object) -> str:
    seed = ":".join([kind, *[str(part) for part in parts]])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def admission_label(record: dict[str, Any]) -> str:
    if record.get("unsafe_admission"):
        return "unsafe_admission"
    if record.get("clean_admission"):
        return "clean_admission"
    if record.get("flagged_admission"):
        return "flagged_admission"
    if record.get("protective_rejection"):
        return "protective_rejection"
    if record.get("rejected"):
        return "rejected"
    return "unknown"


def scorer_action(record: dict[str, Any]) -> str:
    """Map Mnemosyne admission state to REALM-facing scorer action."""
    label = admission_label(record)

    if label == "clean_admission":
        return "score_admitted_proposal"
    if label == "flagged_admission":
        return "score_admitted_with_grounding_flags"
    if label == "protective_rejection":
        return "score_rejection_as_protective_screening"
    if label == "unsafe_admission":
        return "score_as_safety_failure"
    if label == "rejected":
        return "score_rejection"
    return "score_unknown"


def build_case(report: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    sequence_id = str(report.get("sequence_id"))
    config_id = str(report.get("config_id"))
    pack_name = str(record.get("pack_name"))
    episode_id = int(record.get("episode_id"))

    case_id = deterministic_id(
        "realm-tier6-live-llm-official-scorer-case",
        sequence_id,
        config_id,
        pack_name,
        episode_id,
        record.get("source_record_id"),
    )

    return {
        "schema": CASE_SCHEMA,
        "case_id": case_id,
        "sequence_id": sequence_id,
        "config_id": config_id,
        "condition_label": report.get("condition_label"),
        "pack_name": pack_name,
        "episode_id": episode_id,
        "source": {
            "score_bridge_schema": report.get("schema"),
            "source_replay_id": record.get("source_replay_id"),
            "source_record_id": record.get("source_record_id"),
        },
        "mnemosyne_admission": {
            "admitted": bool(record.get("admitted")),
            "rejected": bool(record.get("rejected")),
            "label": admission_label(record),
            "grounding_flags": list(record.get("grounding_flags", [])),
            "unsupported_specificity_count": int(
                record.get("unsupported_specificity_count") or 0
            ),
            "policy_style": record.get("policy_style"),
            "passed_runtime_checks": bool(record.get("passed_runtime_checks")),
        },
        "realm_scorer_handoff": {
            "official_realm_score": False,
            "scorer_action": scorer_action(record),
            "requires_official_realm_scorer": True,
            "safety_passed_before_official_scoring": not bool(
                record.get("unsafe_admission")
            ),
            "screened_before_commit": bool(record.get("rejected")),
            "proposal_summary": record.get("proposal_summary", ""),
        },
    }


def build_bundle(score_bridge_report: dict[str, Any]) -> dict[str, Any]:
    records = list(score_bridge_report.get("records", []))
    cases = [build_case(score_bridge_report, record) for record in records]

    by_pack: dict[str, dict[str, int]] = {}
    for case in cases:
        pack_name = str(case["pack_name"])
        label = str(case["mnemosyne_admission"]["label"])
        action = str(case["realm_scorer_handoff"]["scorer_action"])

        entry = by_pack.setdefault(
            pack_name,
            {
                "cases": 0,
                "clean_admission": 0,
                "flagged_admission": 0,
                "protective_rejection": 0,
                "unsafe_admission": 0,
                "rejected": 0,
                "unknown": 0,
                "score_admitted_proposal": 0,
                "score_admitted_with_grounding_flags": 0,
                "score_rejection_as_protective_screening": 0,
                "score_as_safety_failure": 0,
                "score_rejection": 0,
                "score_unknown": 0,
            },
        )
        entry["cases"] += 1
        entry[label] = entry.get(label, 0) + 1
        entry[action] = entry.get(action, 0) + 1

    return {
        "schema": SCHEMA,
        "source_schema": score_bridge_report.get("schema"),
        "claim_boundary": (
            "Deterministic REALM scorer handoff bundle only. "
            "This is not official REALM scoring, does not mutate runtime stores, "
            "does not emit nondeterministic events.jsonl, and is not confirmatory "
            "Chapter 6 evidence."
        ),
        "sequence_id": score_bridge_report.get("sequence_id"),
        "config_id": score_bridge_report.get("config_id"),
        "condition_label": score_bridge_report.get("condition_label"),
        "official_realm_score": False,
        "handoff_type": "official_realm_scorer_input_bundle",
        "num_cases": len(cases),
        "pack_summary": by_pack,
        "cases": cases,
    }


def render_cases_jsonl(cases: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(case, sort_keys=True, ensure_ascii=False) for case in cases) + "\n"


def render_markdown(bundle: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# R86 REALM Tier-6 Live LLM Official Scorer Handoff")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append("")
    lines.append(bundle["claim_boundary"])
    lines.append("")
    lines.append("## Pilot")
    lines.append("")
    lines.append(f"- Sequence: `{bundle['sequence_id']}`")
    lines.append(f"- Config: `{bundle['config_id']}`")
    lines.append(f"- Condition label: `{bundle['condition_label']}`")
    lines.append(f"- Official REALM score: `{bundle['official_realm_score']}`")
    lines.append(f"- Handoff type: `{bundle['handoff_type']}`")
    lines.append(f"- Cases: `{bundle['num_cases']}`")
    lines.append("")
    lines.append("## Pack Summary")
    lines.append("")
    lines.append("| Pack | Cases | Clean admit | Flagged admit | Protective reject | Unsafe admit | Rejected |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for pack_name, item in bundle["pack_summary"].items():
        lines.append(
            f"| {pack_name} | {item['cases']} | {item['clean_admission']} | "
            f"{item['flagged_admission']} | {item['protective_rejection']} | "
            f"{item['unsafe_admission']} | {item['rejected']} |"
        )

    lines.append("")
    lines.append("## Scorer Action Summary")
    lines.append("")
    lines.append("| Pack | Score admitted | Score admitted with flags | Score protective rejection | Score safety failure | Score rejection |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for pack_name, item in bundle["pack_summary"].items():
        lines.append(
            f"| {pack_name} | {item['score_admitted_proposal']} | "
            f"{item['score_admitted_with_grounding_flags']} | "
            f"{item['score_rejection_as_protective_screening']} | "
            f"{item['score_as_safety_failure']} | {item['score_rejection']} |"
        )

    lines.append("")
    lines.append("## Per-Case Handoff")
    lines.append("")
    lines.append("| Pack | Episode | Admission label | Scorer action | Unsupported | Policy | Summary |")
    lines.append("|---|---:|---|---|---:|---|---|")

    for case in bundle["cases"]:
        admission = case["mnemosyne_admission"]
        handoff = case["realm_scorer_handoff"]
        summary = str(handoff.get("proposal_summary", "")).replace("|", "\\|")
        if len(summary) > 100:
            summary = summary[:97] + "..."
        lines.append(
            f"| {case['pack_name']} | {case['episode_id']} | "
            f"{admission['label']} | {handoff['scorer_action']} | "
            f"{admission['unsupported_specificity_count']} | "
            f"{admission['policy_style']} | {summary} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "This handoff bundle converts the R85 Mnemosyne-side score bridge into "
        "stable, official-REALM-scorer-facing cases."
    )
    lines.append("")
    lines.append(
        "The bundle intentionally does not claim official REALM scoring. It defines "
        "the deterministic input contract for the official scorer integration."
    )
    lines.append("")

    return "\n".join(lines)


def cmd_export(args: argparse.Namespace) -> None:
    score_bridge_path = Path(args.score_bridge_report)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    score_bridge_report = load_json(score_bridge_path)
    bundle = build_bundle(score_bridge_report)

    json_path = output_dir / "realm_scorer_handoff_bundle.json"
    jsonl_path = output_dir / "realm_scorer_handoff_cases.jsonl"
    md_path = output_dir / "realm_scorer_handoff_report.md"

    json_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    jsonl_path.write_text(render_cases_jsonl(bundle["cases"]), encoding="utf-8")
    md_path.write_text(render_markdown(bundle), encoding="utf-8")

    print(
        json.dumps(
            {
                "score_bridge_report": str(score_bridge_path),
                "output_dir": str(output_dir),
                "json": str(json_path),
                "jsonl": str(jsonl_path),
                "markdown": str(md_path),
                "num_cases": bundle["num_cases"],
                "official_realm_score": bundle["official_realm_score"],
                "handoff_type": bundle["handoff_type"],
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="build deterministic REALM scorer handoff bundle")
    export.add_argument("--score-bridge-report", default=DEFAULT_SCORE_BRIDGE_REPORT)
    export.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
