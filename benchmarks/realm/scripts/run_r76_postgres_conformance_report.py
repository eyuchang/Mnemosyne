from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

from mnemosyne.core.store_capabilities import (  # noqa: E402
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
)


POSTGRES_CONFORMANCE_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"


@dataclass(frozen=True)
class R76PostgresConformanceReportResult:
    output_root: Path
    files: dict[str, Path]
    live_postgres_required: bool
    default_ci_safe: bool
    decision: str


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_report() -> dict[str, Any]:
    env_present = bool(os.environ.get(POSTGRES_CONFORMANCE_ENV))

    return {
        "schema_version": "r76_postgres_conformance_report.v1",
        "summary": {
            "store_schema_id": STORE_SCHEMA_ID,
            "store_schema_version": STORE_SCHEMA_VERSION,
            "postgres_conformance_env": POSTGRES_CONFORMANCE_ENV,
            "postgres_conformance_env_present": env_present,
            "live_postgres_required": False,
            "default_ci_safe": not env_present,
            "sqlite_remains_default_store": True,
            "decision": "postgres_live_conformance_harness_defined_as_opt_in",
        },
        "future_live_conformance_plan": [
            "Implement PostgreSQL recovery-store adapter behind the RecoveryStore protocol.",
            "Construct PostgreSQL store only when MNEMOSYNE_POSTGRES_DATABASE_URL is supplied.",
            "Run observe_recovery_store_conformance against PostgreSQL with restart persistence expected.",
            "Keep default CI independent of PostgreSQL service availability.",
        ],
        "claims": {
            "postgres_conformance_boundary_defined": True,
            "postgres_live_test_harness_defined": True,
            "postgres_live_test_opt_in": True,
            "sqlite_remains_default_store": True,
            "live_postgres_required": False,
            "postgres_adapter_implemented": False,
            "postgres_live_conformance_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.6 defines the PostgreSQL live conformance harness only.",
            "R7.6 does not implement the PostgreSQL adapter.",
            "R7.6 does not require a PostgreSQL service in default CI.",
            "R7.6 does not claim Kubernetes, Temporal, or production-runtime recovery.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.6 PostgreSQL Conformance Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Store schema id: `{summary['store_schema_id']}`")
    lines.append(f"- Store schema version: `{summary['store_schema_version']}`")
    lines.append(f"- PostgreSQL conformance env: `{summary['postgres_conformance_env']}`")
    lines.append(f"- Env present: {summary['postgres_conformance_env_present']}")
    lines.append(f"- Live PostgreSQL required: {summary['live_postgres_required']}")
    lines.append(f"- Default CI safe: {summary['default_ci_safe']}")
    lines.append(f"- SQLite remains default store: {summary['sqlite_remains_default_store']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Future Live Conformance Plan")
    lines.append("")
    for item in report["future_live_conformance_plan"]:
        lines.append(f"- {item}")
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


def run_r76_postgres_conformance_report(
    output_root: str | Path | None = None,
) -> R76PostgresConformanceReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = _build_report()

    files = {
        "report_json": root / "reports" / "r76_postgres_conformance_report.json",
        "report_markdown": root / "reports" / "r76_postgres_conformance_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R76PostgresConformanceReportResult(
        output_root=root,
        files=files,
        live_postgres_required=report["summary"]["live_postgres_required"],
        default_ci_safe=report["summary"]["default_ci_safe"],
        decision=report["summary"]["decision"],
    )


def main() -> None:
    result = run_r76_postgres_conformance_report()
    print("R7.6 PostgreSQL conformance report")
    print(f"output_root: {result.output_root}")
    print(f"live_postgres_required: {result.live_postgres_required}")
    print(f"default_ci_safe: {result.default_ci_safe}")
    print(f"decision: {result.decision}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
