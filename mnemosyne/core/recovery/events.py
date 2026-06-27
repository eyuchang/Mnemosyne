from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


RECOVERY_EVENT_SCHEMA_ID = "core.recovery_event"
RECOVERY_EVENT_SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RecoveryEvent:
    """Durable append-only recovery lifecycle event.

    RecoveryEvent is the R7.2 substrate primitive. It records recovery lifecycle
    facts independently from benchmark scripts and prepares replay/idempotency
    work for later R7 commits.
    """

    event_id: str
    tenant_id: str
    recovery_id: str
    sequence_no: int
    event_type: str
    idempotency_key: str
    payload: dict[str, Any] = field(default_factory=dict)
    workflow_id: str | None = None
    causality_key: str | None = None
    created_at: datetime = field(default_factory=_now)
    schema_id: str = RECOVERY_EVENT_SCHEMA_ID
    schema_version: str = RECOVERY_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not self.recovery_id:
            raise ValueError("recovery_id is required")
        if self.sequence_no < 1:
            raise ValueError("sequence_no must be >= 1")
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.idempotency_key:
            raise ValueError("idempotency_key is required")


def recovery_event_to_dict(event: RecoveryEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "tenant_id": event.tenant_id,
        "workflow_id": event.workflow_id,
        "recovery_id": event.recovery_id,
        "sequence_no": event.sequence_no,
        "event_type": event.event_type,
        "idempotency_key": event.idempotency_key,
        "causality_key": event.causality_key,
        "payload": event.payload,
        "schema_id": event.schema_id,
        "schema_version": event.schema_version,
        "created_at": event.created_at.isoformat(),
    }


def recovery_event_from_dict(data: dict[str, Any]) -> RecoveryEvent:
    raw_created_at = data.get("created_at")
    created_at = (
        datetime.fromisoformat(raw_created_at)
        if isinstance(raw_created_at, str)
        else raw_created_at
    )

    return RecoveryEvent(
        event_id=data["event_id"],
        tenant_id=data["tenant_id"],
        workflow_id=data.get("workflow_id"),
        recovery_id=data["recovery_id"],
        sequence_no=int(data["sequence_no"]),
        event_type=data["event_type"],
        idempotency_key=data["idempotency_key"],
        causality_key=data.get("causality_key"),
        payload=dict(data.get("payload") or {}),
        schema_id=data.get("schema_id", RECOVERY_EVENT_SCHEMA_ID),
        schema_version=data.get("schema_version", RECOVERY_EVENT_SCHEMA_VERSION),
        created_at=created_at or _now(),
    )
