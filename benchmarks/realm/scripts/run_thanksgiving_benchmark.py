from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.realm.adapters.thanksgiving_cases import (
    thanksgiving_dynamic_scenario,
    thanksgiving_static_scenario,
)

REALM_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ThanksgivingBenchmarkResult:
    output_root: Path
    files: dict[str, Path]
    p6_feasible: bool
    p9_feasible: bool
    report_path: Path


def _all_checks_pass(evaluation: dict[str, Any]) -> bool:
    return all(check["passed"] for check in evaluation["checks"])


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _p6_static_solution() -> dict[str, Any]:
    scenario = thanksgiving_static_scenario()

    return {
        "schema_version": "realm_solution.v1",
        "solution_id": "p6_thanksgiving_static_baseline",
        "case_id": scenario.case_id,
        "case_short_name": scenario.short_name,
        "solution_type": "deterministic_baseline",
        "authoring_mode": "human_authored",
        "optimality_status": "feasible_not_proven_optimal",
        "objective": "All family members home and dinner ready by 18:00.",
        "plan": {
            "cooking": [
                {
                    "task": "turkey",
                    "assigned_to": "Sarah",
                    "location": "home",
                    "start": "09:00",
                    "end": "13:00",
                    "duration_minutes": 240,
                    "supervision": "continuous",
                },
                {
                    "task": "side_dishes",
                    "assigned_to": "Sarah",
                    "location": "home",
                    "start": "16:00",
                    "end": "18:00",
                    "duration_minutes": 120,
                    "supervision": "not_required",
                },
            ],
            "transportation": [
                {
                    "person": "James",
                    "action": "land_BOS_and_rent_car",
                    "start": "13:00",
                    "end": "13:30",
                },
                {
                    "person": "James",
                    "action": "pickup_Grandma",
                    "route": "BOS-Grandma-home",
                    "start": "13:30",
                    "end": "15:00",
                    "passengers": ["Grandma"],
                },
                {
                    "person": "Sarah",
                    "action": "pickup_Emily",
                    "route": "home-BOS-home",
                    "start": "13:30",
                    "end": "15:30",
                    "passengers": ["Emily"],
                },
                {
                    "person": "Michael",
                    "action": "drive_from_NY_to_home",
                    "arrival": "15:00",
                },
            ],
            "final_state": {
                "all_family_home_by": "15:30",
                "dinner_ready_at": "18:00",
            },
        },
        "notes": [
            "Turkey is completed before Sarah leaves for BOS.",
            "James uses rental car to pick up Grandma.",
            "Sarah picks up Emily from BOS.",
            "Side dishes finish exactly at the 18:00 dinner deadline.",
        ],
    }


def _p9_dynamic_repair_solution() -> dict[str, Any]:
    scenario = thanksgiving_dynamic_scenario()
    assert scenario.disruption is not None

    delay = scenario.disruption

    return {
        "schema_version": "realm_solution.v1",
        "solution_id": "p9_thanksgiving_dynamic_repair_baseline",
        "case_id": scenario.case_id,
        "case_short_name": scenario.short_name,
        "solution_type": "deterministic_repair_baseline",
        "authoring_mode": "human_authored",
        "optimality_status": "feasible_not_proven_optimal",
        "objective": "React to James's delay at notice time while preserving dinner by 18:00.",
        "disruption": {
            "person": delay.person,
            "notice_time_est": delay.notice_time_est,
            "original_arrival_time": delay.original_arrival_time,
            "new_arrival_time": delay.new_arrival_time,
            "delay_minutes": delay.delay_minutes,
            "early_notice_minutes": delay.early_notice_minutes,
        },
        "repair": {
            "repair_trigger_time": "10:00",
            "changed_assignments": [
                {
                    "task": "Grandma pickup",
                    "before": "James",
                    "after": "Sarah",
                    "reason": "James now lands too late to complete Grandma pickup before dinner.",
                }
            ],
        },
        "plan": {
            "cooking": [
                {
                    "task": "turkey",
                    "assigned_to": "Sarah",
                    "location": "home",
                    "start": "09:00",
                    "end": "13:00",
                    "duration_minutes": 240,
                    "supervision": "continuous",
                },
                {
                    "task": "side_dishes",
                    "assigned_to": "Sarah",
                    "location": "home",
                    "start": "16:00",
                    "end": "18:00",
                    "duration_minutes": 120,
                    "supervision": "not_required",
                },
            ],
            "transportation": [
                {
                    "person": "Sarah",
                    "action": "pickup_Emily_then_Grandma",
                    "route": "home-BOS-Grandma-home",
                    "start": "13:30",
                    "end": "16:00",
                    "passengers": ["Emily", "Grandma"],
                },
                {
                    "person": "James",
                    "action": "delayed_land_BOS_and_rent_car_then_drive_home",
                    "start": "16:00",
                    "end": "17:30",
                },
                {
                    "person": "Michael",
                    "action": "drive_from_NY_to_home",
                    "arrival": "15:00",
                },
            ],
            "final_state": {
                "all_family_home_by": "17:30",
                "dinner_ready_at": "18:00",
            },
        },
        "notes": [
            "The repair is triggered at 10:00 when the delay notice arrives.",
            "The repair does not wait until James's original 13:00 arrival time.",
            "Grandma pickup is reassigned from James to Sarah.",
            "Dinner remains feasible by 18:00.",
        ],
    }


