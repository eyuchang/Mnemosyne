from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mnemosyne.core.commitments.models import (
    ActiveCommitment,
    CommitmentEvent,
    CommitmentEventType,
)

ACTIVE_COMMITMENT_EXTENSION_KIND = "mnemosyne.active_commitment_event"
ACTIVE_COMMITMENT_EXTENSION_VERSION = "1.0"


def commitment_to_dict(commitment: ActiveCommitment) -> dict[str, Any]:
    return asdict(commitment)


def commitment_from_dict(data: dict[str, Any]) -> ActiveCommitment:
    return ActiveCommitment(**data)


def event_to_extension(event: CommitmentEvent) -> dict[str, Any]:
    payload = dict(event.payload)

    commitment = payload.get("commitment")
    if isinstance(commitment, ActiveCommitment):
        payload["commitment"] = commitment_to_dict(commitment)

    return {
        "kind": ACTIVE_COMMITMENT_EXTENSION_KIND,
        "version": ACTIVE_COMMITMENT_EXTENSION_VERSION,
        "event_type": event.event_type.value,
        "commitment_id": event.commitment_id,
        "record_id": event.record_id,
        "workflow_id": event.workflow_id,
        "payload": payload,
    }


def is_commitment_extension(extension: dict[str, Any]) -> bool:
    return extension.get("kind") == ACTIVE_COMMITMENT_EXTENSION_KIND


def event_from_extension(extension: dict[str, Any]) -> CommitmentEvent:
    if not is_commitment_extension(extension):
        raise ValueError("extension is not an active commitment event")

    payload = dict(extension.get("payload") or {})

    if "commitment" in payload and isinstance(payload["commitment"], dict):
        payload["commitment"] = commitment_from_dict(payload["commitment"])

    return CommitmentEvent(
        event_type=CommitmentEventType(extension["event_type"]),
        commitment_id=extension["commitment_id"],
        payload=payload,
        record_id=extension.get("record_id"),
        workflow_id=extension.get("workflow_id"),
    )


def extract_commitment_events_from_ctl_records(records: list[Any]) -> list[CommitmentEvent]:
    events: list[CommitmentEvent] = []

    for record in records:
        extension = getattr(record, "extension", None)
        if isinstance(extension, dict) and is_commitment_extension(extension):
            events.append(event_from_extension(extension))

    return events
