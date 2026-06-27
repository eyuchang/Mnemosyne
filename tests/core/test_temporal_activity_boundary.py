# File: tests/core/test_temporal_activity_boundary.py
#
# Purpose:
#   Verify the Stage 1.4 Temporal activity boundary contract.
#
# Contract:
#   Runtime/workflow code orchestrates only.
#   Durable Store/CTL writes happen through activity-like boundaries.
#
# Source-of-truth rule:
#   CTL/store remains domain truth. Temporal remains orchestration.

from __future__ import annotations

import pytest

from mnemosyne.core.models import CommitBatch, TransitionCandidate
from mnemosyne.runtime.temporal import (
    FakeTemporalClient,
    TemporalRuntimeDriver,
    validate_and_commit_batch_activity,
)


def make_activity_batch() -> CommitBatch:
    return CommitBatch(
        batch_id="batch-temporal-activity-001",
        tenant_id="tenant:temporal-activity",
        workflow_id="workflow:temporal-activity-001",
        tx_group_id="group:temporal-activity-001",
        candidates=[
            TransitionCandidate(
                rid="ta-rid-001",
                tenant_id="tenant:temporal-activity",
                tx_group_id="group:temporal-activity-001",
                workflow_id="workflow:temporal-activity-001",
                binding_id="binding:temporal-activity-001",
                eid="itinerary:TA001",
                fsm="ItineraryFSM",
                state_before="draft",
                state_after="flight_held",
                action_type="hold_flight",
                extension={
                    "attrs_after": {
                        "flight": "UA314",
                        "source": "temporal_activity_boundary_test",
                    }
                },
                app_id="travel",
                schema_id="travel.transition",
            )
        ],
    )


@pytest.mark.asyncio
async def test_temporal_activity_boundary_validates_commits_and_returns_stateview(store, validator):
    batch = make_activity_batch()

    result = await validate_and_commit_batch_activity(
        batch=batch,
        store=store,
        validator=validator,
    )

    assert result.batch_id == "batch-temporal-activity-001"
    assert result.tenant_id == "tenant:temporal-activity"
    assert result.workflow_id == "workflow:temporal-activity-001"
    assert result.committed_rids == ["ta-rid-001"]

    assert len(result.state_views) == 1

    view = result.state_views[0]

    assert view.tenant_id == "tenant:temporal-activity"
    assert view.eid == "itinerary:TA001"
    assert view.fsm == "ItineraryFSM"
    assert view.state == "flight_held"
    assert view.version == 1
    assert view.effective_records == ["ta-rid-001"]

    direct_view = await store.get_state_view(
        "tenant:temporal-activity",
        "itinerary:TA001",
        "ItineraryFSM",
    )

    assert direct_view.state == "flight_held"
    assert direct_view.version == 1
    assert direct_view.effective_records == ["ta-rid-001"]


@pytest.mark.asyncio
async def test_temporal_runtime_orchestrates_but_activity_boundary_commits_truth(store, validator):
    client = FakeTemporalClient()
    runtime = TemporalRuntimeDriver(
        namespace="default",
        task_queue="mnemosyne-stage1",
        client=client,
    )

    handle = await runtime.submit_workflow(
        {
            "workflow_id": "workflow:temporal-activity-001",
            "tenant_id": "tenant:temporal-activity",
            "app_id": "travel",
            "entity_id": "itinerary:TA001",
        }
    )

    assert handle.workflow_id == "workflow:temporal-activity-001"
    assert handle.status == "submitted"

    empty_view_before = await store.get_state_view(
        "tenant:temporal-activity",
        "itinerary:TA001",
        "ItineraryFSM",
    )

    assert empty_view_before.state is None
    assert empty_view_before.version == 0
    assert empty_view_before.effective_records == []

    batch = make_activity_batch()

    activity_result = await validate_and_commit_batch_activity(
        batch=batch,
        store=store,
        validator=validator,
    )

    assert activity_result.committed_rids == ["ta-rid-001"]

    view_after_activity = await store.get_state_view(
        "tenant:temporal-activity",
        "itinerary:TA001",
        "ItineraryFSM",
    )

    assert view_after_activity.state == "flight_held"
    assert view_after_activity.version == 1
    assert view_after_activity.effective_records == ["ta-rid-001"]

    runtime_status = await runtime.query_status("workflow:temporal-activity-001")

    assert runtime_status.status == "submitted"
    assert runtime_status.detail["runtime"] == "fake_temporal"

    assert not hasattr(runtime, "commit_batch")
    assert not hasattr(runtime, "get_state_view")