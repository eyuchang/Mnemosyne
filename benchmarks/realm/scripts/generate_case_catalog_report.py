from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.realm.adapters.realm_case_loader import load_realm_bench_cases
from benchmarks.realm.adapters.thanksgiving_cases import (
    thanksgiving_dynamic_scenario,
    thanksgiving_static_scenario,
)

REALM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REALM_ROOT / "reports"


@dataclass(frozen=True)
class REALMCaseCatalogReportResult:
    output_dir: Path
    files: dict[str, Path]
    case_count: int
    dynamic_case_ids: list[str]
    thanksgiving_static_case_id: str
    thanksgiving_dynamic_case_id: str


def _case_summary(case: dict[str, Any]) -> dict[str, Any]:
    disruptions = case.get("disruptions", [])
    return {
        "case_id": case["case_id"],
        "name": case["name"],
        "short_name": case["short_name"],
        "family": case["family"],
        "tier": case["tier"],
        "mode": case["mode"],
        "extends": case.get("extends"),
        "objective": case.get("objective"),
        "metrics": case.get("metrics", []),
        "constraints": case.get("constraints", []),
        "requirements": case.get("requirements", []),
        "disruption_count": len(disruptions),
        "disruptions": disruptions,
    }


def _thanksgiving_summary() -> dict[str, Any]:
    static = thanksgiving_static_scenario()
    dynamic = thanksgiving_dynamic_scenario()

    assert dynamic.disruption is not None
    delay = dynamic.disruption

    return {
        "static": {
            "case_id": static.case_id,
            "short_name": static.short_name,
            "family_members": [member.name for member in static.family_members],
            "pickup_members": [member.name for member in static.pickup_members],
            "host_members": [member.name for member in static.host_members],
            "meal_tasks": [
                {
                    "task": task.task,
                    "duration_minutes": task.duration_minutes,
                    "requires_supervision": task.requires_supervision,
                }
                for task in static.meal_tasks
            ],
            "travel_times_minutes": static.travel_times_minutes,
            "dinner_deadline": static.dinner_deadline,
        },
        "dynamic": {
            "case_id": dynamic.case_id,
            "short_name": dynamic.short_name,
            "extends": "P6",
            "disruption": {
                "person": delay.person,
                "notice_time_est": delay.notice_time_est,
                "original_arrival_time": delay.original_arrival_time,
                "new_arrival_time": delay.new_arrival_time,
                "delay_minutes": delay.delay_minutes,
                "early_notice_minutes": delay.early_notice_minutes,
            },
        },
        "readiness_result": {
            "problem_extracted": True,
            "typed_adapter_loaded": True,
            "solution_available": False,
            "evaluation_available": False,
            "executable_solver_result": "not_run_in_r6.4",
            "next_step": "R6.5 executable Thanksgiving P6/P9 benchmark",
        },
    }


