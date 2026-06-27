from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = REALM_ROOT / "cases" / "j2_jssp_simple_dynamic.json"


@dataclass(frozen=True)
class J2RecoveryBaselineResult:
    output_root: Path
    files: dict[str, Path]
    affected_operation_count: int
    feasible_after_repair: bool
    initial_makespan: int
    repaired_makespan: int


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_case() -> dict[str, Any]:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def _operation_id(job_id: str, operation_index: int) -> str:
    return f"{job_id}:O{operation_index}"


def _machine_breakdown(case: dict[str, Any]) -> dict[str, Any]:
    for disruption in case.get("disruptions", []):
        if disruption.get("type") == "machine_breakdown_example":
            return disruption
    raise ValueError("J2 machine_breakdown_example not found")


def _interval_overlaps(start: int, end: int, block_start: int, block_end: int) -> bool:
    return start < block_end and end > block_start


def _earliest_machine_start(
    *,
    earliest: int,
    duration: int,
    blocked: dict[str, tuple[int, int]] | None,
    machine: str,
) -> int:
    if blocked is None or machine not in blocked:
        return earliest

    block_start, block_end = blocked[machine]
    if _interval_overlaps(earliest, earliest + duration, block_start, block_end):
        return block_end
    return earliest


def _build_greedy_schedule(
    case: dict[str, Any],
    *,
    blocked: dict[str, tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    jobs = case["entities"]["jobs"]

    job_available: dict[str, int] = {job["job_id"]: 0 for job in jobs}
    machine_available: dict[str, int] = {
        machine: 0 for machine in case["entities"]["machines"]
    }
    scheduled: list[dict[str, Any]] = []

    max_ops = max(len(job["operations"]) for job in jobs)

    for operation_index in range(max_ops):
        for job in jobs:
            job_id = job["job_id"]
            operations = job["operations"]
            if operation_index >= len(operations):
                continue

            operation = operations[operation_index]
            machine = operation["machine"]
            duration = int(operation["duration"])

            start = max(job_available[job_id], machine_available[machine])
            start = _earliest_machine_start(
                earliest=start,
                duration=duration,
                blocked=blocked,
                machine=machine,
            )
            end = start + duration

            scheduled_operation = {
                "operation_id": _operation_id(job_id, operation_index + 1),
                "job_id": job_id,
                "operation_index": operation_index + 1,
                "machine": machine,
                "duration": duration,
                "start": start,
                "end": end,
            }
            scheduled.append(scheduled_operation)

            job_available[job_id] = end
            machine_available[machine] = end

    return scheduled


def _makespan(schedule: list[dict[str, Any]]) -> int:
    return max(operation["end"] for operation in schedule)


def _affected_operations(
    schedule: list[dict[str, Any]],
    *,
    machine: str,
    unavailable_start: int,
    unavailable_end: int,
) -> list[dict[str, Any]]:
    return [
        operation
        for operation in schedule
        if operation["machine"] == machine
        and _interval_overlaps(
            operation["start"],
            operation["end"],
            unavailable_start,
            unavailable_end,
        )
    ]


def _check_precedence(schedule: list[dict[str, Any]]) -> bool:
    by_job: dict[str, list[dict[str, Any]]] = {}
    for operation in schedule:
        by_job.setdefault(operation["job_id"], []).append(operation)

    for operations in by_job.values():
        ordered = sorted(operations, key=lambda item: item["operation_index"])
        for left, right in zip(ordered, ordered[1:]):
            if left["end"] > right["start"]:
                return False
    return True


def _check_machine_capacity(schedule: list[dict[str, Any]]) -> bool:
    by_machine: dict[str, list[dict[str, Any]]] = {}
    for operation in schedule:
        by_machine.setdefault(operation["machine"], []).append(operation)

    for operations in by_machine.values():
        ordered = sorted(operations, key=lambda item: (item["start"], item["end"]))
        for left, right in zip(ordered, ordered[1:]):
            if left["end"] > right["start"]:
                return False
    return True


def _check_machine_downtime(
    schedule: list[dict[str, Any]],
    *,
    machine: str,
    unavailable_start: int,
    unavailable_end: int,
) -> bool:
    return not _affected_operations(
        schedule,
        machine=machine,
        unavailable_start=unavailable_start,
        unavailable_end=unavailable_end,
    )


def _render_markdown(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    evaluation = report["evaluation"]
    disruption = report["disruption"]

    lines: list[str] = []

    lines.append("# REALM J2 JSSP Machine-Breakdown Recovery Baseline")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case: {report['case_id']}")
    lines.append(f"- Machine unavailable: `{disruption['machine']}`")
    lines.append(f"- Unavailable window: {disruption['unavailable_start']} to {disruption['unavailable_end']}")
    lines.append(f"- Initial makespan: {baseline['initial_makespan']}")
    lines.append(f"- Repaired makespan: {baseline['repaired_makespan']}")
    lines.append(f"- Affected operations: {len(baseline['affected_operations'])}")
    lines.append(f"- Feasible after repair: {evaluation['feasible_after_repair']}")
    lines.append(f"- Optimality status: {evaluation['optimality_status']}")
    lines.append("")

    lines.append("## Affected Operations")
    lines.append("")
    for operation in baseline["affected_operations"]:
        lines.append(
            f"- `{operation['operation_id']}` on `{operation['machine']}`: "
            f"{operation['start']} to {operation['end']}"
        )
    lines.append("")

    lines.append("## Constraint Checks")
    lines.append("")
    for key, value in evaluation["constraint_checks"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Repaired Schedule")
    lines.append("")
    lines.append("| Operation | Machine | Start | End |")
    lines.append("|---|---|---:|---:|")
    for operation in baseline["repaired_schedule"]:
        lines.append(
            f"| `{operation['operation_id']}` | `{operation['machine']}` | "
            f"{operation['start']} | {operation['end']} |"
        )
    lines.append("")

    lines.append("## Claims")
    lines.append("")
    for key, value in report["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    return "\n".join(lines)


def run_j2_recovery_baseline(
    output_root: str | Path | None = None,
) -> J2RecoveryBaselineResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    case = _load_case()
    disruption = _machine_breakdown(case)
    machine = disruption["machine"]
    unavailable_start = int(disruption["unavailable_start"])
    unavailable_end = int(disruption["unavailable_end"])

    initial_schedule = _build_greedy_schedule(case)
    affected = _affected_operations(
        initial_schedule,
        machine=machine,
        unavailable_start=unavailable_start,
        unavailable_end=unavailable_end,
    )

    repaired_schedule = _build_greedy_schedule(
        case,
        blocked={machine: (unavailable_start, unavailable_end)},
    )

    checks = {
        "precedence_satisfaction": _check_precedence(repaired_schedule),
        "machine_capacity_satisfaction": _check_machine_capacity(repaired_schedule),
        "machine_downtime_satisfaction": _check_machine_downtime(
            repaired_schedule,
            machine=machine,
            unavailable_start=unavailable_start,
            unavailable_end=unavailable_end,
        ),
        "affected_operations_detected": len(affected) > 0,
        "repair_changes_makespan": _makespan(repaired_schedule) >= _makespan(initial_schedule),
    }

    feasible_after_repair = all(checks.values())

    solution = {
        "schema_version": "realm_jssp_j2_recovery_baseline.v1",
        "case_id": "J2",
        "source_case_path": "benchmarks/realm/cases/j2_jssp_simple_dynamic.json",
        "baseline_kind": "deterministic_machine_breakdown_recovery",
        "disruption": {
            "type": "machine_breakdown",
            "machine": machine,
            "unavailable_start": unavailable_start,
            "unavailable_end": unavailable_end,
        },
        "baseline": {
            "initial_schedule": initial_schedule,
            "repaired_schedule": repaired_schedule,
            "affected_operations": affected,
            "initial_makespan": _makespan(initial_schedule),
            "repaired_makespan": _makespan(repaired_schedule),
        },
        "evaluation": {
            "feasible_after_repair": feasible_after_repair,
            "constraint_checks": checks,
            "optimality_status": "feasible_not_proven_optimal",
        },
        "claims": {
            "executable_recovery_baseline": True,
            "api_bound_recovery_claimed": False,
            "j4_full_recovery_claimed": False,
            "production_runtime_claimed": False,
            "durable_logs_claimed": False,
        },
    }

    evaluation = {
        "schema_version": "realm_jssp_j2_recovery_evaluation.v1",
        "case_id": "J2",
        "feasible_after_repair": feasible_after_repair,
        "initial_makespan": solution["baseline"]["initial_makespan"],
        "repaired_makespan": solution["baseline"]["repaired_makespan"],
        "affected_operation_count": len(affected),
        "constraint_checks": checks,
        "optimality_status": "feasible_not_proven_optimal",
    }

    files = {
        "solution_json": root / "solutions" / "j2_jssp_machine_breakdown_recovery_baseline.json",
        "evaluation_json": root / "evaluations" / "j2_jssp_machine_breakdown_recovery_eval.json",
        "report_json": root / "reports" / "j2_jssp_machine_breakdown_recovery_report.json",
        "report_markdown": root / "reports" / "j2_jssp_machine_breakdown_recovery_report.md",
    }

    _write_json(files["solution_json"], solution)
    _write_json(files["evaluation_json"], evaluation)
    _write_json(files["report_json"], solution)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(solution) + "\n", encoding="utf-8")

    return J2RecoveryBaselineResult(
        output_root=root,
        files=files,
        affected_operation_count=len(affected),
        feasible_after_repair=feasible_after_repair,
        initial_makespan=solution["baseline"]["initial_makespan"],
        repaired_makespan=solution["baseline"]["repaired_makespan"],
    )


def main() -> None:
    result = run_j2_recovery_baseline()
    print("R6.8 REALM J2 machine-breakdown recovery baseline")
    print(f"output_root: {result.output_root}")
    print(f"affected_operation_count: {result.affected_operation_count}")
    print(f"feasible_after_repair: {result.feasible_after_repair}")
    print(f"initial_makespan: {result.initial_makespan}")
    print(f"repaired_makespan: {result.repaired_makespan}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
