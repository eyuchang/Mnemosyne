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

from benchmarks.realm.scripts.inspect_jssp_dynamic_contracts import (  # noqa: E402
    run_dynamic_contracts,
)
from benchmarks.realm.scripts.inspect_jssp_readiness import (  # noqa: E402
    run_readiness_report,
)
from benchmarks.realm.scripts.run_jssp_j2_api_bound_recovery import (  # noqa: E402
    run_j2_api_bound_recovery,
)
from benchmarks.realm.scripts.run_jssp_j2_recovery_baseline import (  # noqa: E402
    run_j2_recovery_baseline,
)
from benchmarks.realm.scripts.run_jssp_j4_material_recovery_baseline import (  # noqa: E402
    run_j4_material_recovery_baseline,
)
from benchmarks.realm.scripts.run_jssp_static_baselines import (  # noqa: E402
    run_static_baselines,
)


@dataclass(frozen=True)
class JSSPJ1J4SuiteResult:
    output_root: Path
    files: dict[str, Path]
    readiness_decision: str
    static_case_count: int
    dynamic_contract_case_count: int
    j2_api_bound: bool
    j4_material_recovery: bool
    j4_api_bound: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# REALM J1-J4 JSSP Suite Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- Readiness decision: `{summary['readiness_decision']}`")
    lines.append(f"- Static baseline cases: {summary['static_case_count']}")
    lines.append(f"- Dynamic contract cases: {summary['dynamic_contract_case_count']}")
    lines.append(f"- J2 deterministic recovery baseline: {summary['j2_deterministic_recovery_baseline']}")
    lines.append(f"- J2 API-bound recovery: {summary['j2_api_bound_recovery']}")
    lines.append(f"- J4 material recovery baseline: {summary['j4_material_recovery_baseline']}")
    lines.append(f"- J4 API-bound recovery: {summary['j4_api_bound_recovery']}")
    lines.append(f"- Production-runtime recovery claimed: {summary['production_runtime_claimed']}")
    lines.append(f"- Durable logs claimed: {summary['durable_logs_claimed']}")
    lines.append("")

    lines.append("## Case Coverage")
    lines.append("")
    lines.append("| Case | Mode | R6 status | Claim boundary |")
    lines.append("|---|---|---|---|")
    for row in report["case_coverage"]:
        lines.append(
            f"| {row['case_id']} | {row['mode']} | {row['r6_status']} | {row['claim_boundary']} |"
        )
    lines.append("")

    lines.append("## Generated Artifacts")
    lines.append("")
    for key, path in report["generated_artifacts"].items():
        lines.append(f"- {key}: `{path}`")
    lines.append("")

    lines.append("## R6.9 Decision")
    lines.append("")
    lines.append("- J1 and J3 have deterministic static executable baselines.")
    lines.append("- J2 has deterministic recovery plus API-bound recovery through active commitment memory, proposal emission, repair admission, commitment finalization, and audit lineage.")
    lines.append("- J4 now has deterministic benchmark-local material/resource recovery.")
    lines.append("- J4 is not yet API-bound to active commitment memory.")
    lines.append("- R6.9 completes the R6 REALM J1-J4 executable benchmark layer without claiming production-runtime durable recovery.")
    lines.append("")

    return "\n".join(lines)


def run_jssp_j1_j4_suite(output_root: str | Path | None = None) -> JSSPJ1J4SuiteResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    readiness = run_readiness_report(root)
    static = run_static_baselines(root)
    dynamic_contracts = run_dynamic_contracts(root)
    j2_baseline = run_j2_recovery_baseline(root)
    j2_api_bound = run_j2_api_bound_recovery(root)
    j4_material = run_j4_material_recovery_baseline(root)

    readiness_json = _read_json(readiness.files["json"])
    dynamic_json = _read_json(dynamic_contracts.files["report_json"])
    j2_api_json = _read_json(j2_api_bound.files["api_bound_json"])
    j4_json = _read_json(j4_material.files["solution_json"])

    generated_artifacts = {
        "readiness_report": "benchmarks/realm/reports/jssp_j1_j4_readiness.md",
        "static_baselines_report": "benchmarks/realm/reports/jssp_static_baselines_report.md",
        "dynamic_contracts_report": "benchmarks/realm/reports/jssp_dynamic_contracts_report.md",
        "j2_recovery_baseline_report": "benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.md",
        "j2_api_bound_recovery_report": "benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.md",
        "j4_material_recovery_report": "benchmarks/realm/reports/j4_jssp_material_recovery_report.md",
    }

    report = {
        "schema_version": "realm_jssp_j1_j4_suite_report.v2",
        "summary": {
            "readiness_decision": readiness_json["summary"]["readiness_decision"],
            "static_case_count": static.case_count,
            "dynamic_contract_case_count": dynamic_contracts.case_count,
            "j2_deterministic_recovery_baseline": j2_baseline.feasible_after_repair,
            "j2_api_bound_recovery": j2_api_json["claims"]["api_bound_recovery_claimed"],
            "j4_material_recovery_baseline": j4_json["claims"]["j4_material_recovery_claimed"],
            "j4_api_bound_recovery": j4_json["claims"]["api_bound_recovery_claimed"],
            "production_runtime_claimed": False,
            "durable_logs_claimed": False,
            "r6_j1_j4_executable_layer_complete": True,
        },
        "case_coverage": [
            {
                "case_id": "J1",
                "mode": "static",
                "r6_status": "deterministic_static_baseline",
                "claim_boundary": "feasible_not_proven_optimal",
            },
            {
                "case_id": "J2",
                "mode": "dynamic",
                "r6_status": "deterministic_recovery_and_api_bound_commitment_recovery",
                "claim_boundary": "benchmark_local_api_bound_recovery",
            },
            {
                "case_id": "J3",
                "mode": "static",
                "r6_status": "deterministic_static_baseline",
                "claim_boundary": "feasible_not_proven_optimal",
            },
            {
                "case_id": "J4",
                "mode": "dynamic",
                "r6_status": "deterministic_material_resource_recovery_baseline",
                "claim_boundary": "benchmark_local_material_recovery_not_api_bound",
            },
        ],
        "dynamic_contract_summary": dynamic_json["summary"],
        "generated_artifacts": generated_artifacts,
    }

    files = {
        "report_json": root / "reports" / "jssp_j1_j4_suite_report.json",
        "report_markdown": root / "reports" / "jssp_j1_j4_suite_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return JSSPJ1J4SuiteResult(
        output_root=root,
        files=files,
        readiness_decision=report["summary"]["readiness_decision"],
        static_case_count=report["summary"]["static_case_count"],
        dynamic_contract_case_count=report["summary"]["dynamic_contract_case_count"],
        j2_api_bound=report["summary"]["j2_api_bound_recovery"],
        j4_material_recovery=report["summary"]["j4_material_recovery_baseline"],
        j4_api_bound=report["summary"]["j4_api_bound_recovery"],
    )


def main() -> None:
    result = run_jssp_j1_j4_suite()
    print("R6.9 REALM J1-J4 JSSP suite")
    print(f"output_root: {result.output_root}")
    print(f"readiness_decision: {result.readiness_decision}")
    print(f"static_case_count: {result.static_case_count}")
    print(f"dynamic_contract_case_count: {result.dynamic_contract_case_count}")
    print(f"j2_api_bound: {result.j2_api_bound}")
    print(f"j4_material_recovery: {result.j4_material_recovery}")
    print(f"j4_api_bound: {result.j4_api_bound}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
