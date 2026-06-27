from __future__ import annotations

import ast
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

TARGET_PATTERNS = [
    "mnemosyne/api/*.py",
    "mnemosyne/core/recovery/*.py",
    "mnemosyne/core/validation/*.py",
    "mnemosyne/benchmarks/jssp*.py",
    "tests/core/test_recovery*.py",
    "tests/benchmarks/test_jssp_repair_admission.py",
]

MUTATION_TERMS = [
    "commit_batch",
    "admit_active_commitment",
    "admit_and_finalize",
    "admit_repair",
    "finalize",
    "selected repair",
    "repair admission",
]

VALIDATION_TERMS = [
    "validator",
    "validate",
    "ValidationResult",
    "require_recovery_store",
    "RecoveryStore",
]

BOUNDARY_TERMS = [
    "public",
    "api",
    "boundary",
    "fail",
    "closed",
]


@dataclass(frozen=True)
class R74AdmissionBoundaryInspectionResult:
    output_root: Path
    files: dict[str, Path]
    inspected_file_count: int
    mutation_site_count: int
    validator_site_count: int
    decision: str


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_target_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in TARGET_PATTERNS:
        for path in ROOT.glob(pattern):
            if path.is_file() and path.suffix == ".py":
                files.add(path)
    return sorted(files)


def _functions(path: Path) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    rows: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            rows.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "async": isinstance(node, ast.AsyncFunctionDef),
                }
            )
    return sorted(rows, key=lambda row: row["line"])


def _matching_lines(path: Path, terms: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for term in terms:
            if term in line:
                rows.append(
                    {
                        "line": line_no,
                        "term": term,
                        "text": line.strip(),
                    }
                )
    return rows


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.4 Validated Recovery Admission Boundary Inspection")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Inspected files: {summary['inspected_file_count']}")
    lines.append(f"- Mutation sites: {summary['mutation_site_count']}")
    lines.append(f"- Validation sites: {summary['validator_site_count']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")

    lines.append("## Purpose")
    lines.append("")
    lines.append("R7.4 hardens recovery admission so repair/domain mutation cannot bypass validated public APIs.")
    lines.append("")
    lines.append("This inspection commit does not change mutation semantics. It identifies the admission and validation surfaces to harden next.")
    lines.append("")

    lines.append("## Mutation Sites")
    lines.append("")
    for row in report["mutation_sites"]:
        lines.append(f"### `{row['path']}`")
        lines.append("")
        for site in row["sites"]:
            lines.append(f"- L{site['line']}: `{site['term']}` — `{site['text']}`")
        lines.append("")

    lines.append("## Validation Sites")
    lines.append("")
    for row in report["validation_sites"]:
        lines.append(f"### `{row['path']}`")
        lines.append("")
        for site in row["sites"]:
            lines.append(f"- L{site['line']}: `{site['term']}` — `{site['text']}`")
        lines.append("")

    lines.append("## Recommended R7.4 Hardening Targets")
    lines.append("")
    for item in report["recommended_hardening_targets"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Claim Boundary")
    lines.append("")
    for key, value in report["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    return "\n".join(lines)


def inspect_r74_validated_admission_boundary(
    output_root: str | Path | None = None,
) -> R74AdmissionBoundaryInspectionResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    inspected: list[dict[str, Any]] = []
    mutation_sites: list[dict[str, Any]] = []
    validation_sites: list[dict[str, Any]] = []
    boundary_sites: list[dict[str, Any]] = []

    for path in _iter_target_files():
        relative = path.relative_to(ROOT).as_posix()
        functions = _functions(path)
        mutations = _matching_lines(path, MUTATION_TERMS)
        validations = _matching_lines(path, VALIDATION_TERMS)
        boundaries = _matching_lines(path, BOUNDARY_TERMS)

        inspected.append(
            {
                "path": relative,
                "functions": functions,
                "mutation_site_count": len(mutations),
                "validation_site_count": len(validations),
                "boundary_site_count": len(boundaries),
            }
        )

        if mutations:
            mutation_sites.append({"path": relative, "sites": mutations})
        if validations:
            validation_sites.append({"path": relative, "sites": validations})
        if boundaries:
            boundary_sites.append({"path": relative, "sites": boundaries})

    mutation_site_count = sum(len(row["sites"]) for row in mutation_sites)
    validator_site_count = sum(len(row["sites"]) for row in validation_sites)

    report = {
        "schema_version": "r74_validated_admission_boundary_inspection.v1",
        "summary": {
            "inspected_file_count": len(inspected),
            "mutation_site_count": mutation_site_count,
            "validator_site_count": validator_site_count,
            "decision": "ready_for_validated_admission_boundary_hardening",
        },
        "inspected_files": inspected,
        "mutation_sites": mutation_sites,
        "validation_sites": validation_sites,
        "boundary_sites": boundary_sites,
        "recommended_hardening_targets": [
            "Identify public recovery admission APIs that mutate committed state.",
            "Ensure mutation APIs require a validator or validated admission context.",
            "Fail closed when validator capability is missing.",
            "Keep low-level commit helpers available only as internal substrate helpers.",
            "Add tests proving invalid repairs cannot be admitted through the public boundary.",
            "Add tests proving recovery replay/event-log APIs remain read-only and do not mutate domain truth.",
        ],
        "claims": {
            "inspection_only": True,
            "validated_admission_hardening_claimed": False,
            "mutation_bypass_prevented_claimed": False,
            "postgres_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
    }

    files = {
        "report_json": root / "reports" / "r74_validated_admission_boundary_inspection.json",
        "report_markdown": root / "reports" / "r74_validated_admission_boundary_inspection.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R74AdmissionBoundaryInspectionResult(
        output_root=root,
        files=files,
        inspected_file_count=report["summary"]["inspected_file_count"],
        mutation_site_count=report["summary"]["mutation_site_count"],
        validator_site_count=report["summary"]["validator_site_count"],
        decision=report["summary"]["decision"],
    )


def main() -> None:
    result = inspect_r74_validated_admission_boundary()
    print("R7.4 validated admission boundary inspection")
    print(f"output_root: {result.output_root}")
    print(f"inspected_file_count: {result.inspected_file_count}")
    print(f"mutation_site_count: {result.mutation_site_count}")
    print(f"validator_site_count: {result.validator_site_count}")
    print(f"decision: {result.decision}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
