from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

from mnemosyne.core.recovery.events import RecoveryEvent  # noqa: E402
from mnemosyne.core.recovery.replay import replay_recovery_events  # noqa: E402
from mnemosyne.core.store_capabilities import store_capability_report_to_dict  # noqa: E402
from mnemosyne.core.store_conformance import (  # noqa: E402
    RecoveryStoreConformanceCase,
    observe_recovery_store_conformance,
    recovery_store_conformance_observation_to_dict,
)
from mnemosyne.store.postgres import (  # noqa: E402
    POSTGRES_DATABASE_URL_ENV,
    POSTGRES_SCHEMA_STATEMENTS,
    PostgresStore,
    PostgresStoreConfig,
)


class FakePostgresCursor:
    def __init__(self, connection: "FakePostgresConnection") -> None:
        self.connection = connection
        self._one: dict[str, Any] | None = None
        self._many: list[dict[str, Any]] = []

    def __enter__(self) -> "FakePostgresCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(sql.split()).lower()
        params = params or ()

        self._one = None
        self._many = []

        if normalized.startswith("create table") or normalized.startswith("create index"):
            return

        if normalized.startswith("insert into store_schema_metadata"):
            self.connection.schema_metadata = {
                "schema_id": params[0],
                "schema_version": params[1],
                "store_type": params[2],
            }
            return

        if normalized.startswith("select schema_version from store_schema_metadata"):
            self._one = {"schema_version": self.connection.schema_metadata["schema_version"]}
            return

        if normalized.startswith("select event_id") and "event_id = %s or idempotency_key = %s" in normalized:
            tenant_id, event_id, idempotency_key, _preferred_event_id = params
            matches = [
                row
                for row in self.connection.recovery_events
                if row["tenant_id"] == tenant_id
                and (row["event_id"] == event_id or row["idempotency_key"] == idempotency_key)
            ]
            matches.sort(
                key=lambda row: (
                    0 if row["event_id"] == event_id else 1,
                    row["sequence_no"],
                    row["event_id"],
                )
            )
            self._one = matches[0] if matches else None
            return

        if normalized.startswith("insert into recovery_events"):
            self.connection.recovery_events.append(
                {
                    "event_id": params[0],
                    "tenant_id": params[1],
                    "workflow_id": params[2],
                    "recovery_id": params[3],
                    "sequence_no": params[4],
                    "event_type": params[5],
                    "idempotency_key": params[6],
                    "causality_key": params[7],
                    "payload": params[8],
                    "schema_id": params[9],
                    "schema_version": params[10],
                    "created_at": params[11],
                }
            )
            return

        if normalized.startswith("select event_id") and "from recovery_events" in normalized:
            tenant_id = params[0]
            workflow_id = None
            recovery_id = None
            event_type = None
            index = 1

            if "workflow_id = %s" in normalized:
                workflow_id = params[index]
                index += 1
            if "recovery_id = %s" in normalized:
                recovery_id = params[index]
                index += 1
            if "event_type = %s" in normalized:
                event_type = params[index]

            rows = [
                row
                for row in self.connection.recovery_events
                if row["tenant_id"] == tenant_id
                and (workflow_id is None or row["workflow_id"] == workflow_id)
                and (recovery_id is None or row["recovery_id"] == recovery_id)
                and (event_type is None or row["event_type"] == event_type)
            ]
            rows.sort(key=lambda row: (row["recovery_id"], row["sequence_no"], row["event_id"]))
            self._many = rows
            return

        raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self) -> dict[str, Any] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._many)


class FakePostgresConnection:
    def __init__(self) -> None:
        self.schema_metadata = {
            "schema_id": "mnemosyne.store.sqlite",
            "schema_version": "1.0",
            "store_type": "PostgresStore",
        }
        self.recovery_events: list[dict[str, Any]] = []
        self.commit_count = 0

    def cursor(self) -> FakePostgresCursor:
        return FakePostgresCursor(self)

    def commit(self) -> None:
        self.commit_count += 1


@dataclass(frozen=True)
class R78PostgresLiveAdapterReportResult:
    output_root: Path
    files: dict[str, Path]
    adapter_event_count: int
    conformance_passed: bool
    default_ci_safe: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _event(event_id: str, sequence_no: int, idempotency_key: str) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant-r78",
        workflow_id="workflow-r78",
        recovery_id="recovery-r78",
        sequence_no=sequence_no,
        event_type="commitment_fired",
        idempotency_key=idempotency_key,
        payload={"event_id": event_id},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


