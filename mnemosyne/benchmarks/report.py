# File: mnemosyne/benchmarks/report.py
#
# Purpose:
#   Human-readable Markdown report generator for REALM-style benchmark JSONL.
#
# Stage:
#   R0.1 — Benchmark report readiness.
#
# Contract:
#   Benchmark results remain evidence artifacts only.
#   They do not become domain truth.
#
# Usage:
#   python -m mnemosyne.benchmarks.report \
#     --input results/realm/p1_campus_tour_static_001.jsonl \
#     --output reports/realm/p1_campus_tour_report.md

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def load_jsonl(path: Path) -> list[JsonDict]:
    """Load one JSON object per non-empty line."""
    rows: list[JsonDict] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()

        if not line:
            continue

        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc

        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")

        rows.append(value)

    return rows


def _as_dict(value: Any) -> JsonDict:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _bool_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "unknown"
    return str(value)


def _display(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    if value == "":
        return default
    if isinstance(value, bool):
        return _bool_text(value)
    return str(value)


def _route_text(route: Any) -> str:
    if isinstance(route, list):
        return " -> ".join(str(item) for item in route)
    if isinstance(route, str):
        return route
    return "unknown"


def _markdown_escape(value: Any) -> str:
    text = _display(value)
    return text.replace("|", "\\|")


def _metrics(result: JsonDict) -> JsonDict:
    return _as_dict(result.get("metrics"))


def _details(result: JsonDict) -> JsonDict:
    return _as_dict(result.get("details"))


def _expected(result: JsonDict) -> JsonDict:
    return _as_dict(_details(result).get("expected"))


def _observed(result: JsonDict) -> JsonDict:
    return _as_dict(_details(result).get("observed"))


def _realm_bench(result: JsonDict) -> JsonDict:
    return _as_dict(_details(result).get("realm_bench"))


def _provenance(result: JsonDict) -> JsonDict:
    return _as_dict(_details(result).get("provenance"))


def _p1_trace(result: JsonDict) -> JsonDict:
    return _as_dict(_details(result).get("p1_trace"))


def _solver_certificate(result: JsonDict) -> JsonDict:
    value = result.get("solver_certificate")

    if isinstance(value, dict):
        return value

    details = _details(result)
    value = details.get("solver_certificate")

    if isinstance(value, dict):
        return value

    return {}


def _plan_proposal(result: JsonDict) -> JsonDict:
    value = result.get("plan_proposal")

    if isinstance(value, dict):
        return value

    details = _details(result)
    value = details.get("plan_proposal")

    if isinstance(value, dict):
        return value

    return {}


def _official_realm_bench(result: JsonDict) -> Any:
    details = _details(result)

    if "official_realm_bench" in details:
        return details["official_realm_bench"]

    if "official_realm_bench" in result:
        return result["official_realm_bench"]

    return None


def _committed(result: JsonDict) -> bool:
    observed = _observed(result)

    if "committed" in observed:
        return bool(observed["committed"])

    committed_rids = _as_list(result.get("committed_rids"))
    return len(committed_rids) > 0


def _is_expected_negative_rejection(result: JsonDict) -> bool:
    expected = _expected(result)

    return (
        bool(result.get("ok")) is True
        and expected.get("should_commit") is False
        and not _committed(result)
    )


def _case_type(result: JsonDict) -> str:
    expected = _expected(result)
    provenance = _provenance(result)
    realm = _realm_bench(result)

    source = str(provenance.get("source", "")).lower()
    stage = str(realm.get("stage", "")).lower()

    if expected.get("should_commit") is False:
        return "expected-negative feasibility rejection"

    if "solver" in source or "solver" in stage:
        return "solver-derived plan"

    if _p1_trace(result):
        return "oracle trace replay"

    return "benchmark case"


def summarize_results(results: list[JsonDict]) -> JsonDict:
    total = len(results)
    passed = sum(1 for result in results if bool(result.get("ok")) is True)
    failed = total - passed
    committed = sum(1 for result in results if _committed(result))
    expected_negative_rejections = sum(
        1 for result in results if _is_expected_negative_rejection(result)
    )

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "committed": committed,
        "expected_negative_rejections": expected_negative_rejections,
    }


