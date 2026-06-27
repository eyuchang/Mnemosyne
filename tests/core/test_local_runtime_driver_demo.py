from datetime import datetime, timezone
import json

import pytest

from mnemosyne.core.models import (
    CTLRecord,
    Command,
    CommitBatch,
    ExternalEvent,
    OutboxIntent,
)
from mnemosyne.runtime.local import LocalRuntimeDriver
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This test verifies the Stage 0.3 local runtime boundary.
#
# Previous end-to-end test:
#
#     Command
#     -> inbox event
#     -> event log
#     -> CTL
#     -> StateView
#     -> Outbox
#
# This test adds the local RuntimeDriver:
#
#     LocalRuntimeDriver.submit_workflow(...)
#     LocalRuntimeDriver.signal_disruption(...)
#     LocalRuntimeDriver.query_status(...)
#
# Architectural principle:
#
#     Runtime engines are orchestration mechanisms, not domain truth.
#
# Therefore:
#
#     - The runtime may track workflow status.
#     - The store/CTL remains the source of committed domain truth.
#     - The event log remains the source of observed causes.
#     - StateView remains the public API for current effective state.
#
# This prepares us for Temporal later:
#
#     LocalRuntimeDriver now exercises the same runtime protocol shape that
#     TemporalRuntimeDriver will eventually implement.
# ---------------------------------------------------------------------------


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_command() -> Command:
    """Create a workflow command.

    API role:
        Command represents an instruction from a human, API, CLI, or runtime.

    In this test:
        The command asks the local system to run a ride workflow.

    Store contract:
        append_command(...) should dedupe by tenant_id + idempotency_key.
    """
    return Command(
        command_id="cmd-runtime-demo-001",
        tenant_id="tenant:runtime-demo",
        actor_id="user:alice",
        command_type="ride.start_workflow",
        payload={
            "workflow_id": "ride-workflow:R200",
            "ride_id": "ride:R200",
            "pickup": "Stanford",
            "dropoff": "SFO",
        },
        idempotency_key="runtime-demo:ride:R200:start",
        workflow_id="ride-workflow:R200",
        submitted_at=FIXED_TIME,
    )


def make_external_event() -> ExternalEvent:
    """Create an external disruption/provider event.

    API role:
        ExternalEvent represents an observed external fact.

    In this test:
        A GPS provider reports that the driver has arrived.

    Runtime role:
        The event is signaled into LocalRuntimeDriver.

    Store role:
        The same event is recorded in the inbox and event log.
    """
    return ExternalEvent(
        event_id="evt-runtime-demo-001",
        tenant_id="tenant:runtime-demo",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:R200",
            "driver": "driver:joe",
        },
        payload={
            "location": "Stanford",
            "provider_timestamp": "2026-06-19T12:00:00Z",
        },
        workflow_id="ride-workflow:R200",
        binding_id="binding:ride:R200",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:R200:driver-arrived",
        timestamp=FIXED_TIME,
    )


def make_ctl_record() -> CTLRecord:
    """Create the committed domain transition.

    API role:
        CTLRecord is one committed transition in the Control Transition Ledger.

    In a later implementation:
        The runtime/planner/validator would derive this record from:
            - command log;
            - event log;
            - app FSM;
            - current StateView;
            - policies and constraints.

    In this test:
        We construct it directly to keep the runtime boundary test focused.

    Transition:
        none -> driver_arrived
    """
    return CTLRecord(
        rid="rid-runtime-demo-001",
        op_id="op-runtime-demo-001",
        tenant_id="tenant:runtime-demo",
        tx_group_id="tx-runtime-demo-001",
        workflow_id="ride-workflow:R200",
        binding_id="binding:ride:R200",
        eid="ride:R200",
        fsm="RideFSM",
        version=1,
        state_before="none",
        state_after="driver_arrived",
        action_type="driver_arrival_observed",
        triggers=["evt-runtime-demo-001"],
        dependencies=[],
        metadata={
            "command_id": "cmd-runtime-demo-001",
            "event_id": "evt-runtime-demo-001",
            "runtime": "local",
        },
        extension={
            "driver": "driver:joe",
            "location": "Stanford",
        },
        app_id="rideshare",
        app_version="1.0",
        schema_id="rideshare.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="local.runtime.demo.validator",
        validator_version="1.0",
        timestamp=FIXED_TIME,
    )


