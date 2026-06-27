from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from mnemosyne.core.protocols.recovery_store import require_recovery_store
from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.recovery.replay import replay_recovery_events
from mnemosyne.core.store_capabilities import (
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
)


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class RecoveryStoreConformanceCase:
    store_name: str
    expected_schema_id: str = STORE_SCHEMA_ID
    expected_schema_version: str = STORE_SCHEMA_VERSION
    expects_restart_persistence: bool = False
    live_dependency_required: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecoveryStoreConformanceObservation:
    case: RecoveryStoreConformanceCase
    checks: dict[str, bool]
    details: dict[str, Any]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def _event(
    *,
    event_id: str,
    sequence_no: int,
    event_type: str,
    idempotency_key: str,
    tenant_id: str = "tenant-conformance",
    workflow_id: str = "workflow-conformance",
    recovery_id: str = "recovery-conformance",
    payload: dict[str, Any] | None = None,
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        sequence_no=sequence_no,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload or {},
        created_at=BASE_TIME + timedelta(seconds=sequence_no),
    )


def _event_id(value: Any) -> str | None:
    if isinstance(value, RecoveryEvent):
        return value.event_id

    for attr in ("event", "recovery_event", "stored_event"):
        nested = getattr(value, attr, None)
        if isinstance(nested, RecoveryEvent):
            return nested.event_id
        nested_event_id = getattr(nested, "event_id", None)
        if nested_event_id is not None:
            return str(nested_event_id)

    event_id = getattr(value, "event_id", None)
    return str(event_id) if event_id is not None else None


async def observe_recovery_store_conformance(
    store: Any,
    case: RecoveryStoreConformanceCase,
) -> RecoveryStoreConformanceObservation:
    store = require_recovery_store(store)

    capability_report = await store.get_store_capability_report()
    schema_version = await store.get_store_schema_version()

    await store.append_recovery_event(
        _event(
            event_id="conformance-event-2",
            sequence_no=2,
            event_type="proposal_package_created",
            idempotency_key="conformance-idem-2",
            payload={"proposal_package_id": "pkg-conformance"},
        )
    )
    await store.append_recovery_event(
        _event(
            event_id="conformance-event-1",
            sequence_no=1,
            event_type="commitment_fired",
            idempotency_key="conformance-idem-1",
            payload={"commitment_id": "commitment-conformance"},
        )
    )

    duplicate_result = await store.append_recovery_event(
        _event(
            event_id="conformance-event-duplicate",
            sequence_no=3,
            event_type="commitment_fired",
            idempotency_key="conformance-idem-1",
            payload={"commitment_id": "duplicate-conformance"},
        )
    )

    events = await store.list_recovery_events(
        "tenant-conformance",
        workflow_id="workflow-conformance",
        recovery_id="recovery-conformance",
    )

    replay_states = replay_recovery_events(events)
    replay_state = replay_states.get("recovery-conformance")

    event_ids = [event.event_id for event in events]
    replay_event_ids = (
        [event.event_id for event in replay_state.events]
        if replay_state is not None
        else []
    )

    checks = {
        "schema_id_matches": capability_report.schema_id == case.expected_schema_id,
        "schema_version_matches": schema_version == case.expected_schema_version,
        "capability_reports_durable_events": capability_report.durable_recovery_events,
        "capability_reports_idempotency": capability_report.idempotent_recovery_events,
        "capability_reports_replay_order": capability_report.deterministic_recovery_replay_order,
        "restart_persistence_expectation_matches": (
            capability_report.supports_restart_persistence
            == case.expects_restart_persistence
        ),
        "deterministic_list_order": event_ids == [
            "conformance-event-1",
            "conformance-event-2",
        ],
        "deterministic_replay_order": replay_event_ids == [
            "conformance-event-1",
            "conformance-event-2",
        ],
        "idempotent_duplicate_retry": (
            _event_id(duplicate_result) == "conformance-event-1"
            and len(events) == 2
        ),
    }

    details = {
        "store_type": capability_report.store_type,
        "schema_id": capability_report.schema_id,
        "schema_version": schema_version,
        "supports_restart_persistence": capability_report.supports_restart_persistence,
        "supports_postgres_conformance_target": capability_report.supports_postgres_conformance_target,
        "event_ids": event_ids,
        "replay_event_ids": replay_event_ids,
        "duplicate_result_event_id": _event_id(duplicate_result),
    }

    return RecoveryStoreConformanceObservation(
        case=case,
        checks=checks,
        details=details,
    )


def recovery_store_conformance_observation_to_dict(
    observation: RecoveryStoreConformanceObservation,
) -> dict[str, Any]:
    return {
        "case": {
            "store_name": observation.case.store_name,
            "expected_schema_id": observation.case.expected_schema_id,
            "expected_schema_version": observation.case.expected_schema_version,
            "expects_restart_persistence": observation.case.expects_restart_persistence,
            "live_dependency_required": observation.case.live_dependency_required,
            "notes": list(observation.case.notes),
        },
        "passed": observation.passed,
        "checks": dict(observation.checks),
        "details": dict(observation.details),
    }
