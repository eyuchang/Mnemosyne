import pytest

from mnemosyne.apps.travel import TravelApp


@pytest.mark.asyncio
async def test_commit_batch_updates_projection_synchronously(store, validator):
    app = TravelApp()
    batch = app.example_commit_batches("tenant:sync")[0]
    result = await validator.validate_batch(batch, store)
    assert result.ok
    records = await validator.records_from_batch(batch, store)
    await store.commit_batch(batch, records)
    candidate = batch.candidates[0]
    view = await store.get_state_view(candidate.tenant_id, candidate.eid, candidate.fsm)
    assert view.state == "flight_held"
    assert view.attrs["flight"] == "UA123"
    assert view.effective_records == ["tv-001"]
