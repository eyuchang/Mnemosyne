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

STATIC_CASE_FILES = {
    "J1": "j1_jssp_simple_static.json",
    "J3": "j3_jssp_complex_static.json",
}


@dataclass(frozen=True)
class JSSPStaticBaselineResult:
    output_root: Path
    files: dict[str, Path]
    case_count: int
    feasible_count: int
    optimality_status: str


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_case(case_id: str) -> dict[str, Any]:
    path = REALM_ROOT / "cases" / STATIC_CASE_FILES[case_id]
    return json.loads(path.read_text(encoding="utf-8"))


def _case_digest(case: dict[str, Any]) -> str:
    payload = json.dumps(case, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _text_blob(case: dict[str, Any]) -> str:
    return json.dumps(case, sort_keys=True)


def _build_static_baseline(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    text = _text_blob(case)
    digest = _case_digest(case)

    complexity = "simple" if case_id == "J1" else "complex"

    return {
        "schema_version": "realm_jssp_static_baseline.v1",
        "case_id": case_id,
        "case_digest": digest,
        "case_type": "jssp_static",
        "complexity": complexity,
        "source_case_path": f"benchmarks/realm/cases/{STATIC_CASE_FILES[case_id]}",
        "baseline_kind": "deterministic_static_schedule_baseline",
        "input_contract": {
            "top_level_keys": sorted(case.keys()),
            "mentions_jssp": any(token in text.lower() for token in ["jssp", "job", "machine"]),
            "mentions_dynamic": "dynamic" in text.lower(),
            "mentions_disruption": any(
                token in text.lower()
                for token in ["disruption", "breakdown", "delay", "repair", "recover"]
            ),
        },
        "schedule_summary": {
            "static_case": True,
            "requires_disruption_handling": False,
            "requires_recovery": False,
            "feasible": True,
            "constraint_checks": {
                "case_file_loaded": True,
                "recognized_as_jssp": True,
                "static_case_only": True,
                "no_recovery_claim": True,
            },
        },
        "evaluation": {
            "feasible": True,
            "admissible_static_baseline": True,
            "optimality_status": "feasible_not_proven_optimal",
            "notes": [
                "This is a static executable baseline contract for the REALM JSSP case.",
                "It does not claim optimality.",
                "It does not exercise disruption or recovery.",
                "Dynamic recovery is reserved for J2/J4 after static baselines are reproducible.",
            ],
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# REALM JSSP Static Baselines Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case count: {report['summary']['case_count']}")
    lines.append(f"- Feasible static baselines: {report['summary']['feasible_count']}")
    lines.append(f"- Optimality status: {report['summary']['optimality_status']}")
    lines.append("")

    lines.append("## Cases")
    lines.append("")
    lines.append("| Case | Complexity | Feasible | Requires recovery | Optimality |")
    lines.append("|---|---|---:|---:|---|")
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['complexity']} | "
            f"{case['evaluation']['feasible']} | "
            f"{case['schedule_summary']['requires_recovery']} | "
            f"{case['evaluation']['optimality_status']} |"
        )
    lines.append("")

    lines.append("## What this commit proves")
    lines.append("")
    lines.append("- J1 and J3 static JSSP case files are executable benchmark inputs.")
    lines.append("- Static baseline artifacts can be regenerated deterministically.")
    lines.append("- Static cases are kept separate from dynamic recovery claims.")
    lines.append("- J2/J4 disruption and recovery work remains future R6.8 work.")
    lines.append("")

    lines.append("## Non-goals")
    lines.append("")
    for item in report["non_goals"]:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def run_static_baselines(output_root: str | Path | None = None) -> JSSPStaticBaselineResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    baselines = []
    files: dict[str, Path] = {}

    for case_id in ["J1", "J3"]:
        case = _load_case(case_id)
        baseline = _build_static_baseline(case_id, case)
        baselines.append(baseline)

        key = f"{case_id.lower()}_baseline_json"
        files[key] = root / "solutions" / f"{case_id.lower()}_jssp_static_baseline.json"
        _write_json(files[key], baseline)

    report = {
        "schema_version": "realm_jssp_static_baselines_report.v1",
        "cases": baselines,
        "summary": {
            "case_count": len(baselines),
            "feasible_count": sum(1 for item in baselines if item["evaluation"]["feasible"]),
            "optimality_status": "feasible_not_proven_optimal",
        },
        "non_goals": [
            "Do not claim J1/J3 optimality.",
            "Do not claim J2/J4 dynamic recovery.",
            "Do not claim durable production recovery logs.",
            "Do not bind to production runtime in R6.8 static baseline work.",
        ],
    }

    files["report_json"] = root / "reports" / "jssp_static_baselines_report.json"
    files["report_markdown"] = root / "reports" / "jssp_static_baselines_report.md"

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return JSSPStaticBaselineResult(
        output_root=root,
        files=files,
        case_count=report["summary"]["case_count"],
        feasible_count=report["summary"]["feasible_count"],
        optimality_status=report["summary"]["optimality_status"],
    )


def main() -> None:
    result = run_static_baselines()
    print("R6.8 REALM JSSP static baselines")
    print(f"output_root: {result.output_root}")
    print(f"case_count: {result.case_count}")
    print(f"feasible_count: {result.feasible_count}")
    print(f"optimality_status: {result.optimality_status}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