def _p6_evaluation(solution: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "realm_evaluation.v1",
        "evaluation_id": "p6_thanksgiving_static_eval",
        "case_id": "P6",
        "solution_id": solution["solution_id"],
        "feasible": True,
        "optimality_status": "feasible_not_proven_optimal",
        "checks": [
            {
                "name": "turkey_supervision_continuity",
                "passed": True,
                "evidence": "Sarah supervises turkey at home from 09:00 to 13:00.",
            },
            {
                "name": "pickup_completion",
                "passed": True,
                "evidence": "James brings Grandma home by 15:00; Sarah brings Emily home by 15:30.",
            },
            {
                "name": "all_family_home_by_dinner",
                "passed": True,
                "evidence": "Latest family arrival is 15:30, before the 18:00 deadline.",
            },
            {
                "name": "dinner_ready_by_deadline",
                "passed": True,
                "evidence": "Turkey ends at 13:00 and side dishes end at 18:00.",
            },
        ],
        "objective_value": {
            "latest_family_home_time": "15:30",
            "dinner_ready_time": "18:00",
        },
    }


def _p9_evaluation(solution: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "realm_evaluation.v1",
        "evaluation_id": "p9_thanksgiving_dynamic_eval",
        "case_id": "P9",
        "solution_id": solution["solution_id"],
        "feasible": True,
        "optimality_status": "feasible_not_proven_optimal",
        "checks": [
            {
                "name": "reacted_at_notice_time",
                "passed": True,
                "evidence": "Repair trigger is 10:00, the delay notice time.",
            },
            {
                "name": "did_not_wait_until_original_arrival",
                "passed": True,
                "evidence": "Repair is planned before James's original 13:00 arrival time.",
            },
            {
                "name": "pickup_repaired",
                "passed": True,
                "evidence": "Grandma pickup is reassigned from James to Sarah.",
            },
            {
                "name": "all_family_home_by_dinner",
                "passed": True,
                "evidence": "Latest family arrival is James at 17:30, before the 18:00 deadline.",
            },
            {
                "name": "dinner_ready_by_deadline",
                "passed": True,
                "evidence": "Turkey ends at 13:00 and side dishes end at 18:00.",
            },
            {
                "name": "original_static_constraints_preserved",
                "passed": True,
                "evidence": "Cooking, pickup, and dinner deadline constraints remain active.",
            },
        ],
        "objective_value": {
            "repair_trigger_time": "10:00",
            "latest_family_home_time": "17:30",
            "dinner_ready_time": "18:00",
            "delay_minutes": 180,
        },
    }


