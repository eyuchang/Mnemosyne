from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = REALM_ROOT / "cases" / "j4_jssp_complex_dynamic.json"


@dataclass(frozen=True)
class J4MaterialRecoveryBaselineResult:
    output_root: Path
    files: dict[str, Path]
    operation_count: int
    affected_operation_count: int
    initial_makespan: int
    repaired_makespan: int
    feasible_after_repair: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_case() -> dict[str, Any]:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def _case_digest(case: dict[str, Any]) -> str:
    payload = json.dumps(case, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _normalize_machine(machine: str) -> str:
    return machine.split()[0]


def _operation_id(job_id: str, operation_index: int) -> str:
    return f"{job_id}:O{operation_index}"


def _expand_operations(case: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []

    for template in case["entities"]["operation_templates"]:
        for job_id in template["jobs"]:
            for index, operation in enumerate(template["operations"], start=1):
                machine = _normalize_machine(operation["machine"])
                operations.append(
                    {
                        "operation_id": _operation_id(job_id, index),
                        "job_id": job_id,
                        "operation_index": index,
                        "machine": machine,
                        "duration": int(operation["duration"]),
                        "materials": _material_policy(machine, index),
                    }
                )

    return operations


def _material_policy(machine: str, operation_index: int) -> list[str]:
    """Deterministic R6.9 material-policy realization for the underspecified J4 case.

    The REALM J4 case names material-unavailability examples but does not define
    a per-operation material bill of materials. R6.9 makes that missing substrate
    explicit and benchmark-local.
    """

    if machine == "M1":
        return ["RM-S"]
    if machine == "M2":
        return ["RM-A"]
    if machine == "M3":
        return ["C-X"]
    if machine == "M4":
        return ["C-X", "F"]
    return []


def _material_unavailability_realization(case: dict[str, Any]) -> list[dict[str, Any]]:
    examples: list[str] = []
    for disruption in case.get("disruptions", []):
        if disruption.get("type") == "material_unavailability":
            examples = list(disruption.get("materials_examples", []))

    # J4 gives material examples but no outage windows. R6.9 defines a
    # deterministic benchmark-local realization, not a claim about the source case.
    windows = {
        "C-X": (4, 8),
        "F": (6, 10),
    }

    return [
        {
            "event_id": f"realm-j4:material-unavailable:{material}:{start}-{end}",
            "type": "material_unavailability",
            "material": material,
            "unavailable_start": start,
            "unavailable_end": end,
            "source": "r69_deterministic_realization",
        }
        for material, (start, end) in windows.items()
        if material in examples
    ]


def _interval_overlaps(start: int, end: int, block_start: int, block_end: int) -> bool:
    return start < block_end and end > block_start


def _blocked_material_windows(
    material_events: list[dict[str, Any]],
) -> dict[str, tuple[int, int]]:
    return {
        event["material"]: (int(event["unavailable_start"]), int(event["unavailable_end"]))
        for event in material_events
    }


def _advance_for_materials(
    *,
    earliest: int,
    duration: int,
    materials: list[str],
    material_blocks: dict[str, tuple[int, int]],
) -> int:
    start = earliest

    while True:
        shifted = False
        for material in materials:
            if material not in material_blocks:
                continue
            block_start, block_end = material_blocks[material]
            if _interval_overlaps(start, start + duration, block_start, block_end):
                start = block_end
                shifted = True
        if not shifted:
            return start


def _build_greedy_schedule(
    operations: list[dict[str, Any]],
    *,
    material_events: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    material_blocks = _blocked_material_windows(material_events or [])

    jobs = sorted({operation["job_id"] for operation in operations})
    machines = sorted({operation["machine"] for operation in operations})
    max_ops = max(operation["operation_index"] for operation in operations)

    by_job_and_index = {
        (operation["job_id"], operation["operation_index"]): operation
        for operation in operations
    }

    job_available = {job: 0 for job in jobs}
    machine_available = {machine: 0 for machine in machines}
    scheduled: list[dict[str, Any]] = []

    for operation_index in range(1, max_ops + 1):
        for job_id in jobs:
            operation = by_job_and_index.get((job_id, operation_index))
            if operation is None:
                continue

            start = max(
                job_available[job_id],
                machine_available[operation["machine"]],
            )
            start = _advance_for_materials(
                earliest=start,
                duration=operation["duration"],
                materials=operation["materials"],
                material_blocks=material_blocks,
            )
            end = start + operation["duration"]

            row = dict(operation)
            row["start"] = start
            row["end"] = end
            scheduled.append(row)

            job_available[job_id] = end
            machine_available[operation["machine"]] = end

    return scheduled


def _makespan(schedule: list[dict[str, Any]]) -> int:
    return max(row["end"] for row in schedule)


def _affected_operations(
    schedule: list[dict[str, Any]],
    material_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    affected: list[dict[str, Any]] = []

    for operation in schedule:
        for event in material_events:
            material = event["material"]
            if material not in operation["materials"]:
                continue
            if _interval_overlaps(
                operation["start"],
                operation["end"],
                int(event["unavailable_start"]),
                int(event["unavailable_end"]),
            ):
                row = dict(operation)
                row["blocked_material"] = material
                row["material_event_id"] = event["event_id"]
                affected.append(row)

    return affected


def _check_precedence(schedule: list[dict[str, Any]]) -> bool:
    by_job: dict[str, list[dict[str, Any]]] = {}
    for operation in schedule:
        by_job.setdefault(operation["job_id"], []).append(operation)

    for operations in by_job.values():
        ordered = sorted(operations, key=lambda row: row["operation_index"])
        for left, right in zip(ordered, ordered[1:]):
            if left["end"] > right["start"]:
                return False
    return True


def _check_machine_capacity(schedule: list[dict[str, Any]]) -> bool:
    by_machine: dict[str, list[dict[str, Any]]] = {}
    for operation in schedule:
        by_machine.setdefault(operation["machine"], []).append(operation)

    for operations in by_machine.values():
        ordered = sorted(operations, key=lambda row: (row["start"], row["end"]))
        for left, right in zip(ordered, ordered[1:]):
            if left["end"] > right["start"]:
                return False
    return True


def _check_material_availability(
    schedule: list[dict[str, Any]],
    material_events: list[dict[str, Any]],
) -> bool:
    return not _affected_operations(schedule, material_events)


def _render_markdown(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    evaluation = report["evaluation"]

    lines: list[str] = []

    lines.append("# REALM J4 Material Recovery Baseline")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case: {report['case_id']}")
    lines.append(f"- Operation count: {baseline['operation_count']}")
    lines.append(f"- Initial makespan: {baseline['initial_makespan']}")
    lines.append(f"- Repaired makespan: {baseline['repaired_makespan']}")
    lines.append(f"- Affected material-operation pairs: {len(baseline['affected_operations'])}")
    lines.append(f"- Feasible after repair: {evaluation['feasible_after_repair']}")
    lines.append(f"- Optimality status: {evaluation['optimality_status']}")
    lines.append("")

    lines.append("## Material Unavailability Realization")
    lines.append("")
    lines.append("J4 names material-unavailability examples but does not define outage windows or a per-operation bill of materials; R6.9 makes this benchmark-local realization explicit.")
    lines.append("")
    for event in report["material_events"]:
        lines.append(
            f"- `{event['material']}` unavailable from "
            f"{event['unavailable_start']} to {event['unavailable_end']}"
        )
    lines.append("")

    lines.append("## Affected Operations")
    lines.append("")
    for operation in baseline["affected_operations"]:
        lines.append(
            f"- `{operation['operation_id']}` requires `{operation['blocked_material']}` "
            f"and initially ran {operation['start']} to {operation['end']}"
        )
    lines.append("")

    lines.append("## Constraint Checks")
    lines.append("")
    for key, value in evaluation["constraint_checks"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Claims")
    lines.append("")
    for key, value in report["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def run_j4_material_recovery_baseline(
    output_root: str | Path | None = None,
) -> J4MaterialRecoveryBaselineResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    case = _load_case()
    operations = _expand_operations(case)
    material_events = _material_unavailability_realization(case)

    initial_schedule = _build_greedy_schedule(operations)
    affected = _affected_operations(initial_schedule, material_events)
    repaired_schedule = _build_greedy_schedule(
        operations,
        material_events=material_events,
    )

    checks = {
        "case_file_loaded": True,
        "operation_templates_expanded": len(operations) == 20,
        "material_policy_defined": True,
        "material_events_realized": len(material_events) == 2,
        "affected_operations_detected": len(affected) > 0,
        "precedence_satisfaction": _check_precedence(repaired_schedule),
        "machine_capacity_satisfaction": _check_machine_capacity(repaired_schedule),
        "material_availability_satisfaction": _check_material_availability(
            repaired_schedule,
            material_events,
        ),
        "repair_does_not_reduce_makespan": _makespan(repaired_schedule)
        >= _makespan(initial_schedule),
    }

    feasible_after_repair = all(checks.values())

    report = {
        "schema_version": "realm_jssp_j4_material_recovery_baseline.v1",
        "case_id": "J4",
        "source_case_path": "benchmarks/realm/cases/j4_jssp_complex_dynamic.json",
        "case_digest": _case_digest(case),
        "baseline_kind": "deterministic_material_resource_recovery",
        "material_policy": {
            "policy_id": "r69_j4_material_policy.v1",
            "source_case_materials": case["entities"]["materials"],
            "machine_to_materials": {
                "M1": ["RM-S"],
                "M2": ["RM-A"],
                "M3": ["C-X"],
                "M4": ["C-X", "F"],
            },
            "note": "J4 names material-unavailability examples but not per-operation bills of material; R6.9 makes this benchmark-local policy explicit.",
        },
        "material_events": material_events,
        "baseline": {
            "operation_count": len(operations),
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
            "j4_material_recovery_claimed": True,
            "material_resource_substrate_claimed": True,
            "benchmark_local_recovery_claimed": True,
            "api_bound_recovery_claimed": False,
            "active_commitment_memory_claimed": False,
            "production_runtime_claimed": False,
            "durable_logs_claimed": False,
            "global_optimality_claimed": False,
        },
        "limitations": [
            "This is a deterministic benchmark-local material recovery substrate.",
            "The J4 case provides material examples but no outage windows or bill-of-materials mapping; R6.9 makes those assumptions explicit.",
            "This commit does not bind material recovery to active commitment memory.",
            "This commit does not claim production-runtime durable recovery.",
        ],
    }

    files = {
        "solution_json": root / "solutions" / "j4_jssp_material_recovery_baseline.json",
        "evaluation_json": root / "evaluations" / "j4_jssp_material_recovery_eval.json",
        "report_json": root / "reports" / "j4_jssp_material_recovery_report.json",
        "report_markdown": root / "reports" / "j4_jssp_material_recovery_report.md",
    }

    _write_json(files["solution_json"], report)
    _write_json(files["evaluation_json"], report["evaluation"])
    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return J4MaterialRecoveryBaselineResult(
        output_root=root,
        files=files,
        operation_count=len(operations),
        affected_operation_count=len(affected),
        initial_makespan=report["baseline"]["initial_makespan"],
        repaired_makespan=report["baseline"]["repaired_makespan"],
        feasible_after_repair=feasible_after_repair,
    )


def main() -> None:
    result = run_j4_material_recovery_baseline()
    print("R6.9 REALM J4 material recovery baseline")
    print(f"output_root: {result.output_root}")
    print(f"operation_count: {result.operation_count}")
    print(f"affected_operation_count: {result.affected_operation_count}")
    print(f"initial_makespan: {result.initial_makespan}")
    print(f"repaired_makespan: {result.repaired_makespan}")
    print(f"feasible_after_repair: {result.feasible_after_repair}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
