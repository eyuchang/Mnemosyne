import pytest

from mnemosyne.core.models import Command, ExternalEvent
from mnemosyne.runtime.local import LocalRuntimeDriver


@pytest.mark.asyncio
async def test_command_event_and_local_runtime(store):
    cmd = Command(
        command_id="cmd-1",
        tenant_id="tenant:runtime",
        actor_id="user:edward",
        command_type="submit_spec",
        payload={"workflow_id": "wf:1"},
        idempotency_key="idem-1",
        workflow_id="wf:1",
    )
    await store.append_command(cmd)
    event = ExternalEvent(
        event_id="evt-1",
        tenant_id="tenant:runtime",
        event_type="road_blocked",
        entity_refs={"ride": "ride:R001"},
        payload={"edge": "pickup-airport"},
        workflow_id="wf:1",
    )
    await store.append_event(event)
    assert await store.has_event("tenant:runtime", "evt-1")

    runtime = LocalRuntimeDriver()
    handle = await runtime.submit_workflow({"workflow_id": "wf:1"})
    assert handle.workflow_id == "wf:1"
    await runtime.signal_disruption("wf:1", event)
    status = await runtime.query_status("wf:1")
    assert status.status == "signaled"
    assert status.detail["events"] == ["evt-1"]