def _render_summary_table(results: list[JsonDict]) -> list[str]:
    summary = summarize_results(results)

    return [
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total cases | {summary['total']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        f"| Committed cases | {summary['committed']} |",
        f"| Expected-negative rejections | {summary['expected_negative_rejections']} |",
        "",
    ]


def _render_case_index(results: list[JsonDict]) -> list[str]:
    lines = [
        "## Case index",
        "",
        "| Case | Verdict | Type | Committed |",
        "|---|---|---|---|",
    ]

    for result in results:
        verdict = "passed" if result.get("ok") else "failed"
        lines.append(
            "| "
            f"{_markdown_escape(result.get('case_id'))} | "
            f"{verdict} | "
            f"{_markdown_escape(_case_type(result))} | "
            f"{_bool_text(_committed(result))} |"
        )

    lines.append("")
    return lines


def _render_classification(result: JsonDict) -> list[str]:
    realm = _realm_bench(result)
    provenance = _provenance(result)

    lines = [
        "### Classification",
        "",
        f"- Benchmark family: `{_display(realm.get('benchmark_family'))}`",
        f"- Problem ID: `{_display(realm.get('problem_id'))}`",
        f"- Problem name: `{_display(realm.get('problem_name'))}`",
        f"- Official REALM-Bench fixture: `{_bool_text(_official_realm_bench(result))}`",
        f"- Case type: `{_case_type(result)}`",
    ]

    source = provenance.get("source")
    note = provenance.get("note")
    created_for_stage = provenance.get("created_for_stage")

    if source is not None:
        lines.append(f"- Provenance source: `{_display(source)}`")

    if created_for_stage is not None:
        lines.append(f"- Created for stage: `{_display(created_for_stage)}`")

    if note is not None:
        lines.extend(["", f"Provenance note: {_display(note)}"])

    lines.append("")
    return lines


def _render_expected(result: JsonDict) -> list[str]:
    expected = _expected(result)

    if not expected:
        return [
            "### Expected",
            "",
            "No expected outcome metadata was provided.",
            "",
        ]

    fields = [
        ("Feasible", "feasible"),
        ("Should commit", "should_commit"),
        ("Final state", "final_state"),
        ("Finish time", "finish_time"),
        ("Total minutes", "total_minutes"),
        ("Total records", "total_records"),
        ("Effective records", "effective_records"),
        ("Ineffective records", "ineffective_records"),
        ("Outbox rows", "outbox_rows"),
        ("State version", "state_version"),
    ]

    lines = [
        "### Expected",
        "",
    ]

    for label, key in fields:
        if key in expected:
            lines.append(f"- {label}: `{_display(expected.get(key))}`")

    if "route" in expected:
        lines.append(f"- Route: `{_route_text(expected.get('route'))}`")

    violation_prefixes = _as_list(expected.get("violation_prefixes"))

    if violation_prefixes:
        lines.append(f"- Expected violation prefixes: `{', '.join(str(item) for item in violation_prefixes)}`")

    lines.append("")
    return lines


def _render_observed(result: JsonDict) -> list[str]:
    observed = _observed(result)
    metrics = _metrics(result)

    lines = [
        "### Observed",
        "",
        f"- Case passed: `{_bool_text(result.get('ok'))}`",
        f"- Committed: `{_bool_text(_committed(result))}`",
    ]

    if "prevalidation_ok" in observed:
        lines.append(f"- Prevalidation ok: `{_display(observed.get('prevalidation_ok'))}`")

    committed_rids = _as_list(result.get("committed_rids"))

    if committed_rids:
        lines.append(f"- Committed record count: `{len(committed_rids)}`")

    if metrics:
        metric_fields = [
            ("Final state", "final_state"),
            ("Total records", "total_records"),
            ("Effective records", "effective_records"),
            ("Ineffective records", "ineffective_records"),
            ("Outbox rows", "outbox_rows"),
            ("State version", "state_version"),
        ]

        for label, key in metric_fields:
            if key in metrics:
                lines.append(f"- {label}: `{_display(metrics.get(key))}`")
    else:
        lines.append("- Metrics: `none`")

    lines.append("")
    return lines


def _render_p1_trace(result: JsonDict) -> list[str]:
    trace = _p1_trace(result)

    if not trace:
        return []

    lines = [
        "### P1 trace",
        "",
        f"- Feasible: `{_display(trace.get('feasible'))}`",
        f"- Route: `{_route_text(trace.get('route'))}`",
        f"- Finish time: `{_display(trace.get('finish_time'))}`",
        f"- Deadline: `{_display(trace.get('deadline'))}`",
        f"- Travel minutes: `{_display(trace.get('total_travel_minutes'))}`",
        f"- Visit minutes: `{_display(trace.get('total_visit_minutes'))}`",
        f"- Total minutes: `{_display(trace.get('total_minutes'))}`",
    ]

    violations = _as_list(trace.get("violations"))

    if violations:
        lines.extend(
            [
                "",
                "Violations:",
                "",
            ]
        )

        for violation in violations:
            lines.append(f"- `{_display(violation)}`")

    lines.append("")
    return lines


def _render_solver_certificate(result: JsonDict) -> list[str]:
    certificate = _solver_certificate(result)

    if not certificate:
        return []

    lines = [
        "### Solver certificate",
        "",
        f"- Solver ID: `{_display(certificate.get('solver_id'))}`",
        f"- Solver version: `{_display(certificate.get('solver_version'))}`",
        f"- Solver run ID: `{_display(certificate.get('solver_run_id'))}`",
        f"- Feasible: `{_display(certificate.get('feasible'))}`",
        f"- Optimality status: `{_display(certificate.get('optimality_status'))}`",
        f"- Objective: `{_display(certificate.get('objective_name'))}` = `{_display(certificate.get('objective_value'))}`",
    ]

    constraints = _as_list(certificate.get("constraints_summary"))

    if constraints:
        lines.extend(["", "Constraints summarized by solver:", ""])

        for constraint in constraints:
            lines.append(f"- `{_display(constraint)}`")

    violations = _as_list(certificate.get("violations"))

    if violations:
        lines.extend(["", "Solver-reported violations:", ""])

        for violation in violations:
            lines.append(f"- `{_display(violation)}`")

    metrics = _as_dict(certificate.get("metrics"))

    if metrics:
        lines.extend(["", "Solver metrics:", ""])

        for key in [
            "route",
            "finish_time",
            "deadline",
            "total_travel_minutes",
            "total_visit_minutes",
            "total_minutes",
        ]:
            if key in metrics:
                value = metrics[key]

                if key == "route":
                    value = _route_text(value)

                lines.append(f"- {key}: `{_display(value)}`")

    lines.append("")
    return lines


def _render_plan_proposal(result: JsonDict) -> list[str]:
    proposal = _plan_proposal(result)

    if not proposal:
        return []

    lines = [
        "### Plan proposal",
        "",
        f"- Proposal ID: `{_display(proposal.get('proposal_id'))}`",
        f"- App ID: `{_display(proposal.get('app_id'))}`",
        f"- Schema ID: `{_display(proposal.get('schema_id'))}`",
        f"- Route: `{_route_text(proposal.get('route'))}`",
        f"- Step count: `{len(_as_list(proposal.get('steps')))}`",
    ]

    attrs = _as_dict(proposal.get("attrs"))

    if attrs:
        lines.extend(["", "Proposal attributes:", ""])

        for key in [
            "start_time",
            "finish_time",
            "deadline",
            "total_travel_minutes",
            "total_visit_minutes",
            "total_minutes",
        ]:
            if key in attrs:
                lines.append(f"- {key}: `{_display(attrs.get(key))}`")

    lines.append("")
    return lines


def _render_errors(result: JsonDict) -> list[str]:
    error_codes = _as_list(result.get("error_codes"))
    error_message = result.get("error_message")

    if not error_codes and not error_message:
        return [
            "### Errors",
            "",
            "None.",
            "",
        ]

    lines = [
        "### Errors",
        "",
    ]

    if error_message:
        lines.append(f"- Message: `{_display(error_message)}`")

    if error_codes:
        lines.append("- Codes:")

        for code in error_codes:
            lines.append(f"  - `{_display(code)}`")

    lines.append("")
    return lines


def _render_interpretation(result: JsonDict) -> list[str]:
    ok = bool(result.get("ok"))
    expected = _expected(result)
    committed = _committed(result)
    trace = _p1_trace(result)

    if ok and expected.get("should_commit") is False and not committed:
        text = "The expected-negative case was correctly rejected before commit."
    elif ok and committed and trace.get("feasible") is True:
        text = "The feasible trace or solver-derived plan committed successfully through Mnemosyne."
    elif ok and committed:
        text = "The case committed successfully through Mnemosyne."
    elif not ok:
        text = "The case failed and should be inspected before being used as benchmark evidence."
    else:
        text = "The case completed without a committed state change."

    return [
        "### Interpretation",
        "",
        text,
        "",
    ]


def _render_case(result: JsonDict, index: int) -> list[str]:
    case_id = _display(result.get("case_id"), default=f"case-{index}")

    lines = [
        f"## Case {index} — `{case_id}`",
        "",
        "### Verdict",
        "",
        "Passed." if result.get("ok") else "Failed.",
        "",
    ]

    lines.extend(_render_classification(result))
    lines.extend(_render_expected(result))
    lines.extend(_render_observed(result))
    lines.extend(_render_p1_trace(result))
    lines.extend(_render_solver_certificate(result))
    lines.extend(_render_plan_proposal(result))
    lines.extend(_render_errors(result))
    lines.extend(_render_interpretation(result))

    return lines


def build_markdown_report(
    *,
    results: list[JsonDict],
    title: str = "REALM Local Benchmark Report",
) -> str:
    lines: list[str] = [
        f"# {title}",
        "",
        "This report summarizes local REALM-style benchmark runs.",
        "",
        "Unless explicitly stated otherwise, these are local benchmark artifacts, not official REALM-Bench scores.",
        "",
    ]

    lines.extend(_render_summary_table(results))
    lines.extend(_render_case_index(results))

    for index, result in enumerate(results, start=1):
        lines.extend(_render_case(result, index))

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(
    *,
    input_path: Path,
    output_path: Path,
    title: str,
) -> None:
    results = load_jsonl(input_path)
    report = build_markdown_report(
        results=results,
        title=title,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a human-readable Markdown report from REALM benchmark JSONL."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input JSONL benchmark results file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--title",
        default="REALM Local Benchmark Report",
        help="Markdown report title.",
    )

    args = parser.parse_args(argv)

    write_markdown_report(
        input_path=args.input,
        output_path=args.output,
        title=args.title,
    )

    print(f"Report written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())