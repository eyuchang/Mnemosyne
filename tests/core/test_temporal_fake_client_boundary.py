# File: tests/core/test_temporal_fake_client_boundary.py
#
# Purpose:
#   Verify the Stage 1.3 fake Temporal client boundary.
#
# Contract:
#   TemporalRuntimeDriver may orchestrate through an injected client without
#   requiring temporalio or a Temporal server.
#
# Source-of-truth rule:
#   The fake Temporal client owns only orchestration status. It does not write
#   CTL, mutate Store state, or own StateView truth.

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import ExternalEvent
from mnemosyne.runtime.temporal import FakeTemporalClient, TemporalRuntimeDriver


FIXED_TIME = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


def make_external_event() -> ExternalEvent:
    return ExternalEvent(
        event_id="evt-temporal-fake-001",
        tenant_id="tenant:temporal-fake",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:TF001",
            "driver": "driver:fake",
        },
        payload={
            "location": "Stanford",
        },
        workflow_id="workflow:temporal-fake-001",
        binding_id="binding:temporal-fake-001",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:TF001:driver-arrived",
        timestamp=FIXED_TIME,
    )


@pytest.mark.asyncio
async def test_temporal_runtime_driver_uses_injected_fake_client_without_temporal_sdk():
    client = FakeTemporalClient()
    runtime = TemporalRuntimeDriver(
        namespace="default",
        task_queue="mnemosyne-stage1",
        client=client,
    )

    handle = await runtime.submit_workflow(
        {
            "workflow_id": "workflow:temporal-fake-001",
            "tenant_id": "tenant:temporal-fake",
            "app_id": "rideshare",
            "entity_id": "ride:TF001",
        }
    )

    assert handle.workflow_id == "workflow:temporal-fake-001"
    assert handle.run_id == "fake-run:workflow:temporal-fake-001"
    assert handle.status == "submitted"
    
    submitted_status = await runtime.query_status("workflow:temporal-fake-001")

    assert submitted_status.workflow_id == "workflow:temporal-fake-001"
    assert submitted_status.status == "submitted"
    assert submitted_status.detail["runtime"] == "fake_temporal"
    assert submitted_status.detail["spec"]["tenant_id"] == "tenant:temporal-fake"
    assert submitted_status.detail["events"] == []

    await runtime.signal_disruption(
        "workflow:temporal-fake-001",
        make_external_event(),
    )

    signaled_status = await runtime.query_status("workflow:temporal-fake-001")

    assert signaled_status.workflow_id == "workflow:temporal-fake-001"
    assert signaled_status.status == "signaled"
    assert signaled_status.detail["events"] == ["evt-temporal-fake-001"]


@pytest.mark.asyncio
async def test_fake_temporal_client_does_not_expose_domain_truth_interfaces():
    client = FakeTemporalClient()

    assert not hasattr(client, "commit_batch")
    assert not hasattr(client, "get_state_view")
    assert not hasattr(client, "append_event")
    assert not hasattr(client, "enqueue_outbox")