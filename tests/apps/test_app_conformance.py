import pytest

from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.apps.rideshare import RideshareApp
from mnemosyne.apps.travel import TravelApp


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [RideshareApp(), TravelApp(), JSSPApp()])
async def test_apps_run_through_same_core_without_core_changes(app, store, validator):
    tenant_id = "tenant:test"
    for batch in app.example_commit_batches(tenant_id):
        result = await validator.validate_batch(batch, store)
        assert result.ok, [e.code for e in result.errors]
        records = await validator.records_from_batch(batch, store)
        await store.commit_batch(batch, records)

    last = app.example_commit_batches(tenant_id)[-1].candidates[-1]
    view = await store.get_state_view(tenant_id, last.eid, last.fsm)
    assert view.state == last.state_after
    assert view.version >= 1