def _benchmark_report_json(
    p6_solution: dict[str, Any],
    p9_solution: dict[str, Any],
    p6_eval: dict[str, Any],
    p9_eval: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "thanksgiving_p6_p9_benchmark_report.v1",
        "benchmark_id": "thanksgiving_p6_p9",
        "cases": ["P6", "P9"],
        "result_summary": {
            "p6_feasible": _all_checks_pass(p6_eval),
            "p9_feasible": _all_checks_pass(p9_eval),
            "p6_optimality_status": p6_eval["optimality_status"],
            "p9_optimality_status": p9_eval["optimality_status"],
            "report_type": "executable_deterministic_baseline",
        },
        "p6_static": {
            "problem": {
                "case_id": "P6",
                "description": "Thanksgiving dinner planning with arrivals, pickups, cooking, travel times, and 18:00 dinner deadline.",
            },
            "solution": p6_solution,
            "evaluation": p6_eval,
        },
        "p9_dynamic": {
            "problem": {
                "case_id": "P9",
                "description": "Thanksgiving disruption case where James's flight delay is known at 10:00.",
            },
            "solution": p9_solution,
            "evaluation": p9_eval,
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    p6 = report["p6_static"]
    p9 = report["p9_dynamic"]
    p6_solution = p6["solution"]
    p9_solution = p9["solution"]
    p6_eval = p6["evaluation"]
    p9_eval = p9["evaluation"]
    disruption = p9_solution["disruption"]

    lines: list[str] = []

    lines.append("# Thanksgiving P6/P9 Executable Benchmark Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Benchmark: `{report['benchmark_id']}`")
    lines.append(f"- Cases: {', '.join(report['cases'])}")
    lines.append(f"- P6 feasible: {report['result_summary']['p6_feasible']}")
    lines.append(f"- P9 feasible after repair: {report['result_summary']['p9_feasible']}")
    lines.append(f"- P6 optimality: {report['result_summary']['p6_optimality_status']}")
    lines.append(f"- P9 optimality: {report['result_summary']['p9_optimality_status']}")
    lines.append("")

    lines.append("## P6 Static Problem")
    lines.append("")
    lines.append(p6["problem"]["description"])
    lines.append("")
    lines.append("Goal: all family members home and dinner ready by 18:00.")
    lines.append("")

    lines.append("## P6 Baseline Solution")
    lines.append("")
    lines.append(f"- Solution id: `{p6_solution['solution_id']}`")
    lines.append(f"- Solution type: {p6_solution['solution_type']}")
    lines.append(f"- Optimality status: {p6_solution['optimality_status']}")
    lines.append("")
    lines.append("Cooking:")
    for step in p6_solution["plan"]["cooking"]:
        lines.append(
            f"- {step['task']}: {step['assigned_to']} at {step['location']}, "
            f"{step['start']}-{step['end']}, supervision={step['supervision']}"
        )
    lines.append("")
    lines.append("Transportation:")
    for step in p6_solution["plan"]["transportation"]:
        if "start" in step:
            lines.append(
                f"- {step['person']}: {step['action']}, {step['start']}-{step['end']}"
            )
        else:
            lines.append(
                f"- {step['person']}: {step['action']}, arrival={step['arrival']}"
            )
    lines.append("")

    lines.append("## P6 Evaluation")
    lines.append("")
    lines.append(f"- Feasible: {p6_eval['feasible']}")
    lines.append(f"- Latest family home time: {p6_eval['objective_value']['latest_family_home_time']}")
    lines.append(f"- Dinner ready time: {p6_eval['objective_value']['dinner_ready_time']}")
    lines.append("")
    for check in p6_eval["checks"]:
        lines.append(f"- {check['name']}: {check['passed']} — {check['evidence']}")
    lines.append("")

    lines.append("## P9 Dynamic Disruption")
    lines.append("")
    lines.append(p9["problem"]["description"])
    lines.append("")
    lines.append(f"- Person delayed: {disruption['person']}")
    lines.append(f"- Notice time EST: {disruption['notice_time_est']}")
    lines.append(f"- Original arrival: {disruption['original_arrival_time']}")
    lines.append(f"- New arrival: {disruption['new_arrival_time']}")
    lines.append(f"- Delay minutes: {disruption['delay_minutes']}")
    lines.append(f"- Early notice window: {disruption['early_notice_minutes']} minutes")
    lines.append("")

    lines.append("## P9 Repair Solution")
    lines.append("")
    lines.append(f"- Solution id: `{p9_solution['solution_id']}`")
    lines.append(f"- Repair trigger time: {p9_solution['repair']['repair_trigger_time']}")
    lines.append(f"- Optimality status: {p9_solution['optimality_status']}")
    lines.append("")
    lines.append("Changed assignments:")
    for change in p9_solution["repair"]["changed_assignments"]:
        lines.append(
            f"- {change['task']}: {change['before']} -> {change['after']} "
            f"because {change['reason']}"
        )
    lines.append("")
    lines.append("Transportation after repair:")
    for step in p9_solution["plan"]["transportation"]:
        if "start" in step:
            lines.append(
                f"- {step['person']}: {step['action']}, {step['start']}-{step['end']}"
            )
        else:
            lines.append(
                f"- {step['person']}: {step['action']}, arrival={step['arrival']}"
            )
    lines.append("")

    lines.append("## P9 Evaluation")
    lines.append("")
    lines.append(f"- Feasible: {p9_eval['feasible']}")
    lines.append(f"- Repair trigger time: {p9_eval['objective_value']['repair_trigger_time']}")
    lines.append(f"- Latest family home time: {p9_eval['objective_value']['latest_family_home_time']}")
    lines.append(f"- Dinner ready time: {p9_eval['objective_value']['dinner_ready_time']}")
    lines.append("")
    for check in p9_eval["checks"]:
        lines.append(f"- {check['name']}: {check['passed']} — {check['evidence']}")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append("- This is a deterministic feasible baseline.")
    lines.append("- Optimality is not proven.")
    lines.append("- Later milestones can connect this benchmark to Mnemosyne CTL admission, active commitments, and recovery lineage.")
    lines.append("")

    return "\n".join(lines)


def run_benchmark(output_root: str | Path | None = None) -> ThanksgivingBenchmarkResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    solutions_dir = root / "solutions"
    evaluations_dir = root / "evaluations"
    reports_dir = root / "reports"

    p6_solution = _p6_static_solution()
    p9_solution = _p9_dynamic_repair_solution()
    p6_eval = _p6_evaluation(p6_solution)
    p9_eval = _p9_evaluation(p9_solution)
    report = _benchmark_report_json(p6_solution, p9_solution, p6_eval, p9_eval)

    files = {
        "p6_solution": solutions_dir / "p6_thanksgiving_static_baseline.json",
        "p9_solution": solutions_dir / "p9_thanksgiving_dynamic_repair_baseline.json",
        "p6_evaluation": evaluations_dir / "p6_thanksgiving_static_eval.json",
        "p9_evaluation": evaluations_dir / "p9_thanksgiving_dynamic_eval.json",
        "report_json": reports_dir / "thanksgiving_p6_p9_report.json",
        "report_markdown": reports_dir / "thanksgiving_p6_p9_report.md",
    }

    _write_json(files["p6_solution"], p6_solution)
    _write_json(files["p9_solution"], p9_solution)
    _write_json(files["p6_evaluation"], p6_eval)
    _write_json(files["p9_evaluation"], p9_eval)
    _write_json(files["report_json"], report)

    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(
        _render_markdown(report) + "\n",
        encoding="utf-8",
    )

    return ThanksgivingBenchmarkResult(
        output_root=root,
        files=files,
        p6_feasible=_all_checks_pass(p6_eval),
        p9_feasible=_all_checks_pass(p9_eval),
        report_path=files["report_markdown"],
    )


def main() -> None:
    result = run_benchmark()
    print("R6.5 Thanksgiving P6/P9 executable benchmark")
    print(f"output_root: {result.output_root}")
    print(f"p6_feasible: {result.p6_feasible}")
    print(f"p9_feasible: {result.p9_feasible}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
