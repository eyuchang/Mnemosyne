# File: mnemosyne/benchmarks/audit_report.py
#
# Stage:
#   R2.4 — failure / rejection report rendering.
#
# Purpose:
#   Render benchmark JSONL rows into a human-readable audit report that
#   explains not only successful commits, but also why unsafe proposals were
#   rejected before commit.
#
# Design rule:
#   Rejection is evidence, not a missing result.
#
#   A failed row can be a successful safety outcome if the system rejected
#   an unsafe proposal before commit.

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def load_jsonl(path: Path) -> list[JsonDict]:
    rows: list[JsonDict] = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def _fmt_value(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, (int, float)):
        return f"`{value}`"
    if isinstance(value, str):
        return f"`{value}`"
    return f"`{json.dumps(value, sort_keys=True)}`"


def _error_codes(row: JsonDict) -> list[str]:
    codes = row.get("error_codes", [])
    if isinstance(codes, list):
        return [str(code) for code in codes]
    if codes:
        return [str(codes)]
    return []


def classify_row(row: JsonDict) -> str:
    if row.get("ok") is True:
        return "committed_or_expected_success"

    codes = set(_error_codes(row))

    if "SOLVER_FAILED" in codes:
        return "solver_failure"

    if "SOLVER_PROPOSAL_CONFLICT" in codes:
        return "proposal_conflict_rejection"

    if "STALE_WORLD_RECONCILIATION" in codes:
        return "stale_world_rejection"

    if "P1_TRACE_INFEASIBLE" in codes:
        return "expected_negative_or_trace_rejection"

    if codes:
        return "validation_or_runtime_rejection"

    return "unknown_failure"


def summarize_rows(rows: list[JsonDict]) -> JsonDict:
    summary: JsonDict = {
        "total": len(rows),
        "ok": 0,
        "failed": 0,
        "committed": 0,
        "rejected_before_commit": 0,
        "by_classification": {},
        "by_error_code": {},
    }

    for row in rows:
        ok = row.get("ok") is True
        if ok:
            summary["ok"] += 1
        else:
            summary["failed"] += 1

        committed_rids = row.get("committed_rids", [])
        committed = bool(committed_rids)

        if committed:
            summary["committed"] += 1
        else:
            details = row.get("details", {})
            observed = details.get("observed", {}) if isinstance(details, dict) else {}
            if row.get("ok") is False or observed.get("committed") is False:
                summary["rejected_before_commit"] += 1

        classification = classify_row(row)
        summary["by_classification"][classification] = (
            summary["by_classification"].get(classification, 0) + 1
        )

        for code in _error_codes(row):
            summary["by_error_code"][code] = (
                summary["by_error_code"].get(code, 0) + 1
            )

    return summary


def _render_solver_certificate(details: JsonDict) -> list[str]:
    cert = details.get("solver_certificate")

    if not isinstance(cert, dict) or not cert:
        return []

    lines = [
        "### Solver certificate",
        "",
    ]

    for key in [
        "solver_id",
        "solver_version",
        "solver_run_id",
        "problem_family",
        "problem_id",
        "feasible",
        "optimality_status",
        "objective_name",
        "objective_value",
    ]:
        if key in cert:
            lines.append(f"- {key}: {_fmt_value(cert.get(key))}")

    metrics = cert.get("metrics")
    if isinstance(metrics, dict) and metrics:
        lines.extend(["", "Solver metrics:", ""])
        for key, value in sorted(metrics.items()):
            lines.append(f"- {key}: {_fmt_value(value)}")

    violations = cert.get("violations")
    if isinstance(violations, list) and violations:
        lines.extend(["", "Solver violations:", ""])
        for violation in violations:
            lines.append(f"- {_fmt_value(violation)}")

    lines.append("")
    return lines


def _render_plan_proposal(details: JsonDict) -> list[str]:
    proposal = details.get("plan_proposal")

    if not isinstance(proposal, dict) or not proposal:
        return []

    lines = [
        "### Plan proposal",
        "",
    ]

    for key in [
        "proposal_id",
        "case_id",
        "tenant_id",
        "workflow_id",
        "entity_id",
        "app_id",
        "schema_id",
    ]:
        if key in proposal:
            lines.append(f"- {key}: {_fmt_value(proposal.get(key))}")

    route = proposal.get("route")
    if isinstance(route, list) and route:
        lines.append(f"- route: `{' -> '.join(str(x) for x in route)}`")

    steps = proposal.get("steps")
    if isinstance(steps, list):
        lines.append(f"- step_count: `{len(steps)}`")

    attrs = proposal.get("attrs")
    if isinstance(attrs, dict) and attrs:
        lines.extend(["", "Proposal attributes:", ""])
        for key, value in sorted(attrs.items()):
            if key == "world_assumptions":
                continue
            lines.append(f"- {key}: {_fmt_value(value)}")

        world_assumptions = attrs.get("world_assumptions")
        if isinstance(world_assumptions, list) and world_assumptions:
            lines.extend(["", "World assumptions:", ""])
            for assumption in world_assumptions:
                lines.append(f"- {_fmt_value(assumption)}")

    lines.append("")
    return lines


