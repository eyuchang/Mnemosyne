from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.recovery.replay import replay_recovery_events
from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresRecoveryEventConflictError,
    PostgresStore,
    PostgresStoreConfig,
)


DATABASE_URL = os.environ.get(POSTGRES_DATABASE_URL_ENV)


pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason=f"{POSTGRES_DATABASE_URL_ENV} is not set",
)


def _event(
    *,
    tenant_id: str,
    workflow_id: str,
    recovery_id: str,
    event_id: str,
    sequence_no: int,
    idempotency_key: str,
) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
        sequence_no=sequence_no,
        event_type="commitment_fired",
        idempotency_key=idempotency_key,
        causality_key=f"cause-{event_id}",
        payload={
            "event_id": event_id,
            "sequence_no": sequence_no,
            "source": "r79-live-postgres-database-url-conformance",
        },
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_live_postgres_database_url_append_dedup_conflict_list_replay_reopen():
    try:
        import psycopg  # noqa: F401
    except ImportError as exc:
        raise AssertionError(
            f"{POSTGRES_DATABASE_URL_ENV} is set, but optional dependency "
            "`psycopg` is not installed"
        ) from exc

    tenant_id = f"tenant-r79-{uuid.uuid4()}"
    workflow_id = f"workflow-r79-{uuid.uuid4()}"
    recovery_id = f"recovery-r79-{uuid.uuid4()}"

    store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))

    later = await store.append_recovery_event(
        _event(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
            event_id="r79-event-2",
            sequence_no=2,
            idempotency_key="r79-idem-2",
        )
    )
    earlier = await store.append_recovery_event(
        _event(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
            event_id="r79-event-1",
            sequence_no=1,
            idempotency_key="r79-idem-1",
        )
    )

    duplicate = await store.append_recovery_event(
        _event(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            recovery_id=recovery_id,
            event_id="r79-event-duplicate",
            sequence_no=3,
            idempotency_key="r79-idem-1",
        )
    )

    assert later.event_id == "r79-event-2"
    assert earlier.event_id == "r79-event-1"
    assert duplicate.event_id == "r79-event-1"

    with pytest.raises(PostgresRecoveryEventConflictError):
        await store.append_recovery_event(
            _event(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                recovery_id=recovery_id,
                event_id="r79-event-sequence-conflict",
                sequence_no=1,
                idempotency_key="r79-idem-sequence-conflict",
            )
        )

    listed = await store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
    )

    assert [event.event_id for event in listed] == ["r79-event-1", "r79-event-2"]
    assert [event.payload["event_id"] for event in listed] == [
        "r79-event-1",
        "r79-event-2",
    ]

    replay_state = replay_recovery_events(listed)[recovery_id]
    assert [event.event_id for event in replay_state.events] == [
        "r79-event-1",
        "r79-event-2",
    ]

    reopened_store = PostgresStore(PostgresStoreConfig(database_url=DATABASE_URL))
    reopened = await reopened_store.list_recovery_events(
        tenant_id,
        workflow_id=workflow_id,
        recovery_id=recovery_id,
    )

    assert [event.event_id for event in reopened] == ["r79-event-1", "r79-event-2"]

    capability = await reopened_store.get_store_capability_report()

    assert capability.store_type == "PostgresStore"
    assert capability.durable_recovery_events is True
    assert capability.idempotent_recovery_events is True
    assert capability.deterministic_recovery_replay_order is True
    assert capability.supports_restart_persistence is True
    assert capability.supports_postgres_conformance_target is True
