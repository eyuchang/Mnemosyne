from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import CTLRecord, CommitBatch
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This file verifies the public StateView API:
#
#     await store.get_state_view(tenant_id, eid, fsm)
#
# Earlier tests inspect SQLite tables directly:
#
#     ctl_records
#     entity_projection
#     effective_record_index
#
# Those low-level tests are useful for validating the store internals, but
# production code should not depend on table details. Production code should
# ask the store for a StateView.
#
# Architectural meaning:
#
#     CTL is the append-only source of committed historical state.
#     StateView is the current effective state exposed to runtime/planner code.
#
# In other words:
#
#     CTL remembers what happened.
#     StateView tells the runtime/planner what is currently true.
#
# Important Phase 0.1 note:
#
#     The current replay_state_view(...) implementation does not promote
#     CTLRecord.extension into StateView.attrs. Therefore these tests do not
#     assert values inside view.attrs except for the empty-view case.
#
#     If later phases define a formal projection/attribute merge policy, we can
#     add separate tests for StateView.attrs.
# ---------------------------------------------------------------------------


# Fixed timestamp keeps the test deterministic.
FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_record(
    *,
    rid: str,
    version: int,
    state_before: str,
    state_after: str,
    metadata: dict | None = None,
    eid: str = "itinerary:T-view",
    fsm: str = "ItineraryFSM",
    tenant_id: str = "tenant:view",
    tx_group_id: str = "tx:view",
    workflow_id: str = "trip:T-view",
    binding_id: str = "binding:T-view",
) -> CTLRecord:
    """Create one CTLRecord for StateView API tests.

    API role:
        CTLRecord is one committed transition in the Control Transition Ledger.

    Why this helper exists:
        The tests need multiple CTL records with consistent tenant/entity/FSM
        identifiers. A helper prevents copy-paste mistakes.

    Important fields:
        rid:
            Record id. If the record remains effective, this id should appear
            in StateView.effective_records.

        version:
            Per-entity/FSM version. The store requires version to increase by
            exactly one relative to the current projection.

        state_before / state_after:
            The state transition captured by the CTL record. StateView.state
            should reflect the state_after of the latest effective record.

        metadata:
            Control metadata used for compensation or supersession, such as:
                {"compensates": ["old-rid"]}
                {"supersedes": ["old-rid"]}

            These fields should update effective_record_index and therefore
            change StateView.effective_records.
    """
    return CTLRecord(
        rid=rid,
        op_id=rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        binding_id=binding_id,
        eid=eid,
        fsm=fsm,
        version=version,
        state_before=state_before,
        state_after=state_after,
        action_type="transition",
        triggers=[],
        dependencies=[],
        metadata=metadata or {},
        extension={"step": state_after},
        app_id="travel",
        app_version="1.0",
        schema_id="travel.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="test.validator",
        validator_version="1.0",
        timestamp=FIXED_TIME,
    )


def make_batch(
    *,
    batch_id: str,
    tenant_id: str = "tenant:view",
    workflow_id: str = "trip:T-view",
    tx_group_id: str = "tx:view",
) -> CommitBatch:
    """Create a CommitBatch for StateView API tests.

    API role:
        CommitBatch is the atomic commit boundary.

    In this file:
        We do not need outbox intents. The purpose is only to verify that
        committed CTL records update the public StateView API correctly.
    """
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        tx_group_id=tx_group_id,
        candidates=[],
        outbox_intents=[],
    )


@pytest.mark.asyncio
async def test_get_state_view_returns_empty_view_for_unknown_entity():
    """Verify get_state_view(...) has a safe empty-state contract.

    Scenario:
        The caller asks for an entity/FSM that has no CTL history.

    Expected:
        The store should not crash and should not return None.

        Instead, it should return a StateView with:
            state = None
            version = 0
            attrs = {}
            effective_records = []

    Why this matters:
        Runtime/planner code can safely ask for current state before the first
        transition has occurred.
    """
    store = SQLiteStore()

    view = await store.get_state_view(
        "tenant:view",
        "itinerary:unknown",
        "ItineraryFSM",
    )

    assert view.tenant_id == "tenant:view"
    assert view.eid == "itinerary:unknown"
    assert view.fsm == "ItineraryFSM"
    assert view.state is None
    assert view.version == 0
    assert view.attrs == {}
    assert view.effective_records == []