def build_report() -> dict[str, Any]:
    store = load_realm_bench_cases()
    summaries = [_case_summary(case) for case in store.cases]
    dynamic_case_ids = [
        case["case_id"]
        for case in summaries
        if case["disruption_count"] > 0
    ]

    return {
        "schema_version": "realm_case_catalog_report.v1",
        "case_count": len(summaries),
        "dynamic_case_ids": dynamic_case_ids,
        "cases": summaries,
        "thanksgiving": _thanksgiving_summary(),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# REALM-Bench Case Catalog Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case count: {report['case_count']}")
    lines.append(f"- Dynamic/disruption cases: {', '.join(report['dynamic_case_ids'])}")
    lines.append("- Result type: case catalog and readiness report")
    lines.append("- Executable solving result: not run in R6.4")
    lines.append("")

    lines.append("## Case Index")
    lines.append("")
    lines.append("| Case | Name | Family | Mode | Tier | Disruptions |")
    lines.append("|---|---|---|---:|---:|---:|")
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['name']} | {case['family']} | "
            f"{case['mode']} | {case['tier']} | {case['disruption_count']} |"
        )
    lines.append("")

    lines.append("## Dynamic Disruptions")
    lines.append("")
    for case in report["cases"]:
        if not case["disruptions"]:
            continue

        lines.append(f"### {case['case_id']} {case['name']}")
        lines.append("")
        for disruption in case["disruptions"]:
            lines.append(f"- Type: `{disruption.get('type')}`")
            for key, value in disruption.items():
                if key == "type":
                    continue
                lines.append(f"  - {key}: {value}")
        lines.append("")

    thanksgiving = report["thanksgiving"]
    static = thanksgiving["static"]
    dynamic = thanksgiving["dynamic"]
    delay = dynamic["disruption"]
    readiness = thanksgiving["readiness_result"]

    lines.append("## Thanksgiving Static Case: P6")
    lines.append("")
    lines.append(f"- Case: {static['case_id']} / {static['short_name']}")
    lines.append(f"- Family members: {', '.join(static['family_members'])}")
    lines.append(f"- Pickup members: {', '.join(static['pickup_members'])}")
    lines.append(f"- Host members: {', '.join(static['host_members'])}")
    lines.append(f"- Dinner deadline: {static['dinner_deadline']}")
    lines.append("")
    lines.append("Meal tasks:")
    for task in static["meal_tasks"]:
        lines.append(
            f"- {task['task']}: {task['duration_minutes']} minutes, "
            f"requires supervision: {task['requires_supervision']}"
        )
    lines.append("")
    lines.append("Travel times:")
    for route, minutes in static["travel_times_minutes"].items():
        lines.append(f"- {route}: {minutes} minutes")
    lines.append("")

    lines.append("## Thanksgiving Dynamic Case: P9")
    lines.append("")
    lines.append(f"- Case: {dynamic['case_id']} / {dynamic['short_name']}")
    lines.append(f"- Extends: {dynamic['extends']}")
    lines.append(f"- Person delayed: {delay['person']}")
    lines.append(f"- Notice time EST: {delay['notice_time_est']}")
    lines.append(f"- Original arrival: {delay['original_arrival_time']}")
    lines.append(f"- New arrival: {delay['new_arrival_time']}")
    lines.append(f"- Delay minutes: {delay['delay_minutes']}")
    lines.append(f"- Early notice window: {delay['early_notice_minutes']} minutes")
    lines.append("")
    lines.append("Expected benchmark behavior:")
    lines.append("- React at notice time, not at the original arrival time.")
    lines.append("- Preserve dinner deadline if feasible.")
    lines.append("- Preserve pickup and cooking-supervision constraints.")
    lines.append("")

    lines.append("## Current Result Status")
    lines.append("")
    lines.append(f"- Problem extracted: {readiness['problem_extracted']}")
    lines.append(f"- Typed adapter loaded: {readiness['typed_adapter_loaded']}")
    lines.append(f"- Solution available: {readiness['solution_available']}")
    lines.append(f"- Evaluation available: {readiness['evaluation_available']}")
    lines.append(f"- Executable solver result: {readiness['executable_solver_result']}")
    lines.append(f"- Next step: {readiness['next_step']}")
    lines.append("")

    return "\n".join(lines)


def run_report(output_dir: str | Path | None = None) -> REALMCaseCatalogReportResult:
    output_path = Path(output_dir) if output_dir is not None else DEFAULT_REPORT_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    report = build_report()

    files = {
        "json": output_path / "realm_case_catalog_report.json",
        "markdown": output_path / "realm_case_catalog_report.md",
    }

    files["json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    files["markdown"].write_text(
        render_markdown(report) + "\n",
        encoding="utf-8",
    )

    return REALMCaseCatalogReportResult(
        output_dir=output_path,
        files=files,
        case_count=report["case_count"],
        dynamic_case_ids=report["dynamic_case_ids"],
        thanksgiving_static_case_id="P6",
        thanksgiving_dynamic_case_id="P9",
    )


def main() -> None:
    result = run_report()
    print("R6.4 REALM-Bench case catalog report")
    print(f"output_dir: {result.output_dir}")
    print(f"case_count: {result.case_count}")
    print(f"dynamic_case_ids: {result.dynamic_case_ids}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
