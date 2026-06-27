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
    "mnemosyne/core/*.py",
    "mnemosyne/runtime/*.py",
    "mnemosyne/store/*.py",
    "mnemosyne/benchmarks/jssp*.py",
]

COUPLING_TERMS = [
    "sqlite",
    "SQLite",
    "sqlite3",
    "execute(",
    "executemany(",
    "cursor(",
    "commit(",
    "rollback(",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
]

RECOVERY_TERMS = [
    "recovery",
    "commitment",
    "proposal",
    "admission",
    "audit",
    "lineage",
    "finalize",
    "unresolved",
]


@dataclass(frozen=True)
class R7StoreBoundaryInspectionResult:
    output_root: Path
    files: dict[str, Path]
    inspected_file_count: int
    coupling_site_count: int
    recovery_related_file_count: int
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


def _imports_for_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
    return sorted(set(imports))


def _is_recovery_related(text: str, path: Path) -> bool:
    lowered = text.lower()
    path_text = str(path).lower()
    return any(term in lowered or term in path_text for term in RECOVERY_TERMS)


def _coupling_sites(path: Path, text: str) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    lines = text.splitlines()

    for index, line in enumerate(lines, start=1):
        for term in COUPLING_TERMS:
            if term in line:
                sites.append(
                    {
                        "line": index,
                        "term": term,
                        "text": line.strip(),
                    }
                )

    return sites


def _protocol_mentions(text: str) -> list[str]:
    candidates = sorted(set(re.findall(r"\b[A-Za-z0-9_]*Protocol\b", text)))
    return candidates


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# R7.1 Recovery Store Boundary Inspection")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- Inspected files: {summary['inspected_file_count']}")
    lines.append(f"- Recovery-related files: {summary['recovery_related_file_count']}")
    lines.append(f"- Coupling sites: {summary['coupling_site_count']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")

    lines.append("## R7.1 Purpose")
    lines.append("")
    lines.append("R7 begins by identifying recovery, audit, proposal, admission, and lineage paths that must be placed behind durable store protocols before adding PostgreSQL or production runtime execution.")
    lines.append("")
    lines.append("R7.1 does not claim Postgres support, distributed storage, Kubernetes deployment, Temporal execution, or production-runtime recovery.")
    lines.append("")

    lines.append("## Recovery-Related Files")
    lines.append("")
    for row in report["recovery_related_files"]:
        lines.append(f"- `{row['path']}`")
    lines.append("")

    lines.append("## Store Coupling Sites")
    lines.append("")
    if report["coupling_sites"]:
        for row in report["coupling_sites"]:
            lines.append(f"### `{row['path']}`")
            lines.append("")
            for site in row["sites"]:
                lines.append(f"- L{site['line']}: `{site['term']}` — `{site['text']}`")
            lines.append("")
    else:
        lines.append("- No direct coupling sites detected by lexical inspection.")
        lines.append("")

    lines.append("## Protocol Mentions")
    lines.append("")
    for row in report["protocol_mentions"]:
        lines.append(f"- `{row['path']}`: {', '.join(row['protocols'])}")
    lines.append("")

    lines.append("## Recommended R7.1 Refactor Targets")
    lines.append("")
    for item in report["recommended_refactor_targets"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Claim Boundary")
    lines.append("")
    for key, value in report["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    return "\n".join(lines)


def inspect_r7_recovery_store_boundary(
    output_root: str | Path | None = None,
) -> R7StoreBoundaryInspectionResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    inspected: list[dict[str, Any]] = []
    coupling_rows: list[dict[str, Any]] = []
    recovery_files: list[dict[str, Any]] = []
    protocol_rows: list[dict[str, Any]] = []

    for path in _iter_target_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()

        imports = _imports_for_file(path)
        recovery_related = _is_recovery_related(text, path)
        sites = _coupling_sites(path, text)
        protocols = _protocol_mentions(text)

        inspected.append(
            {
                "path": relative,
                "imports": imports,
                "recovery_related": recovery_related,
                "coupling_site_count": len(sites),
                "protocols": protocols,
            }
        )

        if recovery_related:
            recovery_files.append({"path": relative})

        if sites:
            coupling_rows.append({"path": relative, "sites": sites})

        if protocols:
            protocol_rows.append({"path": relative, "protocols": protocols})

    coupling_site_count = sum(len(row["sites"]) for row in coupling_rows)

    report = {
        "schema_version": "r7_recovery_store_boundary_inspection.v1",
        "summary": {
            "inspected_file_count": len(inspected),
            "recovery_related_file_count": len(recovery_files),
            "coupling_site_count": coupling_site_count,
            "decision": "ready_for_store_protocol_refactor",
        },
        "inspected_files": inspected,
        "recovery_related_files": recovery_files,
        "coupling_sites": coupling_rows,
        "protocol_mentions": protocol_rows,
        "recommended_refactor_targets": [
            "Define an explicit RecoveryStore protocol for active commitments, proposal packages, recovery lineage, and recovery events.",
            "Keep SQLiteStore as the first protocol-conformance implementation.",
            "Move direct audit/recovery persistence assumptions behind protocol methods before adding PostgreSQL.",
            "Add fail-closed tests for missing recovery store capabilities.",
            "Add a durable append-only recovery event log only after the protocol boundary is explicit.",
        ],
        "claims": {
            "inspection_only": True,
            "store_protocol_refactor_claimed": False,
            "postgres_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
    }

    files = {
        "report_json": root / "reports" / "r71_recovery_store_boundary_inspection.json",
        "report_markdown": root / "reports" / "r71_recovery_store_boundary_inspection.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R7StoreBoundaryInspectionResult(
        output_root=root,
        files=files,
        inspected_file_count=report["summary"]["inspected_file_count"],
        coupling_site_count=report["summary"]["coupling_site_count"],
        recovery_related_file_count=report["summary"]["recovery_related_file_count"],
        decision=report["summary"]["decision"],
    )


def main() -> None:
    result = inspect_r7_recovery_store_boundary()
    print("R7.1 recovery store boundary inspection")
    print(f"output_root: {result.output_root}")
    print(f"inspected_file_count: {result.inspected_file_count}")
    print(f"recovery_related_file_count: {result.recovery_related_file_count}")
    print(f"coupling_site_count: {result.coupling_site_count}")
    print(f"decision: {result.decision}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