@pytest.mark.asyncio
async def test_get_state_view_returns_current_state_after_successful_commits():
    """Verify get_state_view(...) reflects the latest successful CTL commit.

    Scenario:
        Commit two valid transitions for the same entity/FSM:

            version 1: none -> flight_held
            version 2: flight_held -> trip_confirmed

    Expected:
        get_state_view(...) should return:
            state = trip_confirmed
            version = 2
            effective_records = ["view-rid-001", "view-rid-002"]

    Why both records remain effective:
        No compensation or supersession occurred in this test.
    """
    store = SQLiteStore()

    first_record = make_record(
        rid="view-rid-001",
        version=1,
        state_before="none",
        state_after="flight_held",
    )

    second_record = make_record(
        rid="view-rid-002",
        version=2,
        state_before="flight_held",
        state_after="trip_confirmed",
    )

    await store.commit_batch(
        make_batch(batch_id="batch-view-success"),
        [first_record, second_record],
    )

    # Public API under test.
    # Production code should prefer this over querying SQLite tables directly.
    view = await store.get_state_view(
        "tenant:view",
        "itinerary:T-view",
        "ItineraryFSM",
    )

    assert view.tenant_id == "tenant:view"
    assert view.eid == "itinerary:T-view"
    assert view.fsm == "ItineraryFSM"

    # Current operational state should be the latest committed state_after.
    assert view.state == "trip_confirmed"

    # Version should match the latest committed CTL version.
    assert view.version == 2

    # Workflow and binding context should be preserved on the projection.
    assert view.workflow_id == "trip:T-view"
    assert view.binding_id == "binding:T-view"

    # No record was compensated or superseded, so both records remain effective.
    assert view.effective_records == ["view-rid-001", "view-rid-002"]

    # Phase 0.1 contract:
    # extension payloads are stored in CTL, but replay_state_view(...) does not
    # yet promote extension fields into StateView.attrs.
    assert view.attrs == {}


@pytest.mark.asyncio
async def test_get_state_view_uses_only_effective_records_after_compensation():
    """Verify get_state_view(...) reflects compensation correctly.

    Scenario:
        1. Commit an original transition:
              none -> flight_held

        2. Commit a later compensation transition:
              flight_held -> flight_cancelled
           with:
              metadata = {"compensates": ["view-comp-rid-001"]}

    Expected:
        CTL still contains both records internally, but StateView should expose
        only the currently effective truth:

            state = flight_cancelled
            version = 2
            effective_records = ["view-comp-rid-002"]

    Why this matters:
        The planner/runtime should not treat compensated records as current
        truth, while the CTL still preserves them as historical memory.
    """
    store = SQLiteStore()

    original = make_record(
        rid="view-comp-rid-001",
        version=1,
        state_before="none",
        state_after="flight_held",
        eid="itinerary:T-view-comp",
        workflow_id="trip:T-view-comp",
        binding_id="binding:T-view-comp",
    )

    compensation = make_record(
        rid="view-comp-rid-002",
        version=2,
        state_before="flight_held",
        state_after="flight_cancelled",
        metadata={"compensates": ["view-comp-rid-001"]},
        eid="itinerary:T-view-comp",
        workflow_id="trip:T-view-comp",
        binding_id="binding:T-view-comp",
    )

    await store.commit_batch(
        make_batch(
            batch_id="batch-view-comp-original",
            workflow_id="trip:T-view-comp",
        ),
        [original],
    )

    await store.commit_batch(
        make_batch(
            batch_id="batch-view-comp-corrective",
            workflow_id="trip:T-view-comp",
        ),
        [compensation],
    )

    # Public API under test.
    view = await store.get_state_view(
        "tenant:view",
        "itinerary:T-view-comp",
        "ItineraryFSM",
    )

    assert view.tenant_id == "tenant:view"
    assert view.eid == "itinerary:T-view-comp"
    assert view.fsm == "ItineraryFSM"

    # The current state should come from the compensation record.
    assert view.state == "flight_cancelled"
    assert view.version == 2

    # The original record was compensated, so it should not appear here.
    assert view.effective_records == ["view-comp-rid-002"]

    # Workflow/binding context should follow the latest effective record.
    assert view.workflow_id == "trip:T-view-comp"
    assert view.binding_id == "binding:T-view-comp"

    # Phase 0.1 contract:
    # attrs remains empty until we define an explicit projection attribute policy.
    assert view.attrs == {}