def make_outbox_intent() -> OutboxIntent:
    """Create a durable external side-effect intent.

    API role:
        OutboxIntent records that an external side effect should happen later.

    Important:
        The runtime and store do not directly send SMS here.

        Instead:
            - commit_batch(...) writes this intent durably;
            - a later worker/provider adapter will execute it.

    This preserves atomicity:
        domain state and side-effect intent are committed together.
    """
    return OutboxIntent(
        outbox_id="outbox-runtime-demo-001",
        tenant_id="tenant:runtime-demo",
        provider="twilio",
        effect_type="send_sms",
        payload={
            "to": "+15551234567",
            "body": "Your driver has arrived at Stanford.",
        },
        provider_idempotency_key="twilio:ride:R200:driver-arrived",
        workflow_id="ride-workflow:R200",
        binding_id="binding:ride:R200",
        created_at=FIXED_TIME,
    )


def make_commit_batch() -> CommitBatch:
    """Create the atomic CTL/outbox commit boundary.

    API role:
        CommitBatch groups domain commits and side-effect intents.

    In this test:
        The batch has one outbox intent, and the CTL record is supplied to:

            await store.commit_batch(batch, [record])
    """
    return CommitBatch(
        batch_id="batch-runtime-demo-001",
        tenant_id="tenant:runtime-demo",
        workflow_id="ride-workflow:R200",
        tx_group_id="tx-runtime-demo-001",
        candidates=[],
        outbox_intents=[make_outbox_intent()],
    )


