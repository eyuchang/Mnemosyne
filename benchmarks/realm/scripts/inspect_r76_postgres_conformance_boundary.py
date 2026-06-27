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

from mnemosyne.core.store_capabilities import (  # noqa: E402
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
)
from mnemosyne.store.sqlite.store import SQLiteStore  # noqa: E402


CORE_RECOVERY_TABLES = [
    "store_schema_metadata",
    "recovery_events",
]

CORE_RUNTIME_TABLES = [
    "commands",
    "events",
    "inbox_messages",
    "outbox_messages",
    "commitments",
    "proposal_packages",
]


@dataclass(frozen=True)
class R76PostgresConformanceBoundaryResult:
    output_root: Path
    files: dict[str, Path]
    sqlite_table_count: int
    required_postgres_table_count: int
    decision: str


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sqlite_schema() -> dict[str, Any]:
    store = SQLiteStore()
    rows = store.conn.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'index')
          AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()

    objects = [
        {
            "type": row["type"],
            "name": row["name"],
            "table": row["tbl_name"],
            "sql": row["sql"],
        }
        for row in rows
    ]

    tables = sorted(row["name"] for row in rows if row["type"] == "table")
    indexes = sorted(row["name"] for row in rows if row["type"] == "index")

    columns: dict[str, list[dict[str, Any]]] = {}
    for table in tables:
        pragma_rows = store.conn.execute(f"PRAGMA table_info({table})").fetchall()
        columns[table] = [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"]),
            }
            for row in pragma_rows
        ]

    return {
        "tables": tables,
        "indexes": indexes,
        "objects": objects,
        "columns": columns,
    }


def _postgres_conformance_requirements(sqlite_schema: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []

    for table in CORE_RECOVERY_TABLES:
        requirements.append(
            {
                "id": f"postgres_table_{table}",
                "category": "table",
                "required": True,
                "sqlite_present": table in sqlite_schema["tables"],
                "description": f"PostgreSQL store must provide `{table}` with equivalent logical fields.",
            }
        )

    requirements.extend(
        [
            {
                "id": "postgres_recovery_events_unique_event_id",
                "category": "constraint",
                "required": True,
                "sqlite_present": True,
                "description": "Preserve unique `(tenant_id, event_id)` for durable idempotency.",
            },
            {
                "id": "postgres_recovery_events_unique_idempotency_key",
                "category": "constraint",
                "required": True,
                "sqlite_present": True,
                "description": "Preserve unique `(tenant_id, idempotency_key)` for retry safety.",
            },
            {
                "id": "postgres_recovery_events_unique_sequence_no",
                "category": "constraint",
                "required": True,
                "sqlite_present": True,
                "description": "Preserve unique `(tenant_id, recovery_id, sequence_no)` for deterministic replay.",
            },
            {
                "id": "postgres_recovery_events_ordering",
                "category": "query_semantics",
                "required": True,
                "sqlite_present": True,
                "description": "List recovery events deterministically by recovery id, sequence number, and event id.",
            },
            {
                "id": "postgres_recovery_events_json_payload",
                "category": "type_semantics",
                "required": True,
                "sqlite_present": True,
                "description": "Payloads must round-trip JSON-compatible data without changing replay semantics.",
            },
            {
                "id": "postgres_schema_metadata",
                "category": "migration",
                "required": True,
                "sqlite_present": "store_schema_metadata" in sqlite_schema["tables"],
                "description": "Store schema id/version must be queryable and stable across restart.",
            },
            {
                "id": "postgres_capability_report",
                "category": "capability",
                "required": True,
                "sqlite_present": True,
                "description": "PostgreSQL store must report durable recovery, idempotency, replay, and restart persistence capabilities.",
            },
            {
                "id": "postgres_default_ci_skip",
                "category": "ci_boundary",
                "required": True,
                "sqlite_present": True,
                "description": "Live PostgreSQL conformance tests must be skipped unless an explicit database URL is supplied.",
            },
        ]
    )

    return requirements


def _postgres_schema_draft() -> list[str]:
    return [
        "CREATE TABLE store_schema_metadata (schema_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL, store_type TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL);",
        "CREATE TABLE recovery_events (event_id TEXT NOT NULL, tenant_id TEXT NOT NULL, workflow_id TEXT, recovery_id TEXT NOT NULL, sequence_no INTEGER NOT NULL, event_type TEXT NOT NULL, idempotency_key TEXT NOT NULL, causality_key TEXT, payload JSONB NOT NULL, schema_id TEXT NOT NULL, schema_version TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (tenant_id, event_id), UNIQUE (tenant_id, idempotency_key), UNIQUE (tenant_id, recovery_id, sequence_no));",
        "CREATE INDEX idx_recovery_events_recovery ON recovery_events (tenant_id, recovery_id, sequence_no);",
        "CREATE INDEX idx_recovery_events_workflow ON recovery_events (tenant_id, workflow_id, created_at);",
    ]


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.6 PostgreSQL Conformance Boundary Inspection")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Store schema id: `{summary['store_schema_id']}`")
    lines.append(f"- Store schema version: `{summary['store_schema_version']}`")
    lines.append(f"- SQLite table count: {summary['sqlite_table_count']}")
    lines.append(f"- Required PostgreSQL table count: {summary['required_postgres_table_count']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Required PostgreSQL Tables")
    lines.append("")
    for table in report["required_postgres_tables"]:
        lines.append(f"- `{table}`")
    lines.append("")
    lines.append("## Conformance Requirements")
    lines.append("")
    for item in report["postgres_conformance_requirements"]:
        lines.append(f"- `{item['id']}`: {item['description']}")
    lines.append("")
    lines.append("## PostgreSQL Schema Draft")
    lines.append("")
    lines.append("```sql")
    for stmt in report["postgres_schema_draft"]:
        lines.append(stmt)
    lines.append("```")
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


