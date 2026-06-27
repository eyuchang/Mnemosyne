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

DYNAMIC_CASE_FILES = {
    "J2": "j2_jssp_simple_dynamic.json",
    "J4": "j4_jssp_complex_dynamic.json",
}


@dataclass(frozen=True)
class JSSPDynamicContractResult:
    output_root: Path
    files: dict[str, Path]
    case_count: int
    existing_substrate_ready_count: int
    requires_extension_count: int


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_case(case_id: str) -> dict[str, Any]:
    path = REALM_ROOT / "cases" / DYNAMIC_CASE_FILES[case_id]
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_for_case(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    disruptions = case.get("disruptions", [])
    disruption_types = [item.get("type") for item in disruptions if isinstance(item, dict)]

    has_machine_breakdown = any(
        item.get("type") == "machine_breakdown_example"
        for item in disruptions
        if isinstance(item, dict)
    )
    has_material_unavailability = any(
        item.get("type") == "material_unavailability"
        for item in disruptions
        if isinstance(item, dict)
    )
    has_stochastic_delay = any(
        item.get("type") == "stochastic_operation_delay"
        for item in disruptions
        if isinstance(item, dict)
    )

    actionable_events: list[dict[str, Any]] = []
    extension_requirements: list[str] = []

    for index, disruption in enumerate(disruptions, start=1):
        if not isinstance(disruption, dict):
            continue

        dtype = disruption.get("type")

        if dtype == "machine_breakdown_example":
            actionable_events.append(
                {
                    "event_id": f"{case_id.lower()}-machine-breakdown-{index}",
                    "type": "machine_breakdown",
                    "machine": disruption.get("machine"),
                    "unavailable_start": disruption.get("unavailable_start"),
                    "unavailable_end": disruption.get("unavailable_end"),
                    "existing_jssp_substrate": "supported",
                    "maps_to": [
                        "mnemosyne.benchmarks.jssp_disruptions",
                        "mnemosyne.benchmarks.jssp_disruption_commitments",
                        "mnemosyne.benchmarks.jssp_recovery_proposals",
                        "mnemosyne.benchmarks.jssp_repair_admission",
                    ],
                }
            )

        elif dtype == "material_unavailability":
            extension_requirements.append(
                "material_unavailability requires material/resource commitment and repair substrate"
            )
            actionable_events.append(
                {
                    "event_id": f"{case_id.lower()}-material-unavailability-{index}",
                    "type": "material_unavailability",
                    "materials_examples": disruption.get("materials_examples", []),
                    "existing_jssp_substrate": "requires_extension",
                    "maps_to": [],
                }
            )

        elif dtype == "stochastic_operation_delay":
            actionable_events.append(
                {
                    "event_id": f"{case_id.lower()}-stochastic-operation-delay-{index}",
                    "type": "stochastic_operation_delay",
                    "distribution": disruption.get("distribution"),
                    "revealed_at": disruption.get("revealed_at"),
                    "existing_jssp_substrate": "contract_only",
                    "maps_to": [],
                }
            )

    if case_id == "J2" and has_machine_breakdown:
        readiness = "ready_for_existing_machine_breakdown_recovery"
    elif case_id == "J4" and has_material_unavailability:
        readiness = "requires_material_recovery_extension"
    else:
        readiness = "contract_only_not_ready_for_recovery"

    return {
        "schema_version": "realm_jssp_dynamic_contract.v1",
        "case_id": case_id,
        "case_path": f"benchmarks/realm/cases/{DYNAMIC_CASE_FILES[case_id]}",
        "family": case.get("family"),
        "mode": case.get("mode"),
        "short_name": case.get("short_name"),
        "objective": case.get("objective"),
        "metrics": case.get("metrics", []),
        "disruption_types": disruption_types,
        "has_stochastic_delay": has_stochastic_delay,
        "has_machine_breakdown": has_machine_breakdown,
        "has_material_unavailability": has_material_unavailability,
        "actionable_events": actionable_events,
        "readiness": readiness,
        "extension_requirements": extension_requirements,
        "claims": {
            "executable_dynamic_contract": True,
            "full_recovery_claimed": False,
            "production_runtime_claimed": False,
            "durable_logs_claimed": False,
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# REALM JSSP Dynamic Disruption Contracts Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- Case count: {summary['case_count']}")
    lines.append(f"- Existing substrate ready: {summary['existing_substrate_ready_count']}")
    lines.append(f"- Requires extension: {summary['requires_extension_count']}")
    lines.append("")

    lines.append("## Case Readiness")
    lines.append("")
    lines.append("| Case | Readiness | Machine breakdown | Material unavailable | Full recovery claimed |")
    lines.append("|---|---|---:|---:|---:|")
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | `{case['readiness']}` | "
            f"{case['has_machine_breakdown']} | "
            f"{case['has_material_unavailability']} | "
            f"{case['claims']['full_recovery_claimed']} |"
        )
    lines.append("")

    lines.append("## Actionable Events")
    lines.append("")
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append("")
        for event in case["actionable_events"]:
            lines.append(f"- `{event['event_id']}`")
            lines.append(f"  - type: `{event['type']}`")
            lines.append(f"  - substrate: `{event['existing_jssp_substrate']}`")
            if event.get("machine"):
                lines.append(f"  - machine: `{event['machine']}`")
                lines.append(f"  - unavailable: {event['unavailable_start']} to {event['unavailable_end']}")
            if event.get("materials_examples"):
                lines.append(f"  - materials examples: `{event['materials_examples']}`")
            if event.get("distribution"):
                lines.append(f"  - distribution: `{event['distribution']}`")
            if event.get("revealed_at"):
                lines.append(f"  - revealed at: `{event['revealed_at']}`")
        lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append("- J2 can proceed to existing machine-breakdown recovery binding.")
    lines.append("- J4 must not be presented as fully recoverable yet.")
    lines.append("- J4 needs material/resource recovery extension before an honest full-recovery claim.")
    lines.append("- R6.8 should keep recovery claims benchmark-local and contract-scoped.")
    lines.append("")

    return "\n".join(lines)


def run_dynamic_contracts(
    output_root: str | Path | None = None,
) -> JSSPDynamicContractResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    files: dict[str, Path] = {}
    contracts: list[dict[str, Any]] = []

    for case_id in ["J2", "J4"]:
        case = _load_case(case_id)
        contract = _contract_for_case(case_id, case)
        contracts.append(contract)

        key = f"{case_id.lower()}_contract_json"
        files[key] = root / "evaluations" / f"{case_id.lower()}_jssp_dynamic_contract.json"
        _write_json(files[key], contract)

    report = {
        "schema_version": "realm_jssp_dynamic_contracts_report.v1",
        "cases": contracts,
        "summary": {
            "case_count": len(contracts),
            "existing_substrate_ready_count": sum(
                1
                for item in contracts
                if item["readiness"] == "ready_for_existing_machine_breakdown_recovery"
            ),
            "requires_extension_count": sum(
                1
                for item in contracts
                if item["readiness"] == "requires_material_recovery_extension"
            ),
        },
        "non_goals": [
            "Do not claim full J4 recovery before material recovery substrate exists.",
            "Do not claim production-runtime durable recovery in R6.8.",
            "Do not treat stochastic delay distributions as realized schedules without an explicit realization policy.",
        ],
    }

    files["report_json"] = root / "reports" / "jssp_dynamic_contracts_report.json"
    files["report_markdown"] = root / "reports" / "jssp_dynamic_contracts_report.md"

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return JSSPDynamicContractResult(
        output_root=root,
        files=files,
        case_count=report["summary"]["case_count"],
        existing_substrate_ready_count=report["summary"]["existing_substrate_ready_count"],
        requires_extension_count=report["summary"]["requires_extension_count"],
    )


def main() -> None:
    result = run_dynamic_contracts()
    print("R6.8 REALM JSSP dynamic disruption contracts")
    print(f"output_root: {result.output_root}")
    print(f"case_count: {result.case_count}")
    print(f"existing_substrate_ready_count: {result.existing_substrate_ready_count}")
    print(f"requires_extension_count: {result.requires_extension_count}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