@pytest.mark.asyncio
async def test_local_runtime_driver_coordinates_with_store_without_becoming_domain_truth():
    """Verify local runtime orchestration plus durable store truth.

    Runtime APIs under test:
        submit_workflow(...)
        signal_disruption(...)
        query_status(...)

    Store APIs under test:
        append_command(...)
        record_inbox_event(...)
        append_event(...)
        commit_batch(...)
        get_state_view(...)

    Expected result:
        - LocalRuntimeDriver tracks workflow submission/signaling.
        - SQLiteStore records command/event/CTL/outbox truth.
        - StateView exposes the current effective domain state.
        - Runtime status does not replace CTL or StateView.
    """
    runtime = LocalRuntimeDriver()
    store = SQLiteStore()

    command = make_command()
    event = make_external_event()
    record = make_ctl_record()
    batch = make_commit_batch()

    # -----------------------------------------------------------------------
    # Step 1: submit workflow to the local runtime.
    # -----------------------------------------------------------------------
    # This proves the local runtime boundary can accept a workflow spec.
    # The runtime stores orchestration status, not domain truth.
    handle = await runtime.submit_workflow(
        {
            "workflow_id": "ride-workflow:R200",
            "tenant_id": "tenant:runtime-demo",
            "app_id": "rideshare",
            "entity_id": "ride:R200",
        }
    )

    assert handle.workflow_id == "ride-workflow:R200"
    assert handle.run_id == "local-run-1"
    assert handle.status == "submitted"

    submitted_status = await runtime.query_status("ride-workflow:R200")

    assert submitted_status.workflow_id == "ride-workflow:R200"
    assert submitted_status.status == "submitted"
    assert submitted_status.detail["spec"]["app_id"] == "rideshare"
    assert submitted_status.detail["spec"]["entity_id"] == "ride:R200"

    # -----------------------------------------------------------------------
    # Step 2: record command in durable store.
    # -----------------------------------------------------------------------
    # The command log is durable intent memory.
    await store.append_command(command)

    command_rows = store.conn.execute(
        """
        SELECT *
        FROM commands
        WHERE tenant_id = ?
          AND command_id = ?
        """,
        ("tenant:runtime-demo", "cmd-runtime-demo-001"),
    ).fetchall()

    assert len(command_rows) == 1
    assert command_rows[0]["workflow_id"] == "ride-workflow:R200"

    # -----------------------------------------------------------------------
    # Step 3: signal external event to runtime.
    # -----------------------------------------------------------------------
    # Runtime receives orchestration signal.
    # This does not itself commit domain state.
    await runtime.signal_disruption("ride-workflow:R200", event)

    signaled_status = await runtime.query_status("ride-workflow:R200")

    assert signaled_status.status == "signaled"
    assert signaled_status.detail["events"] == ["evt-runtime-demo-001"]

    # -----------------------------------------------------------------------
    # Step 4: record event in inbox and event log.
    # -----------------------------------------------------------------------
    # Store receives durable event memory.
    await store.record_inbox_event(event)
    await store.append_event(event)

    inbox_rows = store.conn.execute(
        """
        SELECT *
        FROM event_inbox
        WHERE tenant_id = ?
          AND source = ?
          AND dedupe_key = ?
        """,
        ("tenant:runtime-demo", "gps", "gps:ride:R200:driver-arrived"),
    ).fetchall()

    event_rows = store.conn.execute(
        """
        SELECT *
        FROM event_log
        WHERE tenant_id = ?
          AND event_id = ?
        """,
        ("tenant:runtime-demo", "evt-runtime-demo-001"),
    ).fetchall()

    assert len(inbox_rows) == 1
    assert inbox_rows[0]["status"] == "received"

    assert len(event_rows) == 1
    assert event_rows[0]["event_type"] == "driver_arrived"

    event_refs = json.loads(event_rows[0]["entity_refs"])
    assert event_refs["ride"] == "ride:R200"
    assert event_refs["driver"] == "driver:joe"

    # -----------------------------------------------------------------------
    # Step 5: commit domain transition into CTL.
    # -----------------------------------------------------------------------
    # This is the domain truth commit.
    # Runtime status alone is not enough; CTL must record the transition.
    committed = await store.commit_batch(batch, [record])

    assert len(committed) == 1
    assert committed[0].rid == "rid-runtime-demo-001"
    assert committed[0].state_after == "driver_arrived"
    assert committed[0].triggers == ["evt-runtime-demo-001"]

    # -----------------------------------------------------------------------
    # Step 6: read public StateView.
    # -----------------------------------------------------------------------
    # This is the current effective domain truth exposed to future planners,
    # validators, APIs, and runtime decisions.
    view = await store.get_state_view(
        "tenant:runtime-demo",
        "ride:R200",
        "RideFSM",
    )

    assert view.state == "driver_arrived"
    assert view.version == 1
    assert view.workflow_id == "ride-workflow:R200"
    assert view.binding_id == "binding:ride:R200"
    assert view.effective_records == ["rid-runtime-demo-001"]

    # -----------------------------------------------------------------------
    # Step 7: verify durable outbox intent.
    # -----------------------------------------------------------------------
    # External side effect is pending, not executed inline.
    outbox_rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE tenant_id = ?
          AND provider = ?
          AND provider_idempotency_key = ?
        """,
        ("tenant:runtime-demo", "twilio", "twilio:ride:R200:driver-arrived"),
    ).fetchall()

    assert len(outbox_rows) == 1
    assert outbox_rows[0]["outbox_id"] == "outbox-runtime-demo-001"
    assert outbox_rows[0]["effect_type"] == "send_sms"
    assert outbox_rows[0]["status"] == "pending"

    outbox_payload = json.loads(outbox_rows[0]["payload"])
    assert outbox_payload["body"] == "Your driver has arrived at Stanford."

    # -----------------------------------------------------------------------
    # Final architectural check.
    # -----------------------------------------------------------------------
    # Runtime knows the workflow was signaled.
    # Store/StateView knows the domain state.
    # These are related but separate responsibilities.
    final_runtime_status = await runtime.query_status("ride-workflow:R200")
    final_state_view = await store.get_state_view(
        "tenant:runtime-demo",
        "ride:R200",
        "RideFSM",
    )

    assert final_runtime_status.status == "signaled"
    assert final_state_view.state == "driver_arrived"