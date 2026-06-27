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
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This file begins Stage 0.3: local end-to-end runtime/demo validation.
#
# It does not yet require Temporal, Postgres, OR-Tools, LLM APIs, or any
# external service.
#
# Instead, it verifies the complete local memory loop using SQLiteStore:
#
#   1. Command log
#      A human/API/runtime command is recorded with tenant-scoped idempotency.
#
#   2. Event inbox
#      An external event is received and deduped by tenant/source/dedupe_key.
#
#   3. Event log
#      The observed event is durably recorded as causal memory.
#
#   4. CTL CommitBatch
#      A validated transition is committed to the Control Transition Ledger.
#
#   5. StateView
#      The current effective state is exposed through the public store API.
#
#   6. Outbox
#      An external side-effect intent is durably written, but not executed.
#
# Architectural principle:
#
#   CTL is the source of truth for committed state.
#   Event log is the source of truth for observed causes.
#   Outbox is the durable boundary for external side effects.
#   Runtime engines are orchestration mechanisms, not domain truth.
#
# This test proves that the local core can already express a full operational
# cycle before we add distributed runtime complexity.
# ---------------------------------------------------------------------------


FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_command() -> Command:
    """Create a command representing a user/API request.

    API role:
        Command is the durable intent submitted by a human, API, CLI, or
        runtime.

    In this demo:
        The command asks the system to start or update a ride workflow.

    Store behavior under test:
        append_command(...) should store the command once using
        tenant-scoped idempotency.
    """
    return Command(
        command_id="cmd-demo-001",
        tenant_id="tenant:demo",
        actor_id="user:alice",
        command_type="ride.request_pickup",
        payload={
            "pickup": "Stanford",
            "dropoff": "SFO",
            "passenger": "Alice",
        },
        idempotency_key="demo:ride:R100:request-pickup",
        workflow_id="ride:R100",
        submitted_at=FIXED_TIME,
    )


def make_external_event() -> ExternalEvent:
    """Create an external event representing an observed provider/runtime fact.

    API role:
        ExternalEvent represents an observed cause from outside the CTL.

    In this demo:
        A GPS/provider event says the driver has arrived.

    Store behavior under test:
        record_inbox_event(...) dedupes inbound retries by:
            tenant_id + source + dedupe_key

        append_event(...) records the event as observed causal memory.
    """
    return ExternalEvent(
        event_id="evt-demo-001",
        tenant_id="tenant:demo",
        source="gps",
        event_type="driver_arrived",
        entity_refs={
            "ride": "ride:R100",
            "driver": "driver:joe",
        },
        payload={
            "location": "Stanford",
            "provider_timestamp": "2026-06-19T12:00:00Z",
        },
        workflow_id="ride:R100",
        binding_id="binding:ride:R100",
        schema_id="rideshare.event",
        schema_version="1.0",
        dedupe_key="gps:ride:R100:driver-arrived",
        timestamp=FIXED_TIME,
    )


