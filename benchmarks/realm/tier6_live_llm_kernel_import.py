#!/usr/bin/env python3
"""R83.5b deterministic import/report for REALM Tier-6 live LLM packs.

This script reads manual live-LLM response packs produced by
tier6_live_llm_manual.py and emits deterministic comparison reports.

It intentionally does not commit nondeterministic events.jsonl traces.
The output is a stable pre-kernel/kernel-import comparison artifact for:

- Claude
- GPT
- DeepSeek expert
- DeepSeek instant

Claim boundary:
This is a deterministic live-pack comparison/import report. It is not yet
API automation and not yet a production CTL-domain StateView realization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_PACKS: dict[str, str] = {
    "claude": "results/realm_tier6_live_llm_manual/claude_e7_pilot",
    "gpt": "results/realm_tier6_live_llm_manual/gpt_e7_pilot",
    "deepseek_expert": "results/realm_tier6_live_llm_manual/deepseek_e7_pilot",
    "deepseek_instant": "results/realm_tier6_live_llm_manual/deepseek_instant_e7_pilot",
}

REQUIRED_FIELDS = {
    "proposal_summary",
    "action",
    "predicted_outcome",
    "horizon_rationale",
    "evidence_to_preserve",
    "risk_factors",
    "confidence",
    "should_reject",
}

ACTIVE_TERMS = [
    "repair",
    "reschedule",
    "re-schedule",
    "reroute",
    "re-route",
    "right-shift",
    "reset",
    "maintenance",
    "replace",
    "reassign",
    "re-sequence",
    "resequence",
    "dispatch",
    "apply johnson",
    "spt",
    "shortest processing time",
    "release_all",
    "halt and restart",
]

OBSERVATION_TERMS = [
    "observe",
    "observation",
    "monitor",
    "inspect",
    "diagnostic",
    "snapshot",
    "validate",
    "request",
    "await",
    "preserve",
    "do not",
    "no-op",
    "state-gathering",
    "check current",
]

UNSUPPORTED_PATTERNS: list[tuple[str, str]] = [
    ("machine_id", r"\b(?:Machine|machine|M)\s*-?\s*M?\d+\b|\bM\d+\b|\bMachine-\d+\b"),
    ("workstation_id", r"\bWorkstation\s+[A-Z]\d+\b|\bcritical workstation\s+[A-Z]\d+\b|\bC\d+\b"),
    ("job_id", r"\bJob\s+J\d+\b|\bJobs?\s+J\d+\b|\bJ\d+['’]s\b|\bJ\d+\s+(?:operation|op|completes|due|processing|at|partial)"),
    ("operation_time", r"\bt\s*=\s*\d+\b|\bt\s*=\s*\d+\s*(?:to|..|-)\s*t?\s*\d+\b|\bfrom\s+t\s*=\s*\d+\s+to\s+t\s*=\s*\d+\b"),
    ("quantitative_operational", r"\b\d+(?:\.\d+)?\s*(?:%|hours?|hrs?|time units?|units|°C|h)\b|\b\d+\s*-\s*\d+%\b|\b\d+\s*×\b|\b\d+x\b"),
    ("sensor_or_fault", r"\b(?:temperature|vibration|sensor|bearing|spindle|tool wear|scrap rate|MTBF|mean time between failures|fault code)\b"),
    ("specific_heuristic", r"\b(?:Johnson's rule|Johnson rule|SPT|shortest-processing-time|shortest processing time|critical-ratio|earliest-due)\b"),
    ("concrete_inventory_or_log", r"\b(?:inventory|operator shift notes|maintenance records|repair logs|breakdown logs|spare parts)\b"),
]


@dataclass(frozen=True)
class ResponseRecord:
    pack_name: str
    key: str
    episode_id: int
    response_path: str
    response_sha256: str
    data: dict[str, Any]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_episode_from_key(key: str) -> int:
    match = re.search(r"__e(\d{2})$", key)
    if not match:
        raise ValueError(f"cannot parse episode from key: {key}")
    return int(match.group(1))


def load_json_response(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"response must be a JSON object: {path}")
    return data


def normalize_text(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def count_terms(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def unsupported_specificity(data: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(data)
    flags: list[dict[str, str]] = []

    for category, pattern in UNSUPPORTED_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(0)
            # Keep the report readable and deterministic.
            flags.append({"category": category, "value": value})

    deduped = []
    seen = set()
    for item in flags:
        key = (item["category"], item["value"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "count": len(deduped),
        "examples": deduped[:20],
    }


def classify_policy(data: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(data)
    active_score = count_terms(text, ACTIVE_TERMS)
    observation_score = count_terms(text, OBSERVATION_TERMS)

    if active_score >= 2 and observation_score >= 2:
        style = "mixed"
    elif active_score >= 2:
        style = "active_repair"
    elif observation_score >= 2:
        style = "observation_first"
    else:
        style = "unclear"

    return {
        "style": style,
        "active_score": active_score,
        "observation_score": observation_score,
    }


def deterministic_admission_recommendation(data: dict[str, Any], unsupported_count: int) -> str:
    """A deterministic recommendation, not a production admission decision."""
    if bool(data.get("should_reject")):
        return "model_requests_rejection"
    if unsupported_count >= 10:
        return "review_high_unsupported_specificity"
    if unsupported_count >= 5:
        return "admit_with_grounding_flags"
    return "admit_parseable_proposal"


def summarize_response(record: ResponseRecord) -> dict[str, Any]:
    data = record.data
    missing_fields = sorted(REQUIRED_FIELDS - set(data.keys()))
    policy = classify_policy(data)
    unsupported = unsupported_specificity(data)
    recommendation = deterministic_admission_recommendation(data, unsupported["count"])

    return {
        "pack_name": record.pack_name,
        "key": record.key,
        "episode_id": record.episode_id,
        "response_path": record.response_path,
        "response_sha256": record.response_sha256,
        "fields": sorted(data.keys()),
        "missing_required_fields": missing_fields,
        "should_reject": bool(data.get("should_reject")),
        "confidence": data.get("confidence"),
        "policy_style": policy["style"],
        "active_score": policy["active_score"],
        "observation_score": policy["observation_score"],
        "unsupported_specificity_count": unsupported["count"],
        "unsupported_specificity_examples": unsupported["examples"],
        "deterministic_admission_recommendation": recommendation,
        "proposal_summary": data.get("proposal_summary", ""),
    }


def load_pack(pack_name: str, pack_dir: Path) -> list[ResponseRecord]:
    response_dir = pack_dir / "responses" / "E7"
    if not response_dir.exists():
        raise FileNotFoundError(f"missing response dir: {response_dir}")

    records: list[ResponseRecord] = []
    for i in range(1, 11):
        key = f"E7__T6-7e17ef0cc5f3__e{i:02d}"
        path = response_dir / f"{key}.txt"
        if not path.exists():
            raise FileNotFoundError(f"missing response: {path}")
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        records.append(
            ResponseRecord(
                pack_name=pack_name,
                key=key,
                episode_id=parse_episode_from_key(key),
                response_path=str(path),
                response_sha256=sha256_text(text.strip()),
                data=data,
            )
        )
    return records


def summarize_pack(pack_name: str, records: list[ResponseRecord]) -> dict[str, Any]:
    response_summaries = [summarize_response(record) for record in records]

    policy_counts: dict[str, int] = {}
    recommendations: dict[str, int] = {}

    for item in response_summaries:
        policy_counts[item["policy_style"]] = policy_counts.get(item["policy_style"], 0) + 1
        rec = item["deterministic_admission_recommendation"]
        recommendations[rec] = recommendations.get(rec, 0) + 1

    confidences = [
        item["confidence"]
        for item in response_summaries
        if isinstance(item.get("confidence"), (int, float))
    ]
    unsupported_counts = [item["unsupported_specificity_count"] for item in response_summaries]

    return {
        "pack_name": pack_name,
        "num_responses": len(response_summaries),
        "num_parsed": len(response_summaries),
        "num_should_reject_true": sum(1 for item in response_summaries if item["should_reject"]),
        "confidence_mean": round(mean(confidences), 4) if confidences else None,
        "policy_counts": policy_counts,
        "admission_recommendation_counts": recommendations,
        "unsupported_specificity_total": sum(unsupported_counts),
        "unsupported_specificity_mean": round(mean(unsupported_counts), 4) if unsupported_counts else 0,
        "unsupported_specificity_max": max(unsupported_counts) if unsupported_counts else 0,
        "responses": response_summaries,
    }


def build_report(pack_map: dict[str, Path]) -> dict[str, Any]:
    packs = []
    for pack_name, pack_dir in pack_map.items():
        packs.append(summarize_pack(pack_name, load_pack(pack_name, pack_dir)))

    return {
        "schema": "realm_tier6_live_llm_kernel_import_report_v0",
        "claim_boundary": (
            "Deterministic live-pack comparison/import report only. "
            "Not API automation, not full CTL-domain StateView realization, "
            "and not confirmatory Chapter 6 evidence."
        ),
        "sequence_id": "T6-7e17ef0cc5f3",
        "config_id": "E7",
        "condition_label": "full_crt_stack",
        "packs": packs,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# R83.5b REALM Tier-6 Live LLM Kernel-Import Comparison Report")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append("")
    lines.append(report["claim_boundary"])
    lines.append("")
    lines.append("## Pilot")
    lines.append("")
    lines.append(f"- Sequence: `{report['sequence_id']}`")
    lines.append(f"- Config: `{report['config_id']}`")
    lines.append(f"- Condition label: `{report['condition_label']}`")
    lines.append("")
    lines.append("## Pack Summary")
    lines.append("")
    lines.append("| Pack | Responses | should_reject=true | Mean confidence | Policy counts | Unsupported specificity total | Admission recommendations |")
    lines.append("|---|---:|---:|---:|---|---:|---|")

    for pack in report["packs"]:
        lines.append(
            "| {pack_name} | {num_responses} | {num_should_reject_true} | {confidence_mean} | {policy_counts} | {unsupported_specificity_total} | {admission_recommendation_counts} |".format(
                **pack
            )
        )

    lines.append("")
    lines.append("## Per-Episode Summary")
    lines.append("")

    for pack in report["packs"]:
        lines.append(f"### {pack['pack_name']}")
        lines.append("")
        lines.append("| Episode | Reject? | Confidence | Policy | Unsupported count | Recommendation | Summary |")
        lines.append("|---:|---|---:|---|---:|---|---|")
        for item in pack["responses"]:
            summary = str(item["proposal_summary"]).replace("|", "\\|")
            if len(summary) > 120:
                summary = summary[:117] + "..."
            lines.append(
                f"| {item['episode_id']} | {item['should_reject']} | {item['confidence']} | "
                f"{item['policy_style']} | {item['unsupported_specificity_count']} | "
                f"{item['deterministic_admission_recommendation']} | {summary} |"
            )
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Claude is expected to appear as an active local-repair planner.")
    lines.append("- GPT is expected to appear as the most cautious observation/rejection baseline.")
    lines.append("- DeepSeek expert is expected to be more structured than DeepSeek instant, but still prone to unsupported concretization.")
    lines.append("- DeepSeek instant is expected to be higher variance and less controlled than expert mode.")
    lines.append("")
    lines.append("The report is deterministic and suitable for review. It does not commit nondeterministic `events.jsonl` traces.")
    lines.append("")
    return "\n".join(lines)


def parse_pack_args(values: list[str] | None) -> dict[str, Path]:
    if not values:
        return {name: Path(path) for name, path in DEFAULT_PACKS.items()}

    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"pack must be name=path, got: {value}")
        name, path = value.split("=", 1)
        result[name] = Path(path)
    return result


def cmd_report(args: argparse.Namespace) -> None:
    pack_map = parse_pack_args(args.pack)
    report = build_report(pack_map)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "comparison_report.json"
    md_path = out_dir / "comparison_report.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps({
        "output_dir": str(out_dir),
        "json": str(json_path),
        "markdown": str(md_path),
        "packs": [pack["pack_name"] for pack in report["packs"]],
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="build deterministic live-LLM comparison report")
    report.add_argument(
        "--output-dir",
        default="results/realm_tier6_live_llm_manual/kernel_import_report",
    )
    report.add_argument(
        "--pack",
        action="append",
        help="Optional pack override as name=path. Repeatable.",
    )
    report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