def _render_proposal_conflicts(details: JsonDict) -> list[str]:
    report = details.get("proposal_conflicts")

    if not isinstance(report, dict) or not report:
        return []

    lines = [
        "### Proposal conflict analysis",
        "",
        f"- conflict_free: {_fmt_value(report.get('ok'))}",
    ]

    conflicts = report.get("conflicts", [])
    if isinstance(conflicts, list) and conflicts:
        lines.extend(["", "Conflicts:", ""])
        for conflict in conflicts:
            if isinstance(conflict, dict):
                ctype = conflict.get("conflict_type")
                scope = conflict.get("scope")
                left = conflict.get("left_proposal_id")
                right = conflict.get("right_proposal_id")
                msg = conflict.get("message")
                lines.append(
                    f"- {ctype}: scope={_fmt_value(scope)}, "
                    f"left={_fmt_value(left)}, right={_fmt_value(right)}, "
                    f"message={_fmt_value(msg)}"
                )
            else:
                lines.append(f"- {_fmt_value(conflict)}")

    lines.append("")
    return lines


def _render_world_reconciliation(details: JsonDict) -> list[str]:
    report = details.get("world_reconciliation")

    if not isinstance(report, dict) or not report:
        return []

    lines = [
        "### World reconciliation",
        "",
        f"- world_reconciled: {_fmt_value(report.get('ok'))}",
    ]

    issues = report.get("issues", [])
    if isinstance(issues, list) and issues:
        lines.extend(["", "Issues:", ""])
        for issue in issues:
            if isinstance(issue, dict):
                itype = issue.get("issue_type")
                entity = issue.get("entity_id")
                key = issue.get("key")
                expected = issue.get("expected_value")
                observed = issue.get("observed_value")
                msg = issue.get("message")
                lines.append(
                    f"- {itype}: entity={_fmt_value(entity)}, "
                    f"key={_fmt_value(key)}, expected={_fmt_value(expected)}, "
                    f"observed={_fmt_value(observed)}, message={_fmt_value(msg)}"
                )
            else:
                lines.append(f"- {_fmt_value(issue)}")

    lines.append("")
    return lines


def _render_observed(details: JsonDict) -> list[str]:
    observed = details.get("observed")

    if not isinstance(observed, dict) or not observed:
        return []

    lines = [
        "### Observed outcome",
        "",
    ]

    for key, value in sorted(observed.items()):
        lines.append(f"- {key}: {_fmt_value(value)}")

    lines.append("")
    return lines


def render_case(row: JsonDict, *, index: int) -> str:
    case_id = row.get("case_id", f"case-{index}")
    classification = classify_row(row)
    details = row.get("details", {})
    if not isinstance(details, dict):
        details = {}

    lines = [
        f"## Case {index}: `{case_id}`",
        "",
        f"- classification: `{classification}`",
        f"- ok: {_fmt_value(row.get('ok'))}",
        f"- committed_rids: {_fmt_value(row.get('committed_rids', []))}",
    ]

    codes = _error_codes(row)
    if codes:
        lines.append(f"- error_codes: `{', '.join(codes)}`")

    if row.get("error_message"):
        lines.append(f"- error_message: {_fmt_value(row.get('error_message'))}")

    if row.get("source_case_path"):
        lines.append(f"- source_case_path: {_fmt_value(row.get('source_case_path'))}")

    lines.append("")

    lines.extend(_render_observed(details))
    lines.extend(_render_solver_certificate(details))
    lines.extend(_render_plan_proposal(details))
    lines.extend(_render_proposal_conflicts(details))
    lines.extend(_render_world_reconciliation(details))

    if classification == "proposal_conflict_rejection":
        lines.extend(
            [
                "### Interpretation",
                "",
                "This proposal set was rejected before commit because active proposals conflicted.",
                "No committed records should appear for this case.",
                "",
            ]
        )
    elif classification == "stale_world_rejection":
        lines.extend(
            [
                "### Interpretation",
                "",
                "This proposal was rejected before commit because its world assumptions disagreed with observed facts.",
                "No committed records should appear for this case.",
                "",
            ]
        )
    elif row.get("ok") is False:
        lines.extend(
            [
                "### Interpretation",
                "",
                "This row represents a failed or rejected run. Inspect the error codes and details above.",
                "",
            ]
        )

    return "\n".join(lines)


def build_markdown_report(
    *,
    rows: list[JsonDict],
    title: str,
) -> str:
    summary = summarize_rows(rows)

    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- total rows: `{summary['total']}`",
        f"- ok rows: `{summary['ok']}`",
        f"- failed rows: `{summary['failed']}`",
        f"- rows with committed records: `{summary['committed']}`",
        f"- rejected before commit: `{summary['rejected_before_commit']}`",
        "",
        "### By classification",
        "",
    ]

    for key, value in sorted(summary["by_classification"].items()):
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "### By error code", ""])

    if summary["by_error_code"]:
        for key, value in sorted(summary["by_error_code"].items()):
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none")

    lines.append("")

    for index, row in enumerate(rows, start=1):
        lines.append(render_case(row, index=index))

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(
    *,
    rows: list[JsonDict],
    output_path: Path,
    title: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_markdown_report(
            rows=rows,
            title=title,
        ),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m mnemosyne.benchmarks.audit_report",
        description="Render benchmark JSONL rows as a human-readable audit report.",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--title",
        default="Mnemosyne Benchmark Audit Report",
        help="Report title.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rows = load_jsonl(Path(args.input))
    write_markdown_report(
        rows=rows,
        output_path=Path(args.output),
        title=args.title,
    )

    print(f"Audit report written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