def make_ctl_record() -> CTLRecord:
    """Create one CTL transition derived from the command/event context.

    API role:
        CTLRecord is the committed transition in the Control Transition Ledger.

    In a fuller runtime:
        A validator/planner would produce this CTLRecord from commands,
        events, current StateView, app FSMs, policies, and constraints.

    In this Stage 0.3 local demo:
        We construct the CTLRecord directly so the test remains focused on
        the end-to-end persistence contract.

    Transition:
        none -> driver_arrived

    Expected StateView after commit:
        state = "driver_arrived"
        version = 1
        effective_records = ["rid-demo-001"]
    """
    return CTLRecord(
        rid="rid-demo-001",
        op_id="op-demo-001",
        tenant_id="tenant:demo",
        tx_group_id="tx-demo-001",
        workflow_id="ride:R100",
        binding_id="binding:ride:R100",
        eid="ride:R100",
        fsm="RideFSM",
        version=1,
        state_before="none",
        state_after="driver_arrived",
        action_type="driver_arrival_observed",
        triggers=["evt-demo-001"],
        dependencies=[],
        metadata={
            "command_id": "cmd-demo-001",
            "event_id": "evt-demo-001",
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
        validator_id="local.demo.validator",
        validator_version="1.0",
        timestamp=FIXED_TIME,
    )


def make_outbox_intent() -> OutboxIntent:
    """Create an outbox intent for a side effect triggered by the CTL commit.

    API role:
        OutboxIntent is a durable request to perform an external side effect.

    Why outbox:
        The store must not directly call external systems during CTL commit.
        Instead, it records a pending outbox intent in the same transaction.

    In this demo:
        The side effect is an SMS notification saying the driver arrived.

    Expected:
        The outbox row is inserted with status = "pending".
    """
    return OutboxIntent(
        outbox_id="outbox-demo-001",
        tenant_id="tenant:demo",
        provider="twilio",
        effect_type="send_sms",
        payload={
            "to": "+15551234567",
            "body": "Your driver has arrived at Stanford.",
        },
        provider_idempotency_key="twilio:ride:R100:driver-arrived",
        workflow_id="ride:R100",
        binding_id="binding:ride:R100",
        created_at=FIXED_TIME,
    )


def make_commit_batch() -> CommitBatch:
    """Create the atomic commit boundary for the demo transition.

    API role:
        CommitBatch groups CTL records and outbox intents into one atomic
        durable store transaction.

    In this demo:
        The batch contains one outbox intent. The CTL record is passed
        separately to store.commit_batch(batch, records), following the current
        store API.
    """
    return CommitBatch(
        batch_id="batch-demo-001",
        tenant_id="tenant:demo",
        workflow_id="ride:R100",
        tx_group_id="tx-demo-001",
        candidates=[],
        outbox_intents=[make_outbox_intent()],
    )


@pytest.mark.asyncio
async def test_local_end_to_end_command_event_ctl_stateview_outbox_loop():
    """Verify the full local persistence loop works without external services.

    Store APIs under test:
        append_command(...)
        record_inbox_event(...)
        append_event(...)
        has_event(...)
        commit_batch(...)
        get_state_view(...)

    Tables indirectly exercised:
        commands
        event_inbox
        event_log
        ctl_records
        effective_record_index
        entity_projection
        outbox

    Expected final result:
        - command is logged;
        - inbound event is deduped in inbox;
        - event is logged;
        - CTL record is committed;
        - StateView shows driver_arrived;
        - outbox has one pending SMS intent.
    """
    store = SQLiteStore()

    command = make_command()
    event = make_external_event()
    record = make_ctl_record()
    batch = make_commit_batch()

    # -----------------------------------------------------------------------
    # Step 1: record the submitted command.
    # -----------------------------------------------------------------------
    await store.append_command(command)

    # Submitting the same command again should be idempotent.
    await store.append_command(command)

    command_rows = store.conn.execute(
        """
        SELECT *
        FROM commands
        WHERE tenant_id = ?
          AND idempotency_key = ?
        """,
        ("tenant:demo", "demo:ride:R100:request-pickup"),
    ).fetchall()

    assert len(command_rows) == 1
    assert command_rows[0]["command_id"] == "cmd-demo-001"
    assert command_rows[0]["workflow_id"] == "ride:R100"

    # -----------------------------------------------------------------------
    # Step 2: record the inbound event in the inbox.
    # -----------------------------------------------------------------------
    await store.record_inbox_event(event)

    # Receiving the same provider retry should not duplicate the inbox row.
    await store.record_inbox_event(event)

    inbox_rows = store.conn.execute(
        """
        SELECT *
        FROM event_inbox
        WHERE tenant_id = ?
          AND source = ?
          AND dedupe_key = ?
        """,
        ("tenant:demo", "gps", "gps:ride:R100:driver-arrived"),
    ).fetchall()

    assert len(inbox_rows) == 1
    assert inbox_rows[0]["event_id"] == "evt-demo-001"
    assert inbox_rows[0]["status"] == "received"

    # -----------------------------------------------------------------------
    # Step 3: append the observed event to the event log.
    # -----------------------------------------------------------------------
    await store.append_event(event)

    # Event log is also idempotent by tenant/event_id.
    await store.append_event(event)

    assert await store.has_event("tenant:demo", "evt-demo-001") is True
    assert await store.has_event("tenant:demo", "evt-missing") is False

    event_rows = store.conn.execute(
        """
        SELECT *
        FROM event_log
        WHERE tenant_id = ?
          AND event_id = ?
        """,
        ("tenant:demo", "evt-demo-001"),
    ).fetchall()

    assert len(event_rows) == 1
    assert event_rows[0]["event_type"] == "driver_arrived"

    event_entity_refs = json.loads(event_rows[0]["entity_refs"])
    assert event_entity_refs["ride"] == "ride:R100"
    assert event_entity_refs["driver"] == "driver:joe"

    # -----------------------------------------------------------------------
    # Step 4: commit the CTL transition and outbox intent atomically.
    # -----------------------------------------------------------------------
    committed = await store.commit_batch(batch, [record])

    assert len(committed) == 1
    assert committed[0].rid == "rid-demo-001"
    assert committed[0].state_after == "driver_arrived"

    # -----------------------------------------------------------------------
    # Step 5: verify the public StateView API.
    # -----------------------------------------------------------------------
    view = await store.get_state_view(
        "tenant:demo",
        "ride:R100",
        "RideFSM",
    )

    assert view.tenant_id == "tenant:demo"
    assert view.eid == "ride:R100"
    assert view.fsm == "RideFSM"
    assert view.state == "driver_arrived"
    assert view.version == 1
    assert view.workflow_id == "ride:R100"
    assert view.binding_id == "binding:ride:R100"
    assert view.effective_records == ["rid-demo-001"]

    # -----------------------------------------------------------------------
    # Step 6: verify the outbox side-effect intent is pending.
    # -----------------------------------------------------------------------
    outbox_rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE tenant_id = ?
          AND provider = ?
          AND provider_idempotency_key = ?
        """,
        ("tenant:demo", "twilio", "twilio:ride:R100:driver-arrived"),
    ).fetchall()

    assert len(outbox_rows) == 1
    assert outbox_rows[0]["outbox_id"] == "outbox-demo-001"
    assert outbox_rows[0]["effect_type"] == "send_sms"
    assert outbox_rows[0]["status"] == "pending"

    outbox_payload = json.loads(outbox_rows[0]["payload"])
    assert outbox_payload["body"] == "Your driver has arrived at Stanford."