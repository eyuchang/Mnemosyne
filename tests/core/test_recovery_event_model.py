from __future__ import annotations

import pytest

from mnemosyne.core.recovery.events import (
    RECOVERY_EVENT_SCHEMA_ID,
    RECOVERY_EVENT_SCHEMA_VERSION,
    RecoveryEvent,
    recovery_event_from_dict,
    recovery_event_to_dict,
)


def test_recovery_event_round_trips_through_dict():
    event = RecoveryEvent(
        event_id="event-1",
        tenant_id="tenant",
        workflow_id="workflow",
        recovery_id="recovery",
        sequence_no=1,
        event_type="commitment_fired",
        idempotency_key="idem-1",
        causality_key="commitment-1",
        payload={"commitment_id": "commitment-1"},
    )

    restored = recovery_event_from_dict(recovery_event_to_dict(event))

    assert restored == event
    assert restored.schema_id == RECOVERY_EVENT_SCHEMA_ID
    assert restored.schema_version == RECOVERY_EVENT_SCHEMA_VERSION


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("event_id", ""),
        ("tenant_id", ""),
        ("recovery_id", ""),
        ("event_type", ""),
        ("idempotency_key", ""),
    ],
)
def test_recovery_event_requires_identity_fields(field_name: str, value: str):
    kwargs = {
        "event_id": "event-1",
        "tenant_id": "tenant",
        "recovery_id": "recovery",
        "sequence_no": 1,
        "event_type": "commitment_fired",
        "idempotency_key": "idem-1",
    }
    kwargs[field_name] = value

    with pytest.raises(ValueError):
        RecoveryEvent(**kwargs)


def test_recovery_event_sequence_must_be_positive():
    with pytest.raises(ValueError):
        RecoveryEvent(
            event_id="event-1",
            tenant_id="tenant",
            recovery_id="recovery",
            sequence_no=0,
            event_type="commitment_fired",
            idempotency_key="idem-1",
        )