def inspect_r76_postgres_conformance_boundary(
    output_root: str | Path | None = None,
) -> R76PostgresConformanceBoundaryResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    sqlite_schema = _sqlite_schema()
    requirements = _postgres_conformance_requirements(sqlite_schema)

    required_postgres_tables = CORE_RECOVERY_TABLES

    report = {
        "schema_version": "r76_postgres_conformance_boundary_inspection.v1",
        "summary": {
            "store_schema_id": STORE_SCHEMA_ID,
            "store_schema_version": STORE_SCHEMA_VERSION,
            "sqlite_table_count": len(sqlite_schema["tables"]),
            "sqlite_index_count": len(sqlite_schema["indexes"]),
            "required_postgres_table_count": len(required_postgres_tables),
            "decision": "postgres_conformance_boundary_ready_for_contract_tests",
        },
        "sqlite_schema": sqlite_schema,
        "current_runtime_tables": CORE_RUNTIME_TABLES,
        "required_postgres_tables": required_postgres_tables,
        "postgres_conformance_requirements": requirements,
        "postgres_schema_draft": _postgres_schema_draft(),
        "claims": {
            "postgres_conformance_boundary_defined": True,
            "postgres_schema_draft_defined": True,
            "sqlite_remains_default_store": True,
            "live_postgres_required": False,
            "postgres_adapter_implemented": False,
            "postgres_live_conformance_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.6 Commit 1 defines the PostgreSQL conformance boundary only.",
            "No live PostgreSQL adapter is implemented in this commit.",
            "SQLite remains the default store and test target.",
            "Live PostgreSQL tests should remain skipped unless an explicit database URL is supplied.",
        ],
    }

    files = {
        "report_json": root / "reports" / "r76_postgres_conformance_boundary_inspection.json",
        "report_markdown": root / "reports" / "r76_postgres_conformance_boundary_inspection.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R76PostgresConformanceBoundaryResult(
        output_root=root,
        files=files,
        sqlite_table_count=report["summary"]["sqlite_table_count"],
        required_postgres_table_count=report["summary"]["required_postgres_table_count"],
        decision=report["summary"]["decision"],
    )


def main() -> None:
    result = inspect_r76_postgres_conformance_boundary()
    print("R7.6 PostgreSQL conformance boundary inspection")
    print(f"output_root: {result.output_root}")
    print(f"sqlite_table_count: {result.sqlite_table_count}")
    print(f"required_postgres_table_count: {result.required_postgres_table_count}")
    print(f"decision: {result.decision}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