async def _build_report() -> dict[str, Any]:
    connection = FakePostgresConnection()
    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_factory=lambda: connection,
    )

    capability = await store.get_store_capability_report()
    schema_version = await store.get_store_schema_version()

    await store.append_recovery_event(_event("r78-event-2", 2, "r78-idem-2"))
    await store.append_recovery_event(_event("r78-event-1", 1, "r78-idem-1"))
    duplicate = await store.append_recovery_event(_event("r78-event-dup", 3, "r78-idem-1"))

    events = await store.list_recovery_events(
        "tenant-r78",
        workflow_id="workflow-r78",
        recovery_id="recovery-r78",
    )

    replay_state = replay_recovery_events(events)["recovery-r78"]

    conformance_connection = FakePostgresConnection()
    conformance_store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_factory=lambda: conformance_connection,
    )
    conformance = await observe_recovery_store_conformance(
        conformance_store,
        RecoveryStoreConformanceCase(
            store_name="PostgresStore",
            expects_restart_persistence=True,
        ),
    )

    event_ids = [event.event_id for event in events]
    replay_ids = [event.event_id for event in replay_state.events]

    return {
        "schema_version": "r78_postgres_live_adapter_report.v1",
        "summary": {
            "postgres_database_url_env": POSTGRES_DATABASE_URL_ENV,
            "schema_version": schema_version,
            "event_ids": event_ids,
            "replay_event_ids": replay_ids,
            "duplicate_result_event_id": duplicate.event_id,
            "adapter_event_count": len(events),
            "conformance_passed": conformance.passed,
            "default_ci_safe": True,
            "decision": "opt_in_postgres_recovery_event_adapter_established",
        },
        "capability_report": store_capability_report_to_dict(capability),
        "conformance_observation": recovery_store_conformance_observation_to_dict(conformance),
        "schema_statement_count": len(POSTGRES_SCHEMA_STATEMENTS),
        "claims": {
            "postgres_recovery_event_adapter_claimed": True,
            "postgres_schema_initialization_claimed": True,
            "postgres_event_append_claimed": True,
            "postgres_event_list_claimed": True,
            "postgres_idempotent_retry_claimed": True,
            "postgres_conformance_fake_connection_claimed": True,
            "live_postgres_env_opt_in_claimed": True,
            "default_ci_postgres_free_claimed": True,
            "real_postgres_service_required_in_default_ci": False,
            "distributed_storage_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.8 implements the PostgreSQL recovery-event adapter surface.",
            "Default CI uses fake connection tests and does not require a PostgreSQL service.",
            "Real live PostgreSQL conformance remains gated by MNEMOSYNE_POSTGRES_DATABASE_URL.",
            "R7.8 does not claim Kubernetes, Temporal, or production-runtime recovery.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.8 PostgreSQL Live Adapter Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- PostgreSQL env: `{summary['postgres_database_url_env']}`")
    lines.append(f"- Schema version: `{summary['schema_version']}`")
    lines.append(f"- Event ids: {summary['event_ids']}")
    lines.append(f"- Replay event ids: {summary['replay_event_ids']}")
    lines.append(f"- Duplicate result event id: `{summary['duplicate_result_event_id']}`")
    lines.append(f"- Adapter event count: {summary['adapter_event_count']}")
    lines.append(f"- Conformance passed: {summary['conformance_passed']}")
    lines.append(f"- Default CI safe: {summary['default_ci_safe']}")
    lines.append(f"- Decision: `{summary['decision']}`")
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


def run_r78_postgres_live_adapter_report(
    output_root: str | Path | None = None,
) -> R78PostgresLiveAdapterReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = asyncio.run(_build_report())

    files = {
        "report_json": root / "reports" / "r78_postgres_live_adapter_report.json",
        "report_markdown": root / "reports" / "r78_postgres_live_adapter_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R78PostgresLiveAdapterReportResult(
        output_root=root,
        files=files,
        adapter_event_count=report["summary"]["adapter_event_count"],
        conformance_passed=report["summary"]["conformance_passed"],
        default_ci_safe=report["summary"]["default_ci_safe"],
    )


def main() -> None:
    result = run_r78_postgres_live_adapter_report()
    print("R7.8 PostgreSQL live adapter report")
    print(f"output_root: {result.output_root}")
    print(f"adapter_event_count: {result.adapter_event_count}")
    print(f"conformance_passed: {result.conformance_passed}")
    print(f"default_ci_safe: {result.default_ci_safe}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
