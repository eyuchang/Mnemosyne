# File: tests/core/test_cross_entity_compensation_projection.py
#
# Purpose:
#   Regression test for Claude Review A finding BL-1.
#
# Bug:
#   A record on entity B can compensate a record on entity A.
#   The effective_record_index correctly marks entity A's record ineffective,
#   but entity A's StateView projection must also be refreshed.
#
# Contract:
#   StateView must reflect current effective truth, even when effectiveness
#   changes are caused by a different entity.

from __future__ import annotations

import pytest

from mnemosyne.core.models import CommitBatch, TransitionCandidate


async def validate_and_commit(batch: CommitBatch, store, validator) -> None:
    result = await validator.validate_batch(batch, store)

    assert result.ok, [error.code for error in result.errors]

    records = await validator.records_from_batch(batch, store)

    await store.commit_batch(batch, records)


@pytest.mark.asyncio
async def test_cross_entity_compensation_refreshes_compensated_entity_projection(store, validator):
    tenant_id = "tenant:cross-entity-compensation"
    workflow_id = "workflow:cross-entity-compensation"

    entity_a_batch = CommitBatch(
        batch_id="batch-cross-entity-a",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        tx_group_id="group-cross-entity-a",
        candidates=[
            TransitionCandidate(
                rid="ce-a1",
                tenant_id=tenant_id,
                tx_group_id="group-cross-entity-a",
                workflow_id=workflow_id,
                binding_id="binding:entity-a",
                eid="itinerary:entity-a",
                fsm="ItineraryFSM",
                state_before="draft",
                state_after="flight_held",
                action_type="hold_flight",
                extension={
                    "attrs_after": {
                        "flight": "UA100",
                        "entity": "A",
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )

    await validate_and_commit(entity_a_batch, store, validator)

    entity_a_before = await store.get_state_view(
        tenant_id,
        "itinerary:entity-a",
        "ItineraryFSM",
    )

    assert entity_a_before.state == "flight_held"
    assert entity_a_before.version == 1
    assert entity_a_before.effective_records == ["ce-a1"]
    assert await store.is_effective(tenant_id, "ce-a1")

    entity_b_batch = CommitBatch(
        batch_id="batch-cross-entity-b",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        tx_group_id="group-cross-entity-b",
        candidates=[
            TransitionCandidate(
                rid="ce-b1",
                tenant_id=tenant_id,
                tx_group_id="group-cross-entity-b",
                workflow_id=workflow_id,
                binding_id="binding:entity-b",
                eid="itinerary:entity-b",
                fsm="ItineraryFSM",
                state_before="draft",
                state_after="flight_held",
                action_type="hold_flight",
                metadata={
                    "compensates": ["ce-a1"],
                },
                extension={
                    "attrs_after": {
                        "flight": "UA200",
                        "entity": "B",
                        "compensates_entity_a": True,
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )

    await validate_and_commit(entity_b_batch, store, validator)

    assert not await store.is_effective(tenant_id, "ce-a1")
    assert await store.is_effective(tenant_id, "ce-b1")

    entity_a_after = await store.get_state_view(
        tenant_id,
        "itinerary:entity-a",
        "ItineraryFSM",
    )

    assert entity_a_after.state is None
    assert entity_a_after.version == 0
    assert entity_a_after.effective_records == []

    entity_b_after = await store.get_state_view(
        tenant_id,
        "itinerary:entity-b",
        "ItineraryFSM",
    )

    assert entity_b_after.state == "flight_held"
    assert entity_b_after.version == 1
    assert entity_b_after.effective_records == ["ce-b1"]