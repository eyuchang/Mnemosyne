# File: tests/core/test_op_id_idempotency.py
#
# Purpose:
#   Regression test for Claude Review A finding IM-2.
#
# Contract:
#   op_id is the logical operation idempotency key.
#   Replaying the same op_id with a different rid must return the original
#   committed CTL record instead of inserting a new record or raising.

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import CTLRecord, CommitBatch, OutboxIntent
from mnemosyne.store.sqlite import SQLiteStore


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_batch(batch_id: str, outbox_id: str) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id="tenant:op-id",
        workflow_id="workflow:op-id",
        tx_group_id="group:op-id",
        candidates=[],
        outbox_intents=[
            OutboxIntent(
                outbox_id=outbox_id,
                tenant_id="tenant:op-id",
                provider="airline",
                effect_type="hold_flight",
                payload={
                    "itinerary_id": "itinerary:op-id",
                    "flight": "UA100",
                },
                provider_idempotency_key="airline:hold-flight:op-id-001",
                workflow_id="workflow:op-id",
                binding_id="binding:op-id",
                created_at=FIXED_TIME,
            )
        ],
    )


def make_record(rid: str, op_id: str) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        op_id=op_id,
        tenant_id="tenant:op-id",
        tx_group_id="group:op-id",
        workflow_id="workflow:op-id",
        binding_id="binding:op-id",
        eid="itinerary:op-id",
        fsm="ItineraryFSM",
        version=1,
        state_before="draft",
        state_after="flight_held",
        action_type="hold_flight",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={
            "attrs_after": {
                "flight": "UA100",
            }
        },
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


def scalar(store: SQLiteStore, sql: str, params: tuple = ()) -> int:
    row = store.conn.execute(sql, params).fetchone()

    return int(row[0])


@pytest.mark.asyncio
async def test_same_op_id_with_different_rid_returns_existing_record_without_new_commit():
    store = SQLiteStore()

    first_record = make_record(
        rid="rid-original",
        op_id="op-hold-flight-001",
    )

    first_result = await store.commit_batch(
        make_batch(
            batch_id="batch-op-id-original",
            outbox_id="outbox-op-id-original",
        ),
        [first_record],
    )

    assert len(first_result) == 1
    assert first_result[0].rid == "rid-original"
    assert first_result[0].op_id == "op-hold-flight-001"

    replay_record = make_record(
        rid="rid-replayed-different",
        op_id="op-hold-flight-001",
    )

    replay_result = await store.commit_batch(
        make_batch(
            batch_id="batch-op-id-replayed",
            outbox_id="outbox-op-id-replayed",
        ),
        [replay_record],
    )

    assert len(replay_result) == 1
    assert replay_result[0].rid == "rid-original"
    assert replay_result[0].op_id == "op-hold-flight-001"

    assert scalar(
        store,
        "SELECT COUNT(*) FROM ctl_records WHERE tenant_id=?",
        ("tenant:op-id",),
    ) == 1

    assert scalar(
        store,
        "SELECT COUNT(*) FROM outbox WHERE tenant_id=?",
        ("tenant:op-id",),
    ) == 1

    view = await store.get_state_view(
        "tenant:op-id",
        "itinerary:op-id",
        "ItineraryFSM",
    )

    assert view.state == "flight_held"
    assert view.version == 1
    assert view.effective_records == ["rid-original"]