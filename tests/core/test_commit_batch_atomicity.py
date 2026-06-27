from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import CTLRecord, CommitBatch, OutboxIntent
from mnemosyne.store.sqlite import SQLiteStore


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_record(
    *,
    rid: str,
    version: int,
    eid: str = "itinerary:T-atomic",
    fsm: str = "ItineraryFSM",
    state_before: str = "none",
    state_after: str = "flight_held",
    tenant_id: str = "tenant:atomic",
    tx_group_id: str = "tx:atomic",
    workflow_id: str = "trip:T-atomic",
    binding_id: str = "binding:T-atomic",
) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        op_id=rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        binding_id=binding_id,
        eid=eid,
        fsm=fsm,
        version=version,
        state_before=state_before,
        state_after=state_after,
        action_type="transition",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"flight": "UA123"},
        app_id="travel",
        app_version="1.0",
        schema_id="travel.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="test.validator",
        validator_version="1.0",
        timestamp=FIXED_TIME,
    )


def make_outbox_intent() -> OutboxIntent:
    return OutboxIntent(
        outbox_id="outbox-atomic-001",
        tenant_id="tenant:atomic",
        provider="email",
        effect_type="send_email",
        payload={
            "to": "customer@example.com",
            "subject": "Flight held",
        },
        provider_idempotency_key="email:trip:T-atomic:flight-held",
        workflow_id="trip:T-atomic",
        binding_id="binding:T-atomic",
        created_at=FIXED_TIME,
    )


@pytest.mark.asyncio
async def test_commit_batch_rolls_back_all_ctl_records_on_later_failure():
    store = SQLiteStore()

    first_record = make_record(
        rid="atomic-rid-001",
        version=1,
        state_before="none",
        state_after="flight_held",
    )

    invalid_second_record = make_record(
        rid="atomic-rid-002",
        version=1,
        state_before="flight_held",
        state_after="hotel_held",
    )

    batch = CommitBatch(
        batch_id="batch-atomic-001",
        tenant_id="tenant:atomic",
        workflow_id="trip:T-atomic",
        tx_group_id="tx:atomic",
        candidates=[],
        outbox_intents=[],
    )

    with pytest.raises(ValueError, match="bad version"):
        await store.commit_batch(batch, [first_record, invalid_second_record])

    ctl_rows = store.conn.execute(
        """
        SELECT *
        FROM ctl_records
        WHERE tenant_id = ?
          AND tx_group_id = ?
        """,
        ("tenant:atomic", "tx:atomic"),
    ).fetchall()

    projection_rows = store.conn.execute(
        """
        SELECT *
        FROM entity_projection
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        """,
        ("tenant:atomic", "itinerary:T-atomic", "ItineraryFSM"),
    ).fetchall()

    effective_rows = store.conn.execute(
        """
        SELECT *
        FROM effective_record_index
        WHERE tenant_id = ?
        """,
        ("tenant:atomic",),
    ).fetchall()

    assert ctl_rows == []
    assert projection_rows == []
    assert effective_rows == []


@pytest.mark.asyncio
async def test_commit_batch_rolls_back_outbox_when_ctl_commit_fails():
    store = SQLiteStore()

    first_record = make_record(
        rid="atomic-rid-003",
        version=1,
        state_before="none",
        state_after="flight_held",
    )

    invalid_second_record = make_record(
        rid="atomic-rid-004",
        version=1,
        state_before="flight_held",
        state_after="hotel_held",
    )

    batch = CommitBatch(
        batch_id="batch-atomic-002",
        tenant_id="tenant:atomic",
        workflow_id="trip:T-atomic",
        tx_group_id="tx:atomic",
        candidates=[],
        outbox_intents=[make_outbox_intent()],
    )

    with pytest.raises(ValueError, match="bad version"):
        await store.commit_batch(batch, [first_record, invalid_second_record])

    ctl_rows = store.conn.execute(
        """
        SELECT *
        FROM ctl_records
        WHERE tenant_id = ?
          AND tx_group_id = ?
        """,
        ("tenant:atomic", "tx:atomic"),
    ).fetchall()

    outbox_rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE tenant_id = ?
          AND provider_idempotency_key = ?
        """,
        ("tenant:atomic", "email:trip:T-atomic:flight-held"),
    ).fetchall()

    projection_rows = store.conn.execute(
        """
        SELECT *
        FROM entity_projection
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        """,
        ("tenant:atomic", "itinerary:T-atomic", "ItineraryFSM"),
    ).fetchall()

    assert ctl_rows == []
    assert outbox_rows == []
    assert projection_rows == []