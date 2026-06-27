from __future__ import annotations

import asyncio
import json
import sys
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
from mnemosyne.core.recovery.replay import (  # noqa: E402
    recovery_replay_state_to_dict,
    replay_recovery_events,
)
from mnemosyne.store.sqlite.store import SQLiteStore  # noqa: E402


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class R73RecoveryReplayReportResult:
    output_root: Path
    files: dict[str, Path]
    replayed_event_count: int
    duplicate_event_count: int
    terminal_event_seen: bool


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
    recovery_id: str = "r73-recovery",
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant-r73",
        workflow_id="workflow-r73",
        recovery_id=recovery_id,
        sequence_no=sequence_no,
        event_type=event_type,
        idempotency_key=idempotency_key,
        causality_key=payload.get("commitment_id") if payload else None,
        payload=payload or {},
        created_at=BASE_TIME + timedelta(seconds=sequence_no),
    )


async def _build_report() -> dict[str, Any]:
    store = SQLiteStore()

    # Intentionally append out of sequence; replay must reconstruct order.
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="r73-event-2",
            sequence_no=2,
            event_type="proposal_package_created",
            idempotency_key="r73-idem-2",
            payload={"proposal_package_id": "pkg-r73"},
        ),
    )
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="r73-event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="r73-idem-1",
            payload={"commitment_id": "commitment-r73"},
        ),
    )
    await append_recovery_event(
        store=store,
        event=_event(
            event_id="r73-event-3",
            sequence_no=3,
            event_type="repair_admission_committed",
            idempotency_key="r73-idem-3",
            payload={"admission_id": "admission-r73"},
        ),
    )

    replay_result = await replay_recovery_events_from_store(
        store=store,
        tenant_id="tenant-r73",
        workflow_id="workflow-r73",
        recovery_id="r73-recovery",
    )

    original = _event(
        event_id="dup-event-1",
        sequence_no=1,
        event_type="commitment_fired",
        idempotency_key="dup-idem-1",
        payload={"commitment_id": "dup-commitment"},
        recovery_id="dup-recovery",
    )
    duplicate_event_id = _event(
        event_id="dup-event-1",
        sequence_no=2,
        event_type="commitment_fired",
        idempotency_key="dup-idem-2",
        payload={"commitment_id": "duplicate-event-id"},
        recovery_id="dup-recovery",
    )
    duplicate_idempotency_key = _event(
        event_id="dup-event-3",
        sequence_no=3,
        event_type="commitment_fired",
        idempotency_key="dup-idem-1",
        payload={"commitment_id": "duplicate-idempotency-key"},
        recovery_id="dup-recovery",
    )
    duplicate_state = replay_recovery_events(
        [original, duplicate_event_id, duplicate_idempotency_key]
    )["dup-recovery"]

    state = replay_result.states["r73-recovery"]

    return {
        "schema_version": "r73_recovery_replay_report.v1",
        "summary": {
            "tenant_id": replay_result.tenant_id,
            "workflow_id": replay_result.workflow_id,
            "recovery_count": replay_result.recovery_count,
            "replayed_event_count": replay_result.replayed_event_count,
            "duplicate_event_count": replay_result.duplicate_event_count,
            "last_sequence_no": state.last_sequence_no,
            "terminal_event_seen": state.terminal_event_seen,
            "deterministic_sequence_order": [
                event.event_id for event in state.events
            ],
            "duplicate_replay_tolerance_checked": True,
            "duplicate_replay_duplicate_count": duplicate_state.duplicate_event_count,
        },
        "api_replay": recovery_replay_api_result_to_dict(replay_result),
        "duplicate_replay": recovery_replay_state_to_dict(duplicate_state),
        "claims": {
            "durable_event_log_replay_claimed": True,
            "deterministic_replay_order_claimed": True,
            "idempotent_duplicate_tolerance_claimed": True,
            "checkpoint_projection_claimed": True,
            "postgres_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.3 replays durable recovery events into deterministic recovery state.",
            "R7.3 does not yet replay domain CTL mutation after crash.",
            "R7.3 does not claim PostgreSQL, Kubernetes, Temporal, or production-runtime execution.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.3 Recovery Replay and Idempotency Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Tenant: `{summary['tenant_id']}`")
    lines.append(f"- Workflow: `{summary['workflow_id']}`")
    lines.append(f"- Recovery count: {summary['recovery_count']}")
    lines.append(f"- Replayed event count: {summary['replayed_event_count']}")
    lines.append(f"- Duplicate event count: {summary['duplicate_event_count']}")
    lines.append(f"- Last sequence number: {summary['last_sequence_no']}")
    lines.append(f"- Terminal event seen: {summary['terminal_event_seen']}")
    lines.append(f"- Duplicate replay tolerance checked: {summary['duplicate_replay_tolerance_checked']}")
    lines.append(f"- Duplicate replay duplicate count: {summary['duplicate_replay_duplicate_count']}")
    lines.append("")
    lines.append("## Deterministic Replay Order")
    lines.append("")
    for event_id in summary["deterministic_sequence_order"]:
        lines.append(f"- `{event_id}`")
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


def run_r73_recovery_replay_report(
    output_root: str | Path | None = None,
) -> R73RecoveryReplayReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = asyncio.run(_build_report())

    files = {
        "report_json": root / "reports" / "r73_recovery_replay_report.json",
        "report_markdown": root / "reports" / "r73_recovery_replay_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R73RecoveryReplayReportResult(
        output_root=root,
        files=files,
        replayed_event_count=report["summary"]["replayed_event_count"],
        duplicate_event_count=report["summary"]["duplicate_replay_duplicate_count"],
        terminal_event_seen=report["summary"]["terminal_event_seen"],
    )


def main() -> None:
    result = run_r73_recovery_replay_report()
    print("R7.3 recovery replay and idempotency report")
    print(f"output_root: {result.output_root}")
    print(f"replayed_event_count: {result.replayed_event_count}")
    print(f"duplicate_event_count: {result.duplicate_event_count}")
    print(f"terminal_event_seen: {result.terminal_event_seen}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
