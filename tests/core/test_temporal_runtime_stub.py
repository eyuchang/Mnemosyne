# File: tests/core/test_temporal_runtime_stub.py
#
# Purpose:
#   Verify the Temporal runtime adapter stub.
#
# Stage:
#   Stage 1.1.4 checks two cases:
#
#   1. temporalio is not installed:
#        TemporalRuntimeDriver methods should raise RuntimeError with a helpful
#        optional-extra install message.
#
#   2. temporalio is installed:
#        TemporalRuntimeDriver methods should raise NotImplementedError because
#        real Temporal workflow integration has not been implemented yet.
#
# Rule:
#   Temporal remains orchestration only. CTL/store remains domain truth.

import inspect
from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import ExternalEvent
from mnemosyne.runtime.temporal import TemporalRuntimeDriver, is_temporal_sdk_available


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_external_event() -> ExternalEvent:
    return ExternalEvent(
        event_id="evt-temporal-stub-001",
        tenant_id="tenant:temporal-stub",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:T400",
            "driver": "driver:joe",
        },
        payload={
            "location": "Stanford",
        },
        workflow_id="ride-workflow:T400",
        binding_id="binding:ride:T400",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:T400:driver-arrived",
        timestamp=FIXED_TIME,
    )


def expected_temporal_stub_exception() -> type[Exception]:
    if is_temporal_sdk_available():
        return NotImplementedError
    return RuntimeError


def expected_temporal_stub_message(method_name: str) -> str:
    if is_temporal_sdk_available():
        return method_name
    return "Temporal SDK is not installed"


def test_temporal_runtime_driver_can_be_constructed_without_temporal_dependency():
    driver = TemporalRuntimeDriver(namespace="default", task_queue="mnemosyne-stage1")

    assert driver.namespace == "default"
    assert driver.task_queue == "mnemosyne-stage1"


def test_temporal_runtime_driver_exposes_required_async_methods():
    required_async_methods = [
        "submit_workflow",
        "signal_disruption",
        "query_status",
    ]

    for method_name in required_async_methods:
        method = getattr(TemporalRuntimeDriver, method_name, None)

        assert method is not None, f"TemporalRuntimeDriver is missing {method_name}(...)"
        assert inspect.iscoroutinefunction(method), (
            f"TemporalRuntimeDriver.{method_name}(...) must be async"
        )


@pytest.mark.asyncio
async def test_temporal_runtime_driver_submit_workflow_guarded_stub():
    driver = TemporalRuntimeDriver()

    with pytest.raises(
        expected_temporal_stub_exception(),
        match=expected_temporal_stub_message("submit_workflow"),
    ):
        await driver.submit_workflow(
            {
                "workflow_id": "ride-workflow:T400",
                "tenant_id": "tenant:temporal-stub",
                "app_id": "rideshare",
                "entity_id": "ride:T400",
            }
        )


@pytest.mark.asyncio
async def test_temporal_runtime_driver_signal_disruption_guarded_stub():
    driver = TemporalRuntimeDriver()
    event = make_external_event()

    with pytest.raises(
        expected_temporal_stub_exception(),
        match=expected_temporal_stub_message("signal_disruption"),
    ):
        await driver.signal_disruption("ride-workflow:T400", event)


@pytest.mark.asyncio
async def test_temporal_runtime_driver_query_status_guarded_stub():
    driver = TemporalRuntimeDriver()

    with pytest.raises(
        expected_temporal_stub_exception(),
        match=expected_temporal_stub_message("query_status"),
    ):
        await driver.query_status("ride-workflow:T400")