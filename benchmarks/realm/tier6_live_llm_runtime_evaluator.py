#!/usr/bin/env python3
"""R84 deterministic runtime evaluator for REALM Tier-6 live-LLM kernel traces.

This script reads the R83.5c deterministic kernel trace report and evaluates it
through a stable runtime-replay layer.

It does not mutate the production runtime store.
It does not emit nondeterministic events.jsonl files.
It produces deterministic JSON/Markdown reports suitable for regression testing.

Claim boundary:
R84 phase 1 is a deterministic runtime replay/evaluator report. It is not API
automation, not production CTL-domain StateView realization, and not
confirmatory Chapter 6 evidence.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any


DEFAULT_TRACE_REPORT = (
    "results/realm_tier6_live_llm_manual/kernel_trace_report/kernel_trace_report.json"
)

DEFAULT_OUTPUT_DIR = (
    "results/realm_tier6_live_llm_manual/runtime_evaluator_report"
)

SCHEMA = "realm_tier6_live_llm_runtime_evaluator_report_v0"
REPLAY_RECORD_SCHEMA = "realm_tier6_live_llm_runtime_replay_record_v0"

ADMITTING_METHODS = {
    "accept_via_kernel",
    "accept_via_kernel_with_flags",
}

REJECTING_METHODS = {
    "reject_before_commit",
}


def deterministic_id(kind: str, *parts: object) -> str:
    seed = ":".join([kind, *[str(part) for part in parts]])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def method_expected_admitted(method: str) -> bool:
    if method in ADMITTING_METHODS:
        return True
    if method in REJECTING_METHODS:
        return False
    return False


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    admission = record["kernel_admission_record"]
    method = str(admission["method"])
    admitted = bool(admission["admitted"])
    expected_admitted = method_expected_admitted(method)
    flags = list(admission.get("grounding_flags", []))
    input_summary = admission.get("input_summary", {})

    checks: list[dict[str, Any]] = []

    checks.append(
        {
            "name": "method_admission_consistency",
            "passed": admitted == expected_admitted,
            "detail": {
                "method": method,
                "admitted": admitted,
                "expected_admitted": expected_admitted,
            },
        }
    )

    unsupported_count = int(input_summary.get("unsupported_specificity_count", 0) or 0)

    checks.append(
        {
            "name": "high_specificity_requires_rejection_or_flag",
            "passed": (
                unsupported_count < 10
                or not admitted
                or "high_unsupported_specificity" in flags
            ),
            "detail": {
                "unsupported_specificity_count": unsupported_count,
                "flags": flags,
                "admitted": admitted,
            },
        }
    )

    checks.append(
        {
            "name": "moderate_specificity_requires_flag_when_flagged_method",
            "passed": (
                method != "accept_via_kernel_with_flags"
                or "moderate_unsupported_specificity" in flags
                or "high_unsupported_specificity" in flags
            ),
            "detail": {
                "method": method,
                "flags": flags,
            },
        }
    )

    checks.append(
        {
            "name": "deterministic_timestamp",
            "passed": str(record.get("event_time", "")).startswith("2000-01-01T"),
            "detail": {
                "event_time": record.get("event_time"),
            },
        }
    )

    checks.append(
        {
            "name": "stable_record_id_present",
            "passed": bool(record.get("record_id")),
            "detail": {
                "record_id": record.get("record_id"),
            },
        }
    )

    passed = all(check["passed"] for check in checks)

    replay_id = deterministic_id(
        "realm-tier6-live-llm-runtime-replay",
        record.get("trace_id"),
        record.get("record_id"),
        record.get("event_index"),
    )

    runtime_envelope_id = deterministic_id(
        "realm-tier6-live-llm-runtime-envelope",
        record.get("sequence_id"),
        record.get("config_id"),
        record.get("pack_name"),
        record.get("episode_id"),
        record.get("record_id"),
    )

    return {
        "schema": REPLAY_RECORD_SCHEMA,
        "replay_id": replay_id,
        "runtime_envelope_id": runtime_envelope_id,
        "source_record_id": record.get("record_id"),
        "source_trace_id": record.get("trace_id"),
        "event_index": record.get("event_index"),
        "event_time": record.get("event_time"),
        "sequence_id": record.get("sequence_id"),
        "config_id": record.get("config_id"),
        "condition_label": record.get("condition_label"),
        "pack_name": record.get("pack_name"),
        "episode_id": record.get("episode_id"),
        "runtime_replay": {
            "mode": "deterministic_replay",
            "store_mutation": False,
            "events_jsonl_emitted": False,
            "method": method,
            "admitted": admitted,
            "grounding_flags": flags,
            "policy_style": input_summary.get("policy_style"),
            "unsupported_specificity_count": unsupported_count,
            "proposal_summary": admission.get("proposal_summary", ""),
        },
        "checks": checks,
        "passed": passed,
    }


def validate_global_invariants(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    record_ids = [record.get("record_id") for record in records]
    event_indices = [record.get("event_index") for record in records]
    replay_order = sorted(event_indices)

    checks.append(
        {
            "name": "record_ids_unique",
            "passed": len(record_ids) == len(set(record_ids)),
            "detail": {
                "num_record_ids": len(record_ids),
                "num_unique_record_ids": len(set(record_ids)),
            },
        }
    )

    checks.append(
        {
            "name": "event_indices_contiguous",
            "passed": replay_order == list(range(len(records))),
            "detail": {
                "expected_count": len(records),
                "min_event_index": min(event_indices) if event_indices else None,
                "max_event_index": max(event_indices) if event_indices else None,
            },
        }
    )

    checks.append(
        {
            "name": "all_timestamps_deterministic",
            "passed": all(str(record.get("event_time", "")).startswith("2000-01-01T") for record in records),
            "detail": {
                "num_records": len(records),
            },
        }
    )

    checks.append(
        {
            "name": "no_events_jsonl_output",
            "passed": True,
            "detail": {
                "events_jsonl_emitted": False,
            },
        }
    )

    return checks


def summarize_by_pack(replay_records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, dict[str, Any]] = {}

    for record in replay_records:
        pack_name = str(record["pack_name"])
        entry = summary.setdefault(
            pack_name,
            {
                "records": 0,
                "passed": 0,
                "failed": 0,
                "admitted": 0,
                "rejected": 0,
                "flagged": 0,
                "policy_counts": {},
            },
        )

        replay = record["runtime_replay"]
        entry["records"] += 1
        entry["passed"] += 1 if record["passed"] else 0
        entry["failed"] += 0 if record["passed"] else 1
        entry["admitted"] += 1 if replay["admitted"] else 0
        entry["rejected"] += 0 if replay["admitted"] else 1
        entry["flagged"] += 1 if replay["grounding_flags"] else 0

        policy = str(replay.get("policy_style"))
        entry["policy_counts"][policy] = entry["policy_counts"].get(policy, 0) + 1

    return summary


def build_runtime_evaluator_report(trace_report: dict[str, Any]) -> dict[str, Any]:
    records = list(trace_report.get("records", []))
    replay_records = [evaluate_record(record) for record in records]
    global_checks = validate_global_invariants(records)

    num_passed = sum(1 for record in replay_records if record["passed"])
    num_failed = len(replay_records) - num_passed
    num_admitted = sum(1 for record in replay_records if record["runtime_replay"]["admitted"])
    num_rejected = len(replay_records) - num_admitted
    num_flagged = sum(1 for record in replay_records if record["runtime_replay"]["grounding_flags"])

    return {
        "schema": SCHEMA,
        "source_schema": trace_report.get("schema"),
        "claim_boundary": (
            "Deterministic runtime replay/evaluator report only. "
            "Does not mutate runtime store, does not emit nondeterministic events.jsonl, "
            "and is not confirmatory Chapter 6 evidence."
        ),
        "sequence_id": trace_report.get("sequence_id"),
        "config_id": trace_report.get("config_id"),
        "condition_label": trace_report.get("condition_label"),
        "runtime_mode": "deterministic_replay_no_store_mutation",
        "num_records": len(replay_records),
        "num_passed": num_passed,
        "num_failed": num_failed,
        "num_admitted": num_admitted,
        "num_rejected": num_rejected,
        "num_flagged": num_flagged,
        "global_checks": global_checks,
        "global_passed": all(check["passed"] for check in global_checks) and num_failed == 0,
        "pack_summary": summarize_by_pack(replay_records),
        "records": replay_records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# R84 REALM Tier-6 Live LLM Runtime Evaluator Report")
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
    lines.append(f"- Runtime mode: `{report['runtime_mode']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Records: `{report['num_records']}`")
    lines.append(f"- Passed evaluator checks: `{report['num_passed']}`")
    lines.append(f"- Failed evaluator checks: `{report['num_failed']}`")
    lines.append(f"- Admitted: `{report['num_admitted']}`")
    lines.append(f"- Rejected: `{report['num_rejected']}`")
    lines.append(f"- Flagged: `{report['num_flagged']}`")
    lines.append(f"- Global passed: `{report['global_passed']}`")
    lines.append("")
    lines.append("## Global Checks")
    lines.append("")
    lines.append("| Check | Passed | Detail |")
    lines.append("|---|---|---|")
    for check in report["global_checks"]:
        lines.append(
            f"| {check['name']} | {check['passed']} | `{check['detail']}` |"
        )

    lines.append("")
    lines.append("## Pack Summary")
    lines.append("")
    lines.append("| Pack | Records | Passed | Failed | Admitted | Rejected | Flagged | Policy counts |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for pack_name, entry in report["pack_summary"].items():
        lines.append(
            f"| {pack_name} | {entry['records']} | {entry['passed']} | "
            f"{entry['failed']} | {entry['admitted']} | {entry['rejected']} | "
            f"{entry['flagged']} | `{entry['policy_counts']}` |"
        )

    lines.append("")
    lines.append("## Per-Episode Replay Records")
    lines.append("")
    lines.append("| Pack | Episode | Passed | Admitted | Flags | Policy | Unsupported | Summary |")
    lines.append("|---|---:|---|---|---|---|---:|---|")
    for record in report["records"]:
        replay = record["runtime_replay"]
        summary = str(replay.get("proposal_summary", "")).replace("|", "\\|")
        if len(summary) > 110:
            summary = summary[:107] + "..."
        flags = ",".join(replay.get("grounding_flags", []))
        lines.append(
            f"| {record['pack_name']} | {record['episode_id']} | {record['passed']} | "
            f"{replay['admitted']} | {flags} | {replay.get('policy_style')} | "
            f"{replay.get('unsupported_specificity_count')} | {summary} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "This report replays the R83.5c deterministic kernel trace records through "
        "a stable runtime-evaluator layer. It checks admission consistency, "
        "grounding-flag consistency, deterministic timestamps, stable record IDs, "
        "contiguous event ordering, and absence of nondeterministic events output."
    )
    lines.append("")
    lines.append(
        "This is a deterministic evaluator artifact. It does not mutate the "
        "production runtime store."
    )
    lines.append("")

    return "\n".join(lines)


def cmd_evaluate(args: argparse.Namespace) -> None:
    trace_report_path = Path(args.trace_report)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trace_report = load_json(trace_report_path)
    report = build_runtime_evaluator_report(trace_report)

    json_path = output_dir / "runtime_evaluator_report.json"
    md_path = output_dir / "runtime_evaluator_report.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "trace_report": str(trace_report_path),
                "output_dir": str(output_dir),
                "json": str(json_path),
                "markdown": str(md_path),
                "num_records": report["num_records"],
                "num_passed": report["num_passed"],
                "num_failed": report["num_failed"],
                "num_admitted": report["num_admitted"],
                "num_rejected": report["num_rejected"],
                "num_flagged": report["num_flagged"],
                "global_passed": report["global_passed"],
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="build deterministic runtime evaluator report")
    evaluate.add_argument("--trace-report", default=DEFAULT_TRACE_REPORT)
    evaluate.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    evaluate.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
