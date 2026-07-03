#!/usr/bin/env python3
"""R83.5c deterministic kernel-admission trace attachment for REALM Tier-6 live LLM packs.

This script reads the deterministic R83.5b comparison report and emits stable
kernel-admission attachment records with deterministic IDs and synthetic
deterministic timestamps.

It does not write nondeterministic events.jsonl files and does not mutate the
runtime store.

Claim boundary:
This is a deterministic trace attachment/report layer. It is not API automation,
not production CTL-domain StateView realization, and not confirmatory Chapter 6
evidence.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any


DEFAULT_COMPARISON_REPORT = (
    "results/realm_tier6_live_llm_manual/kernel_import_report/comparison_report.json"
)

DEFAULT_OUTPUT_DIR = (
    "results/realm_tier6_live_llm_manual/kernel_trace_report"
)

SCHEMA = "realm_tier6_live_llm_kernel_trace_report_v0"
RECORD_SCHEMA = "realm_tier6_live_llm_kernel_trace_record_v0"

DECISION_TO_KERNEL_METHOD = {
    "admit_parseable_proposal": "accept_via_kernel",
    "admit_with_grounding_flags": "accept_via_kernel_with_flags",
    "review_high_unsupported_specificity": "reject_before_commit",
    "model_requests_rejection": "reject_before_commit",
}


def deterministic_id(kind: str, *parts: object) -> str:
    seed = ":".join([kind, *[str(part) for part in parts]])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def deterministic_event_time(pack_index: int, episode_id: int) -> str:
    return f"2000-01-01T00:{pack_index:02d}:{episode_id:02d}Z"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def grounding_flags(response: dict[str, Any]) -> list[str]:
    flags: list[str] = []

    unsupported_count = int(response.get("unsupported_specificity_count", 0))
    recommendation = str(response.get("deterministic_admission_recommendation", ""))

    if unsupported_count >= 10:
        flags.append("high_unsupported_specificity")
    elif unsupported_count >= 5:
        flags.append("moderate_unsupported_specificity")

    if bool(response.get("should_reject")):
        flags.append("model_requested_rejection")

    if recommendation == "review_high_unsupported_specificity":
        flags.append("requires_human_review")

    return flags


def admitted_for_recommendation(recommendation: str) -> bool:
    return recommendation in {
        "admit_parseable_proposal",
        "admit_with_grounding_flags",
    }


def kernel_method_for_recommendation(recommendation: str) -> str:
    return DECISION_TO_KERNEL_METHOD.get(recommendation, "reject_before_commit")


def build_trace_record(
    *,
    report: dict[str, Any],
    pack: dict[str, Any],
    response: dict[str, Any],
    pack_index: int,
    event_index: int,
) -> dict[str, Any]:
    sequence_id = str(report["sequence_id"])
    config_id = str(report["config_id"])
    pack_name = str(pack["pack_name"])
    episode_id = int(response["episode_id"])
    key = str(response["key"])
    recommendation = str(response["deterministic_admission_recommendation"])
    method = kernel_method_for_recommendation(recommendation)
    flags = grounding_flags(response)

    trace_id = deterministic_id(
        "realm-tier6-live-llm-kernel-trace",
        sequence_id,
        config_id,
        pack_name,
    )
    record_id = deterministic_id(
        "realm-tier6-live-llm-kernel-record",
        sequence_id,
        config_id,
        pack_name,
        episode_id,
        str(response.get("response_sha256", "")),
    )

    return {
        "schema": RECORD_SCHEMA,
        "trace_id": trace_id,
        "record_id": record_id,
        "event_index": event_index,
        "event_time": deterministic_event_time(pack_index, episode_id),
        "event_time_note": "synthetic deterministic timestamp for stable trace reports",
        "sequence_id": sequence_id,
        "config_id": config_id,
        "condition_label": report.get("condition_label"),
        "pack_name": pack_name,
        "episode_id": episode_id,
        "proposal_ref": {
            "key": key,
            "response_path": response.get("response_path"),
            "response_sha256": response.get("response_sha256"),
        },
        "kernel_admission_record": {
            "adapter": "KernelAdmissionAdapter",
            "method": method,
            "admitted": admitted_for_recommendation(recommendation),
            "decision_label": recommendation,
            "grounding_flags": flags,
            "input_summary": {
                "should_reject": bool(response.get("should_reject")),
                "confidence": response.get("confidence"),
                "policy_style": response.get("policy_style"),
                "active_score": response.get("active_score"),
                "observation_score": response.get("observation_score"),
                "unsupported_specificity_count": response.get(
                    "unsupported_specificity_count"
                ),
            },
            "proposal_summary": response.get("proposal_summary", ""),
        },
    }


def build_trace_report(comparison_report: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    event_index = 0

    for pack_index, pack in enumerate(comparison_report.get("packs", [])):
        for response in pack.get("responses", []):
            records.append(
                build_trace_record(
                    report=comparison_report,
                    pack=pack,
                    response=response,
                    pack_index=pack_index,
                    event_index=event_index,
                )
            )
            event_index += 1

    method_counts: dict[str, int] = {}
    pack_counts: dict[str, int] = {}
    admitted_count = 0
    rejected_count = 0

    for record in records:
        method = record["kernel_admission_record"]["method"]
        pack_name = record["pack_name"]
        method_counts[method] = method_counts.get(method, 0) + 1
        pack_counts[pack_name] = pack_counts.get(pack_name, 0) + 1

        if record["kernel_admission_record"]["admitted"]:
            admitted_count += 1
        else:
            rejected_count += 1

    return {
        "schema": SCHEMA,
        "source_schema": comparison_report.get("schema"),
        "claim_boundary": (
            "Deterministic kernel-admission trace attachment report only. "
            "Does not mutate runtime store, does not emit nondeterministic "
            "events.jsonl, and is not confirmatory Chapter 6 evidence."
        ),
        "sequence_id": comparison_report.get("sequence_id"),
        "config_id": comparison_report.get("config_id"),
        "condition_label": comparison_report.get("condition_label"),
        "num_records": len(records),
        "num_admitted": admitted_count,
        "num_rejected": rejected_count,
        "kernel_method_counts": method_counts,
        "pack_counts": pack_counts,
        "records": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# R83.5c REALM Tier-6 Live LLM Kernel-Trace Attachment Report")
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
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Records: `{report['num_records']}`")
    lines.append(f"- Admitted: `{report['num_admitted']}`")
    lines.append(f"- Rejected before commit: `{report['num_rejected']}`")
    lines.append(f"- Kernel method counts: `{report['kernel_method_counts']}`")
    lines.append(f"- Pack counts: `{report['pack_counts']}`")
    lines.append("")
    lines.append("## Per-Pack Kernel Attachment Summary")
    lines.append("")
    lines.append("| Pack | Records | accept_via_kernel | accept_via_kernel_with_flags | reject_before_commit |")
    lines.append("|---|---:|---:|---:|---:|")

    per_pack: dict[str, dict[str, int]] = {}
    for record in report["records"]:
        pack_name = record["pack_name"]
        method = record["kernel_admission_record"]["method"]
        per_pack.setdefault(
            pack_name,
            {
                "records": 0,
                "accept_via_kernel": 0,
                "accept_via_kernel_with_flags": 0,
                "reject_before_commit": 0,
            },
        )
        per_pack[pack_name]["records"] += 1
        per_pack[pack_name][method] = per_pack[pack_name].get(method, 0) + 1

    for pack_name, counts in per_pack.items():
        lines.append(
            f"| {pack_name} | {counts['records']} | "
            f"{counts.get('accept_via_kernel', 0)} | "
            f"{counts.get('accept_via_kernel_with_flags', 0)} | "
            f"{counts.get('reject_before_commit', 0)} |"
        )

    lines.append("")
    lines.append("## Per-Episode Records")
    lines.append("")
    lines.append("| Pack | Episode | Method | Admitted | Flags | Policy | Unsupported | Summary |")
    lines.append("|---|---:|---|---|---|---|---:|---|")

    for record in report["records"]:
        admission = record["kernel_admission_record"]
        summary = str(admission.get("proposal_summary", "")).replace("|", "\\|")
        if len(summary) > 110:
            summary = summary[:107] + "..."
        flags = ",".join(admission.get("grounding_flags", []))
        input_summary = admission["input_summary"]
        lines.append(
            f"| {record['pack_name']} | {record['episode_id']} | "
            f"{admission['method']} | {admission['admitted']} | "
            f"{flags} | {input_summary.get('policy_style')} | "
            f"{input_summary.get('unsupported_specificity_count')} | {summary} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "This report attaches each deterministic live-LLM response summary to a "
        "stable kernel-admission-style record using deterministic UUIDv5 IDs and "
        "synthetic deterministic timestamps."
    )
    lines.append("")
    lines.append(
        "The artifact is suitable for review and regression testing. It deliberately "
        "does not emit nondeterministic raw trace files."
    )
    lines.append("")

    return "\n".join(lines)


def cmd_trace(args: argparse.Namespace) -> None:
    comparison_path = Path(args.comparison_report)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_report = load_json(comparison_path)
    trace_report = build_trace_report(comparison_report)

    json_path = output_dir / "kernel_trace_report.json"
    md_path = output_dir / "kernel_trace_report.md"

    json_path.write_text(
        json.dumps(trace_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(trace_report), encoding="utf-8")

    print(
        json.dumps(
            {
                "comparison_report": str(comparison_path),
                "output_dir": str(output_dir),
                "json": str(json_path),
                "markdown": str(md_path),
                "num_records": trace_report["num_records"],
                "num_admitted": trace_report["num_admitted"],
                "num_rejected": trace_report["num_rejected"],
                "kernel_method_counts": trace_report["kernel_method_counts"],
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    trace = sub.add_parser("trace", help="build deterministic kernel trace report")
    trace.add_argument("--comparison-report", default=DEFAULT_COMPARISON_REPORT)
    trace.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    trace.set_defaults(func=cmd_trace)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
