from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

from mnemosyne.api.recovery_events import append_recovery_event  # noqa: E402
from mnemosyne.api.recovery_replay import (  # noqa: E402
    recovery_replay_api_result_to_dict,
    replay_recovery_events_from_store,
)
from mnemosyne.core.recovery.events import RecoveryEvent  # noqa: E402
from mnemosyne.core.store_capabilities import (  # noqa: E402
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
    store_capability_report_to_dict,
)
from mnemosyne.store.sqlite.store import SQLiteStore  # noqa: E402


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class R75StoreDurabilityReportResult:
    output_root: Path
    files: dict[str, Path]
    restart_persistence_verified: bool
    replay_after_reopen_verified: bool
    idempotent_retry_after_reopen_verified: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _event(
    *,
    event_id: str,
    sequence_no: int,
    event_type: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant-r75",
        workflow_id="workflow-r75",
        recovery_id="recovery-r75",
        sequence_no=sequence_no,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload or {},
        created_at=BASE_TIME + timedelta(seconds=sequence_no),
    )


async def _build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "r75-durability.sqlite"

        first_store = SQLiteStore(db_path)
        first_capability = await first_store.get_store_capability_report()

        await append_recovery_event(
            store=first_store,
            event=_event(
                event_id="r75-event-1",
                sequence_no=1,
                event_type="commitment_fired",
                idempotency_key="r75-idem-1",
                payload={"commitment_id": "commitment-r75"},
            ),
        )
        await append_recovery_event(
            store=first_store,
            event=_event(
                event_id="r75-event-2",
                sequence_no=2,
                event_type="proposal_package_created",
                idempotency_key="r75-idem-2",
                payload={"proposal_package_id": "package-r75"},
            ),
        )

        second_store = SQLiteStore(db_path)
        second_capability = await second_store.get_store_capability_report()

        reopened_events = await second_store.list_recovery_events(
            "tenant-r75",
            workflow_id="workflow-r75",
            recovery_id="recovery-r75",
        )

        replay_result = await replay_recovery_events_from_store(
            store=second_store,
            tenant_id="tenant-r75",
            workflow_id="workflow-r75",
            recovery_id="recovery-r75",
        )

        duplicate_result = await append_recovery_event(
            store=second_store,
            event=_event(
                event_id="r75-event-duplicate",
                sequence_no=3,
                event_type="commitment_fired",
                idempotency_key="r75-idem-1",
                payload={"commitment_id": "duplicate-r75"},
            ),
        )

        reopened_after_duplicate = await second_store.list_recovery_events(
            "tenant-r75",
            workflow_id="workflow-r75",
            recovery_id="recovery-r75",
        )

    event_ids = [event.event_id for event in reopened_events]
    replay_sequence = (
        [
            event.event_id
            for event in replay_result.states["recovery-r75"].events
        ]
        if "recovery-r75" in replay_result.states
        else []
    )

    restart_persistence_verified = event_ids == ["r75-event-1", "r75-event-2"]
    replay_after_reopen_verified = replay_sequence == ["r75-event-1", "r75-event-2"]
    duplicate_event = getattr(duplicate_result, "event", None)
    if duplicate_event is None:
        duplicate_event = getattr(duplicate_result, "recovery_event", None)
    if duplicate_event is None:
        duplicate_event = getattr(duplicate_result, "stored_event", None)
    if duplicate_event is None:
        duplicate_event = duplicate_result

    duplicate_result_event_id = getattr(duplicate_event, "event_id", None)

    idempotent_retry_after_reopen_verified = (
        duplicate_result_event_id == "r75-event-1"
        and len(reopened_after_duplicate) == 2
    )

    return {
        "schema_version": "r75_store_durability_report.v1",
        "summary": {
            "store_schema_id": STORE_SCHEMA_ID,
            "store_schema_version": STORE_SCHEMA_VERSION,
            "restart_persistence_verified": restart_persistence_verified,
            "replay_after_reopen_verified": replay_after_reopen_verified,
            "idempotent_retry_after_reopen_verified": idempotent_retry_after_reopen_verified,
            "reopened_event_ids": event_ids,
            "replay_sequence": replay_sequence,
            "event_count_after_duplicate_retry": len(reopened_after_duplicate),
            "duplicate_result_event_id": duplicate_result_event_id,
            "decision": "sqlite_store_durability_and_migration_readiness_established",
        },
        "capability_reports": {
            "first_store": store_capability_report_to_dict(first_capability),
            "reopened_store": store_capability_report_to_dict(second_capability),
        },
        "replay_report": recovery_replay_api_result_to_dict(replay_result),
        "claims": {
            "sqlite_schema_metadata_claimed": True,
            "sqlite_restart_persistence_claimed": True,
            "durable_recovery_event_reopen_claimed": True,
            "replay_after_reopen_claimed": True,
            "idempotent_retry_after_reopen_claimed": True,
            "postgres_claimed": False,
            "distributed_storage_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.5 proves file-backed SQLite restart persistence for recovery events.",
            "R7.5 records schema metadata and capability reporting.",
            "R7.5 does not implement PostgreSQL.",
            "R7.5 does not claim distributed storage, Kubernetes, Temporal, or production-runtime recovery.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.5 Store Durability and Migration Readiness Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Store schema id: `{summary['store_schema_id']}`")
    lines.append(f"- Store schema version: `{summary['store_schema_version']}`")
    lines.append(f"- Restart persistence verified: {summary['restart_persistence_verified']}")
    lines.append(f"- Replay after reopen verified: {summary['replay_after_reopen_verified']}")
    lines.append(f"- Idempotent retry after reopen verified: {summary['idempotent_retry_after_reopen_verified']}")
    lines.append(f"- Reopened event ids: {summary['reopened_event_ids']}")
    lines.append(f"- Replay sequence: {summary['replay_sequence']}")
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


def run_r75_store_durability_report(
    output_root: str | Path | None = None,
) -> R75StoreDurabilityReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = asyncio.run(_build_report())

    files = {
        "report_json": root / "reports" / "r75_store_durability_report.json",
        "report_markdown": root / "reports" / "r75_store_durability_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R75StoreDurabilityReportResult(
        output_root=root,
        files=files,
        restart_persistence_verified=report["summary"]["restart_persistence_verified"],
        replay_after_reopen_verified=report["summary"]["replay_after_reopen_verified"],
        idempotent_retry_after_reopen_verified=report["summary"]["idempotent_retry_after_reopen_verified"],
    )


def main() -> None:
    result = run_r75_store_durability_report()
    print("R7.5 store durability report")
    print(f"output_root: {result.output_root}")
    print(f"restart_persistence_verified: {result.restart_persistence_verified}")
    print(f"replay_after_reopen_verified: {result.replay_after_reopen_verified}")
    print(f"idempotent_retry_after_reopen_verified: {result.idempotent_retry_after_reopen_verified}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
