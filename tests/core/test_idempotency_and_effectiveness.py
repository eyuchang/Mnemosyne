import pytest

from mnemosyne.apps.travel import TravelApp
from mnemosyne.core.models import CommitBatch, TransitionCandidate


@pytest.mark.asyncio
async def test_commit_batch_is_idempotent_by_rid(store, validator):
    app = TravelApp()
    batch = app.example_commit_batches("tenant:idempotency")[0]
    result = await validator.validate_batch(batch, store)
    assert result.ok
    records = await validator.records_from_batch(batch, store)
    first = await store.commit_batch(batch, records)
    second = await store.commit_batch(batch, records)
    assert first[0].rid == second[0].rid
    view = await store.get_state_view("tenant:idempotency", "itinerary:T001", "ItineraryFSM")
    assert view.version == 1


@pytest.mark.asyncio
async def test_compensated_dependency_is_not_effective(store, validator):
    app = TravelApp()
    tenant_id = "tenant:deps"
    batch = app.example_commit_batches(tenant_id)[0]
    result = await validator.validate_batch(batch, store)
    assert result.ok
    records = await validator.records_from_batch(batch, store)
    await store.commit_batch(batch, records)

    # Append a compensating/superseding transition that marks tv-001 ineffective.
    comp_batch = CommitBatch(
        batch_id="b-comp",
        tenant_id=tenant_id,
        workflow_id="trip:T001",
        tx_group_id="g-comp",
        candidates=[
            TransitionCandidate(
                rid="tv-c001",
                tenant_id=tenant_id,
                tx_group_id="g-comp",
                workflow_id="trip:T001",
                binding_id="binding:T001",
                eid="itinerary:T001",
                fsm="ItineraryFSM",
                state_before="flight_held",
                state_after="cancelled",
                action_type="cancel",
                metadata={"compensates": ["tv-001"]},
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )
    result = await validator.validate_batch(comp_batch, store)
    assert result.ok
    await store.commit_batch(comp_batch, await validator.records_from_batch(comp_batch, store))
    assert not await store.is_effective(tenant_id, "tv-001")

    bad_batch = app.example_commit_batches(tenant_id)[1]
    result = await validator.validate_batch(bad_batch, store)
    assert not result.ok
    assert "DEPENDENCY_NOT_EFFECTIVE" in [e.code for e in result.errors]
