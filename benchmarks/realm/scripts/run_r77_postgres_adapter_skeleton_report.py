from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

from mnemosyne.core.store_capabilities import store_capability_report_to_dict  # noqa: E402
from mnemosyne.store.factory import (  # noqa: E402
    POSTGRES_BACKEND,
    SQLITE_BACKEND,
    STORE_BACKEND_ENV,
    SQLITE_PATH_ENV,
    StoreFactoryConfig,
    create_store,
    store_factory_config_from_env,
    store_factory_config_to_dict,
)
from mnemosyne.store.postgres import POSTGRES_DATABASE_URL_ENV  # noqa: E402


@dataclass(frozen=True)
class R77PostgresAdapterSkeletonReportResult:
    output_root: Path
    files: dict[str, Path]
    default_store_type: str
    postgres_store_type: str
    default_ci_safe: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def _build_report() -> dict[str, Any]:
    default_config = store_factory_config_from_env({})
    default_store = create_store(default_config)
    default_capability = await default_store.get_store_capability_report()

    postgres_config = store_factory_config_from_env(
        {
            STORE_BACKEND_ENV: POSTGRES_BACKEND,
            POSTGRES_DATABASE_URL_ENV: "postgresql://user:secret@localhost:5432/mnemosyne",
        }
    )
    postgres_store = create_store(postgres_config)
    postgres_capability = await postgres_store.get_store_capability_report()

    return {
        "schema_version": "r77_postgres_adapter_skeleton_report.v1",
        "summary": {
            "default_backend": default_config.normalized_backend,
            "default_store_type": type(default_store).__name__,
            "postgres_backend": postgres_config.normalized_backend,
            "postgres_store_type": type(postgres_store).__name__,
            "postgres_configured": postgres_store.config.configured,
            "postgres_redacted_database_url": postgres_store.config.redacted_database_url,
            "default_ci_safe": True,
            "decision": "optional_postgres_adapter_skeleton_and_factory_established",
        },
        "environment": {
            "store_backend_env": STORE_BACKEND_ENV,
            "sqlite_path_env": SQLITE_PATH_ENV,
            "postgres_database_url_env": POSTGRES_DATABASE_URL_ENV,
        },
        "factory_configs": {
            "default": store_factory_config_to_dict(default_config),
            "postgres": store_factory_config_to_dict(postgres_config),
        },
        "capability_reports": {
            "default": store_capability_report_to_dict(default_capability),
            "postgres": store_capability_report_to_dict(postgres_capability),
        },
        "claims": {
            "postgres_adapter_skeleton_claimed": True,
            "postgres_configuration_boundary_claimed": True,
            "store_factory_claimed": True,
            "sqlite_default_claimed": True,
            "default_ci_postgres_free_claimed": True,
            "live_postgres_persistence_claimed": False,
            "postgres_live_conformance_claimed": False,
            "distributed_storage_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.7 provides the PostgreSQL adapter skeleton and store factory.",
            "R7.7 does not implement live PostgreSQL persistence.",
            "R7.7 does not claim live PostgreSQL conformance.",
            "Default CI remains SQLite-only.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.7 Optional PostgreSQL Adapter Skeleton Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Default backend: `{summary['default_backend']}`")
    lines.append(f"- Default store type: `{summary['default_store_type']}`")
    lines.append(f"- PostgreSQL backend: `{summary['postgres_backend']}`")
    lines.append(f"- PostgreSQL store type: `{summary['postgres_store_type']}`")
    lines.append(f"- PostgreSQL configured: {summary['postgres_configured']}")
    lines.append(f"- Default CI safe: {summary['default_ci_safe']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Environment")
    lines.append("")
    for key, value in report["environment"].items():
        lines.append(f"- {key}: `{value}`")
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


def run_r77_postgres_adapter_skeleton_report(
    output_root: str | Path | None = None,
) -> R77PostgresAdapterSkeletonReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = asyncio.run(_build_report())

    files = {
        "report_json": root / "reports" / "r77_postgres_adapter_skeleton_report.json",
        "report_markdown": root / "reports" / "r77_postgres_adapter_skeleton_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R77PostgresAdapterSkeletonReportResult(
        output_root=root,
        files=files,
        default_store_type=report["summary"]["default_store_type"],
        postgres_store_type=report["summary"]["postgres_store_type"],
        default_ci_safe=report["summary"]["default_ci_safe"],
    )


def main() -> None:
    result = run_r77_postgres_adapter_skeleton_report()
    print("R7.7 optional PostgreSQL adapter skeleton report")
    print(f"output_root: {result.output_root}")
    print(f"default_store_type: {result.default_store_type}")
    print(f"postgres_store_type: {result.postgres_store_type}")
    print(f"default_ci_safe: {result.default_ci_safe}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
