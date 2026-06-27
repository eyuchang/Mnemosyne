# File: tests/core/test_runtime_parity.py
#
# Purpose:
#   Define shared runtime behavior for runtime drivers.
#
# Current status:
#   LocalRuntimeDriver is functional and must satisfy the parity flow.
#   TemporalRuntimeDriver is still a guarded stub.
#
# Important:
#   If temporalio is not installed, TemporalRuntimeDriver raises RuntimeError.
#   If temporalio is installed, TemporalRuntimeDriver raises NotImplementedError
#   because real Temporal integration is still pending.

from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import ExternalEvent
from mnemosyne.runtime.local import LocalRuntimeDriver
from mnemosyne.runtime.temporal import TemporalRuntimeDriver, is_temporal_sdk_available


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_external_event() -> ExternalEvent:
    return ExternalEvent(
        event_id="evt-runtime-parity-001",
        tenant_id="tenant:runtime-parity",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:R500",
            "driver": "driver:joe",
        },
        payload={
            "location": "Stanford",
        },
        workflow_id="ride-workflow:R500",
        binding_id="binding:ride:R500",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:R500:driver-arrived",
        timestamp=FIXED_TIME,
    )


async def exercise_runtime_submit_signal_query_flow(runtime) -> None:
    event = make_external_event()

    handle = await runtime.submit_workflow(
        {
            "workflow_id": "ride-workflow:R500",
            "tenant_id": "tenant:runtime-parity",
            "app_id": "rideshare",
            "entity_id": "ride:R500",
        }
    )

    assert handle.workflow_id == "ride-workflow:R500"
    assert handle.status == "submitted"

    submitted_status = await runtime.query_status("ride-workflow:R500")

    assert submitted_status.workflow_id == "ride-workflow:R500"
    assert submitted_status.status == "submitted"
    assert submitted_status.detail["spec"]["tenant_id"] == "tenant:runtime-parity"
    assert submitted_status.detail["spec"]["app_id"] == "rideshare"
    assert submitted_status.detail["spec"]["entity_id"] == "ride:R500"

    await runtime.signal_disruption("ride-workflow:R500", event)

    signaled_status = await runtime.query_status("ride-workflow:R500")

    assert signaled_status.workflow_id == "ride-workflow:R500"
    assert signaled_status.status == "signaled"
    assert signaled_status.detail["events"] == ["evt-runtime-parity-001"]


def expected_temporal_stub_exception() -> type[Exception]:
    if is_temporal_sdk_available():
        return NotImplementedError
    return RuntimeError


def expected_temporal_stub_message() -> str:
    if is_temporal_sdk_available():
        return "submit_workflow"
    return "Temporal SDK is not installed"


@pytest.mark.asyncio
async def test_local_runtime_driver_satisfies_runtime_parity_flow():
    runtime = LocalRuntimeDriver()

    await exercise_runtime_submit_signal_query_flow(runtime)


@pytest.mark.asyncio
async def test_temporal_runtime_driver_is_excluded_from_behavioral_parity_until_implemented():
    runtime = TemporalRuntimeDriver(namespace="default", task_queue="mnemosyne-stage1")

    with pytest.raises(expected_temporal_stub_exception(), match=expected_temporal_stub_message()):
        await runtime.submit_workflow(
            {
                "workflow_id": "ride-workflow:R500",
                "tenant_id": "tenant:runtime-parity",
                "app_id": "rideshare",
                "entity_id": "ride:R500",
            }
        )