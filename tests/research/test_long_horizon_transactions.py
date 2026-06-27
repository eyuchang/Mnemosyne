# File: tests/research/test_long_horizon_transactions.py
#
# Purpose:
#   Exercise a deterministic long-horizon CTL transaction history.
#
# Policy:
#   This test is marked long_horizon, so it is visible in the repository but
#   skipped by the default public test run unless explicitly selected.
#
# Run explicitly with:
#   python -m pytest -q -m long_horizon

from __future__ import annotations

import pytest

from mnemosyne.core.models import CommitBatch, OutboxIntent, TransitionCandidate


TENANT_ID = "tenant:long-horizon"
WORKFLOW_ID = "trip:long-horizon-001"
TOTAL_ENTITIES = 60


def make_hold_flight_batch(index: int) -> CommitBatch:
    itinerary_id = f"itinerary:LH{index:03d}"
    rid = f"lh-hold-flight-{index:03d}"

    return CommitBatch(
        batch_id=f"batch-lh-hold-flight-{index:03d}",
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
        tx_group_id=f"group-lh-hold-flight-{index:03d}",
        candidates=[
            TransitionCandidate(
                rid=rid,
                tenant_id=TENANT_ID,
                tx_group_id=f"group-lh-hold-flight-{index:03d}",
                workflow_id=WORKFLOW_ID,
                binding_id=f"binding:LH{index:03d}",
                eid=itinerary_id,
                fsm="ItineraryFSM",
                state_before="draft",
                state_after="flight_held",
                action_type="hold_flight",
                extension={
                    "attrs_after": {
                        "flight": f"UA{index:03d}",
                        "step": index,
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
        outbox_intents=[
            OutboxIntent(
                outbox_id=f"outbox-lh-hold-flight-{index:03d}",
                tenant_id=TENANT_ID,
                provider="airline",
                effect_type="hold_flight",
                payload={
                    "itinerary_id": itinerary_id,
                    "flight": f"UA{index:03d}",
                },
                provider_idempotency_key=f"airline:hold-flight:LH{index:03d}",
                workflow_id=WORKFLOW_ID,
                binding_id=f"binding:LH{index:03d}",
            )
        ],
    )


def make_hold_hotel_batch(index: int) -> CommitBatch:
    itinerary_id = f"itinerary:LH{index:03d}"
    flight_rid = f"lh-hold-flight-{index:03d}"

    return CommitBatch(
        batch_id=f"batch-lh-hold-hotel-{index:03d}",
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
        tx_group_id=f"group-lh-hold-hotel-{index:03d}",
        candidates=[
            TransitionCandidate(
                rid=f"lh-hold-hotel-{index:03d}",
                tenant_id=TENANT_ID,
                tx_group_id=f"group-lh-hold-hotel-{index:03d}",
                workflow_id=WORKFLOW_ID,
                binding_id=f"binding:LH{index:03d}",
                eid=itinerary_id,
                fsm="ItineraryFSM",
                state_before="flight_held",
                state_after="hotel_held",
                action_type="hold_hotel",
                dependencies=[flight_rid],
                extension={
                    "attrs_after": {
                        "hotel": f"Kyoto Inn {index:03d}",
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )


def make_cancel_batch(index: int) -> CommitBatch:
    itinerary_id = f"itinerary:LH{index:03d}"
    flight_rid = f"lh-hold-flight-{index:03d}"

    return CommitBatch(
        batch_id=f"batch-lh-cancel-{index:03d}",
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
        tx_group_id=f"group-lh-cancel-{index:03d}",
        candidates=[
            TransitionCandidate(
                rid=f"lh-cancel-{index:03d}",
                tenant_id=TENANT_ID,
                tx_group_id=f"group-lh-cancel-{index:03d}",
                workflow_id=WORKFLOW_ID,
                binding_id=f"binding:LH{index:03d}",
                eid=itinerary_id,
                fsm="ItineraryFSM",
                state_before="flight_held",
                state_after="cancelled",
                action_type="cancel",
                dependencies=[flight_rid],
                metadata={
                    "compensates": [flight_rid],
                },
                extension={
                    "attrs_after": {
                        "cancelled": True,
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )


async def validate_and_commit(batch: CommitBatch, store, validator) -> None:
    result = await validator.validate_batch(batch, store)

    assert result.ok, [error.code for error in result.errors]

    records = await validator.records_from_batch(batch, store)

    await store.commit_batch(batch, records)


def scalar(store, sql: str, params: tuple = ()):
    row = store.conn.execute(sql, params).fetchone()

    return row[0]


@pytest.mark.long_horizon
@pytest.mark.asyncio
async def test_long_horizon_ctl_history_preserves_memory_and_projects_current_truth(store, validator):
    cancelled_indexes = set()

    for index in range(1, TOTAL_ENTITIES + 1):
        hold_batch = make_hold_flight_batch(index)

        await validate_and_commit(hold_batch, store, validator)

        if index % 10 == 0:
            cancelled_indexes.add(index)
            await validate_and_commit(make_cancel_batch(index), store, validator)
        else:
            await validate_and_commit(make_hold_hotel_batch(index), store, validator)

    expected_records = TOTAL_ENTITIES * 2
    expected_outbox_rows = TOTAL_ENTITIES

    assert scalar(store, "SELECT COUNT(*) FROM ctl_records WHERE tenant_id=?", (TENANT_ID,)) == expected_records
    assert scalar(store, "SELECT COUNT(*) FROM outbox WHERE tenant_id=?", (TENANT_ID,)) == expected_outbox_rows

    local_positions = [
        row["local_log_position"]
        for row in store.conn.execute(
            """
            SELECT local_log_position
            FROM ctl_records
            WHERE tenant_id=? AND workflow_id=?
            ORDER BY log_position ASC
            """,
            (TENANT_ID, WORKFLOW_ID),
        ).fetchall()
    ]

    assert local_positions == list(range(1, expected_records + 1))

    for index in range(1, TOTAL_ENTITIES + 1):
        itinerary_id = f"itinerary:LH{index:03d}"
        flight_rid = f"lh-hold-flight-{index:03d}"
        view = await store.get_state_view(TENANT_ID, itinerary_id, "ItineraryFSM")

        if index in cancelled_indexes:
            cancel_rid = f"lh-cancel-{index:03d}"

            assert view.state == "cancelled"
            assert view.version == 2
            assert view.effective_records == [cancel_rid]
            assert not await store.is_effective(TENANT_ID, flight_rid)
            assert await store.is_effective(TENANT_ID, cancel_rid)
        else:
            hotel_rid = f"lh-hold-hotel-{index:03d}"

            assert view.state == "hotel_held"
            assert view.version == 2
            assert view.effective_records == [flight_rid, hotel_rid]
            assert await store.is_effective(TENANT_ID, flight_rid)
            assert await store.is_effective(TENANT_ID, hotel_rid)

    first_batch = make_hold_flight_batch(1)
    first_records = await validator.records_from_batch(first_batch, store)

    await store.commit_batch(first_batch, first_records)

    assert scalar(store, "SELECT COUNT(*) FROM ctl_records WHERE tenant_id=?", (TENANT_ID,)) == expected_records
    assert scalar(store, "SELECT COUNT(*) FROM outbox WHERE tenant_id=?", (TENANT_ID,)) == expected_outbox_rows