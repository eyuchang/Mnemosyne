from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

JSSP_CASE_FILES = {
    "J1": "j1_jssp_simple_static.json",
    "J2": "j2_jssp_simple_dynamic.json",
    "J3": "j3_jssp_complex_static.json",
    "J4": "j4_jssp_complex_dynamic.json",
}

TARGET_MODULES = [
    "mnemosyne.benchmarks.jssp_disruptions",
    "mnemosyne.benchmarks.jssp_schedule_admission",
    "mnemosyne.benchmarks.jssp_disruption_commitments",
    "mnemosyne.benchmarks.jssp_recovery_proposals",
    "mnemosyne.benchmarks.jssp_repair_admission",
    "mnemosyne.api.commitments",
    "mnemosyne.api.proposal_packages",
    "mnemosyne.api.audit",
]


@dataclass(frozen=True)
class JSSPReadinessResult:
    output_root: Path
    files: dict[str, Path]
    case_count: int
    available_case_count: int
    available_module_count: int
    readiness_decision: str


def _stable_signature(value: Any) -> str:
    try:
        signature = str(inspect.signature(value))
    except (TypeError, ValueError):
        return "<unavailable>"
    return re.sub(r"0x[0-9a-fA-F]+", "0xADDR", signature)


def _public_callables(module: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in sorted(vars(module).items()):
        if name.startswith("_"):
            continue
        if not callable(value):
            continue
        lower = name.lower()
        if not any(
            token in lower
            for token in [
                "jssp",
                "schedule",
                "disruption",
                "commitment",
                "proposal",
                "repair",
                "admit",
                "audit",
                "lineage",
                "candidate",
                "recovery",
            ]
        ):
            continue
        rows.append(
            {
                "name": name,
                "kind": type(value).__name__,
                "signature": _stable_signature(value),
            }
        )
    return rows


def _load_case(case_id: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    payload: dict[str, Any] | None = None
    error: str | None = None

    if exists:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            error = repr(exc)

    top_level_keys = sorted(payload.keys()) if isinstance(payload, dict) else []

    text = json.dumps(payload, sort_keys=True).lower() if payload is not None else ""
    inferred = {
        "is_static": "static" in text,
        "is_dynamic": "dynamic" in text,
        "mentions_jssp": "jssp" in text or "job" in text or "machine" in text,
        "mentions_disruption": "disruption" in text or "breakdown" in text or "delay" in text,
        "mentions_repair": "repair" in text or "reschedule" in text or "recover" in text,
    }

    if case_id in {"J1", "J3"}:
        expected_role = "static_schedule_feasibility"
    else:
        expected_role = "dynamic_disruption_recovery"

    return {
        "case_id": case_id,
        "path": str(path.relative_to(ROOT)),
        "exists": exists,
        "load_error": error,
        "top_level_keys": top_level_keys,
        "expected_role": expected_role,
        "inferred": inferred,
        "ready_for_baseline": bool(exists and error is None and inferred["mentions_jssp"]),
    }


def _inspect_module(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        return {
            "module": module_name,
            "available": True,
            "error": None,
            "public_callables": _public_callables(module),
        }
    except Exception as exc:
        return {
            "module": module_name,
            "available": False,
            "error": repr(exc),
            "public_callables": [],
        }


def build_readiness_report() -> dict[str, Any]:
    cases_dir = REALM_ROOT / "cases"
    cases = [
        _load_case(case_id, cases_dir / filename)
        for case_id, filename in JSSP_CASE_FILES.items()
    ]
    modules = [_inspect_module(module_name) for module_name in TARGET_MODULES]

    available_case_count = sum(1 for case in cases if case["exists"])
    ready_case_count = sum(1 for case in cases if case["ready_for_baseline"])
    available_module_count = sum(1 for module in modules if module["available"])

    missing_cases = [case["case_id"] for case in cases if not case["exists"]]
    missing_modules = [module["module"] for module in modules if not module["available"]]

    if (
        available_case_count == 4
        and ready_case_count == 4
        and available_module_count == len(TARGET_MODULES)
    ):
        readiness_decision = "ready_for_executable_j1_j4_baselines"
    else:
        readiness_decision = "not_ready_missing_case_or_substrate"

    return {
        "schema_version": "realm_jssp_readiness.v1",
        "purpose": "Inspect whether REALM J1-J4 cases and Mnemosyne JSSP substrate are ready for executable benchmark work.",
        "cases": cases,
        "modules": modules,
        "summary": {
            "case_count": len(cases),
            "available_case_count": available_case_count,
            "ready_case_count": ready_case_count,
            "module_count": len(modules),
            "available_module_count": available_module_count,
            "missing_cases": missing_cases,
            "missing_modules": missing_modules,
            "readiness_decision": readiness_decision,
        },
        "recommended_next_steps": [
            "Build J1/J3 static executable schedule baselines first.",
            "Build J2/J4 dynamic disruption baselines second.",
            "Bind J2/J4 recovery to Mnemosyne JSSP APIs only after the executable baselines are reproducible.",
            "Continue to describe R6.8 recovery as benchmark-local, not production-runtime durable recovery.",
        ],
        "non_goals": [
            "Do not claim durable production recovery in R6.8.",
            "Do not introduce distributed runtime dependencies in R6.8.",
            "Do not skip static J1/J3 baselines before dynamic J2/J4 recovery.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# REALM J1-J4 JSSP Readiness Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- Case count: {summary['case_count']}")
    lines.append(f"- Available cases: {summary['available_case_count']}")
    lines.append(f"- Ready cases: {summary['ready_case_count']}")
    lines.append(f"- Module count: {summary['module_count']}")
    lines.append(f"- Available modules: {summary['available_module_count']}")
    lines.append(f"- Readiness decision: `{summary['readiness_decision']}`")
    lines.append("")

    lines.append("## Case Files")
    lines.append("")
    lines.append("| Case | Exists | Expected role | Ready for baseline | Path |")
    lines.append("|---|---:|---|---:|---|")
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['exists']} | {case['expected_role']} | "
            f"{case['ready_for_baseline']} | `{case['path']}` |"
        )
    lines.append("")

    lines.append("## Case Field Inspection")
    lines.append("")
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append("")
        lines.append(f"- Top-level keys: `{case['top_level_keys']}`")
        lines.append(f"- Inferred static: {case['inferred']['is_static']}")
        lines.append(f"- Inferred dynamic: {case['inferred']['is_dynamic']}")
        lines.append(f"- Mentions JSSP: {case['inferred']['mentions_jssp']}")
        lines.append(f"- Mentions disruption: {case['inferred']['mentions_disruption']}")
        lines.append(f"- Mentions repair: {case['inferred']['mentions_repair']}")
        lines.append("")

    lines.append("## JSSP Substrate Modules")
    lines.append("")
    for module in report["modules"]:
        lines.append(f"### `{module['module']}`")
        lines.append("")
        lines.append(f"- Available: {module['available']}")
        if module["error"]:
            lines.append(f"- Error: `{module['error']}`")
        lines.append(f"- Relevant public callables: {len(module['public_callables'])}")
        if module["public_callables"]:
            lines.append("")
            lines.append("| Callable | Kind | Signature |")
            lines.append("|---|---|---|")
            for item in module["public_callables"]:
                lines.append(
                    f"| `{item['name']}` | {item['kind']} | `{item['signature']}` |"
                )
        lines.append("")

    lines.append("## Recommended Next Steps")
    lines.append("")
    for item in report["recommended_next_steps"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Non-goals")
    lines.append("")
    for item in report["non_goals"]:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def run_readiness_report(output_root: str | Path | None = None) -> JSSPReadinessResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = build_readiness_report()

    files = {
        "json": root / "reports" / "jssp_j1_j4_readiness.json",
        "markdown": root / "reports" / "jssp_j1_j4_readiness.md",
    }

    files["json"].parent.mkdir(parents=True, exist_ok=True)
    files["json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    files["markdown"].write_text(render_markdown(report) + "\n", encoding="utf-8")

    summary = report["summary"]
    return JSSPReadinessResult(
        output_root=root,
        files=files,
        case_count=summary["case_count"],
        available_case_count=summary["available_case_count"],
        available_module_count=summary["available_module_count"],
        readiness_decision=summary["readiness_decision"],
    )


def main() -> None:
    result = run_readiness_report()
    print("R6.8 REALM J1-J4 readiness")
    print(f"output_root: {result.output_root}")
    print(f"case_count: {result.case_count}")
    print(f"available_case_count: {result.available_case_count}")
    print(f"available_module_count: {result.available_module_count}")
    print(f"readiness_decision: {result.readiness_decision}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
