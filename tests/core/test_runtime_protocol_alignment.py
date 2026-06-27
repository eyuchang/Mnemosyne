import inspect
from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import ExternalEvent
from mnemosyne.core.protocols import RuntimeDriver
from mnemosyne.runtime.local import LocalRuntimeDriver


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This file starts Stage 1.0.1: runtime protocol alignment.
#
# Stage 0 proved the local durable-memory loop:
#
#     Command
#     -> inbox
#     -> event log
#     -> CTL
#     -> StateView
#     -> outbox
#
# Stage 1 prepares for Temporal.
#
# Before adding Temporal, we first verify that the current LocalRuntimeDriver
# exposes the same runtime API shape that a future TemporalRuntimeDriver must
# implement.
#
# Runtime principle:
#
#     Runtime engines orchestrate workflows.
#     Runtime engines are not domain truth.
#
# Domain truth remains in:
#
#     CTL
#     event log
#     StateView
#     outbox
#
# RuntimeDriver API:
#
#     submit_workflow(...)
#         Register or start a workflow with the runtime.
#
#     signal_disruption(...)
#         Send an external event/signal into an existing workflow.
#
#     query_status(...)
#         Ask the runtime for orchestration status.
#
# These are Python methods. They are not terminal commands.
# ---------------------------------------------------------------------------


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_external_event() -> ExternalEvent:
    """Create a runtime signal event for testing LocalRuntimeDriver.

    API role:
        ExternalEvent represents an observed external fact.

    In this runtime test:
        The event is signaled into LocalRuntimeDriver.

    Important:
        Signaling the runtime does not by itself create domain truth.
        Domain truth still requires CTL/store commits in other tests.
    """
    return ExternalEvent(
        event_id="evt-runtime-protocol-001",
        tenant_id="tenant:runtime-protocol",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:R300",
            "driver": "driver:joe",
        },
        payload={
            "location": "Stanford",
        },
        workflow_id="ride-workflow:R300",
        binding_id="binding:ride:R300",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:R300:driver-arrived",
        timestamp=FIXED_TIME,
    )


def test_runtime_driver_protocol_exposes_required_methods():
    """Verify the formal RuntimeDriver protocol declares the required APIs.

    This test checks the protocol itself.

    Why this matters:
        A future TemporalRuntimeDriver should implement the same public methods
        as LocalRuntimeDriver.

    Required protocol methods:
        submit_workflow(...)
        signal_disruption(...)
        query_status(...)
    """
    assert hasattr(RuntimeDriver, "submit_workflow")
    assert hasattr(RuntimeDriver, "signal_disruption")
    assert hasattr(RuntimeDriver, "query_status")


def test_local_runtime_driver_exposes_required_async_methods():
    """Verify LocalRuntimeDriver exposes the runtime API as async methods.

    This is a human-readable contract test.

    It confirms that LocalRuntimeDriver provides:

        submit_workflow(...)
        signal_disruption(...)
        query_status(...)

    and that each one is async.

    This is important because runtime orchestration will involve async systems
    such as Temporal in later stages.
    """
    required_async_methods = [
        "submit_workflow",
        "signal_disruption",
        "query_status",
    ]

    for method_name in required_async_methods:
        method = getattr(LocalRuntimeDriver, method_name, None)

        assert method is not None, f"LocalRuntimeDriver is missing {method_name}(...)"
        assert inspect.iscoroutinefunction(method), (
            f"LocalRuntimeDriver.{method_name}(...) must be async"
        )


@pytest.mark.asyncio
async def test_local_runtime_driver_submit_signal_and_query_flow():
    """Verify LocalRuntimeDriver behavior through its public API.

    Runtime APIs under test:
        submit_workflow(...)
        signal_disruption(...)
        query_status(...)

    Scenario:
        1. Submit a workflow.
        2. Query status.
        3. Signal an external event into the workflow.
        4. Query status again.

    Expected:
        - submit_workflow returns a workflow handle.
        - query_status returns submitted status after submission.
        - signal_disruption records the event id in runtime detail.
        - query_status returns signaled status after the signal.

    Important:
        This test checks runtime orchestration status only.
        It does not claim that runtime status is domain truth.
    """
    runtime = LocalRuntimeDriver()
    event = make_external_event()

    handle = await runtime.submit_workflow(
        {
            "workflow_id": "ride-workflow:R300",
            "tenant_id": "tenant:runtime-protocol",
            "app_id": "rideshare",
            "entity_id": "ride:R300",
        }
    )

    assert handle.workflow_id == "ride-workflow:R300"
    assert handle.status == "submitted"

    submitted_status = await runtime.query_status("ride-workflow:R300")

    assert submitted_status.workflow_id == "ride-workflow:R300"
    assert submitted_status.status == "submitted"
    assert submitted_status.detail["spec"]["tenant_id"] == "tenant:runtime-protocol"
    assert submitted_status.detail["spec"]["app_id"] == "rideshare"
    assert submitted_status.detail["spec"]["entity_id"] == "ride:R300"

    await runtime.signal_disruption("ride-workflow:R300", event)

    signaled_status = await runtime.query_status("ride-workflow:R300")

    assert signaled_status.workflow_id == "ride-workflow:R300"
    assert signaled_status.status == "signaled"
    assert signaled_status.detail["events"] == ["evt-runtime-protocol-001"]
