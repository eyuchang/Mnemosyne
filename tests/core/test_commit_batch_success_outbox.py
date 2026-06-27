from datetime import datetime, timezone

import pytest

from mnemosyne.core.models import CTLRecord, CommitBatch, OutboxIntent
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This test verifies the positive/success path for SQLiteStore.commit_batch(...).
#
# In Phase 0 / Phase 0.1, commit_batch is one of the most important store APIs.
# It must atomically write:
#
#   1. CTL records
#      - The Control Transition Ledger, source of truth for committed state.
#
#   2. Entity projection
#      - The latest materialized StateView for quick reads.
#
#   3. Effective-record index
#      - Tracks which CTL records are currently effective.
#
#   4. Outbox intents
#      - Durable requests for external side effects, such as email, SMS,
#        payment, booking, cancellation, etc.
#
# This test confirms that when a valid CommitBatch succeeds, all of these
# structures are updated together.
#
# This complements test_commit_batch_atomicity.py, which verifies that when
# commit_batch fails, none of these structures are partially written.
# ---------------------------------------------------------------------------


# Use a fixed timestamp so tests are deterministic and easy to debug.
FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_record(
    *,
    rid: str,
    version: int,
    state_before: str,
    state_after: str,
    eid: str = "itinerary:T-success",
    fsm: str = "ItineraryFSM",
    tenant_id: str = "tenant:success",
    tx_group_id: str = "tx:success",
    workflow_id: str = "trip:T-success",
    binding_id: str = "binding:T-success",
) -> CTLRecord:
    """Create a CTLRecord for the successful CommitBatch test.

    API role:
        CTLRecord represents one committed transition in the Control
        Transition Ledger.

    Important fields:
        rid:
            Globally meaningful record identifier inside the tenant scope.

        op_id:
            Operation id used for idempotency. In this test, we set it equal
            to rid for simplicity.

        tenant_id:
            Tenant namespace. All idempotency and uniqueness rules are
            tenant-scoped.

        tx_group_id:
            Transaction group id. Multiple records in the same CommitBatch
            share the same tx_group_id.

        workflow_id / binding_id:
            Workflow-level identifiers. These later connect CTL records to
            runtime orchestration, Temporal workflows, or application bindings.

        eid:
            Entity id. Here the entity is one travel itinerary.

        fsm:
            Name of the finite-state machine governing the entity.

        version:
            Monotonic entity/FSM version. commit_batch expects each new record
            to advance the current projection version by exactly one.

        state_before / state_after:
            State transition captured by this CTL record.

        action_type:
            Action-typed FSM edge. This matters later for validation,
            compensation, policies, and explainability.

        metadata / extension:
            metadata is for control information such as compensates/supersedes.
            extension is application-specific payload.

    Test design:
        The test creates two records:
            version 1: none -> flight_held
            version 2: flight_held -> trip_confirmed

        This should produce a final projection state of trip_confirmed.
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
        metadata={},
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


def make_outbox_intent() -> OutboxIntent:
    """Create one OutboxIntent for the successful CommitBatch test.

    API role:
        OutboxIntent is a durable declaration that an external side effect
        should happen later.

    Why outbox exists:
        CTL commits should not directly call external APIs such as email,
        payment, booking, or SMS providers.

        Instead, the system writes an outbox intent inside the same transaction
        as the CTL commit. A later worker can read the outbox and perform the
        external side effect safely.

    Important fields:
        outbox_id:
            Local durable id for this outbox request.

        provider:
            External system category, such as email, twilio, stripe, airline.

        effect_type:
            Type of external action requested.

        provider_idempotency_key:
            Provider-facing idempotency key. This prevents duplicated external
            effects if workers retry.

        workflow_id / binding_id:
            Links the external effect back to the workflow/entity context.
    """
    return OutboxIntent(
        outbox_id="outbox-success-001",
        tenant_id="tenant:success",
        provider="email",
        effect_type="send_email",
        payload={
            "to": "customer@example.com",
            "subject": "Trip confirmed",
        },
        provider_idempotency_key="email:trip:T-success:confirmed",
        workflow_id="trip:T-success",
        binding_id="binding:T-success",
        created_at=FIXED_TIME,
    )


@pytest.mark.asyncio
async def test_successful_commit_batch_writes_ctl_projection_and_outbox_atomically():
    """Verify successful CommitBatch writes all required store surfaces.

    Store API under test:
        await store.commit_batch(batch, records)

    Expected behavior:
        If all records are valid:
            - all CTL records are inserted;
            - entity_projection reflects the latest state;
            - effective_record_index marks inserted records effective;
            - outbox intents are inserted as pending;
            - all changes are committed together.

    This test does not call any external provider. It only verifies that the
    durable outbox request is written.
    """
    store = SQLiteStore()

    # First CTL transition for the itinerary entity.
    # Because this is the first transition, version must be 1.
    first_record = make_record(
        rid="success-rid-001",
        version=1,
        state_before="none",
        state_after="flight_held",
    )

    # Second CTL transition for the same entity/FSM.
    # Because the first record is version 1, this record must be version 2.
    second_record = make_record(
        rid="success-rid-002",
        version=2,
        state_before="flight_held",
        state_after="trip_confirmed",
    )

    # CommitBatch groups records and outbox intents into one atomic commit.
    # In production, this is the boundary where a planner/validator has decided
    # that a set of transitions should be committed together.
    batch = CommitBatch(
        batch_id="batch-success-001",
        tenant_id="tenant:success",
        workflow_id="trip:T-success",
        tx_group_id="tx:success",
        candidates=[],
        outbox_intents=[make_outbox_intent()],
    )

    # Main API call under test.
    committed = await store.commit_batch(batch, [first_record, second_record])

    # -----------------------------------------------------------------------
    # Verify API return value.
    # -----------------------------------------------------------------------
    # commit_batch should return the committed CTL records.
    assert len(committed) == 2
    assert committed[0].rid == "success-rid-001"
    assert committed[1].rid == "success-rid-002"

    # -----------------------------------------------------------------------
    # Inspect CTL records.
    # -----------------------------------------------------------------------
    # CTL is the source of truth for committed state.
    ctl_rows = store.conn.execute(
        """
        SELECT *
        FROM ctl_records
        WHERE tenant_id = ?
          AND tx_group_id = ?
        ORDER BY version ASC
        """,
        ("tenant:success", "tx:success"),
    ).fetchall()

    # -----------------------------------------------------------------------
    # Inspect entity projection.
    # -----------------------------------------------------------------------
    # Projection is a read-optimized materialized view of current entity state.
    # It should reflect the latest effective CTL history.
    projection_rows = store.conn.execute(
        """
        SELECT *
        FROM entity_projection
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        """,
        ("tenant:success", "itinerary:T-success", "ItineraryFSM"),
    ).fetchall()

    # -----------------------------------------------------------------------
    # Inspect effective-record index.
    # -----------------------------------------------------------------------
    # The effective index distinguishes records that still count toward current
    # state from records later compensated or superseded.
    effective_rows = store.conn.execute(
        """
        SELECT *
        FROM effective_record_index
        WHERE tenant_id = ?
        ORDER BY rid ASC
        """,
        ("tenant:success",),
    ).fetchall()

    # -----------------------------------------------------------------------
    # Inspect outbox.
    # -----------------------------------------------------------------------
    # Outbox rows represent durable external-effect intents.
    # The external effect has not executed yet; its status should be pending.
    outbox_rows = store.conn.execute(
        """
        SELECT *
        FROM outbox
        WHERE tenant_id = ?
          AND provider_idempotency_key = ?
        """,
        ("tenant:success", "email:trip:T-success:confirmed"),
    ).fetchall()

    # -----------------------------------------------------------------------
    # CTL assertions.
    # -----------------------------------------------------------------------
    # Both records should be present and versioned in order.
    assert len(ctl_rows) == 2
    assert ctl_rows[0]["rid"] == "success-rid-001"
    assert ctl_rows[0]["version"] == 1
    assert ctl_rows[1]["rid"] == "success-rid-002"
    assert ctl_rows[1]["version"] == 2

    # -----------------------------------------------------------------------
    # Projection assertions.
    # -----------------------------------------------------------------------
    # Because the second record transitions to trip_confirmed, the projection
    # should show trip_confirmed as the current state.
    assert len(projection_rows) == 1
    assert projection_rows[0]["state"] == "trip_confirmed"
    assert projection_rows[0]["version"] == 2
    assert projection_rows[0]["workflow_id"] == "trip:T-success"
    assert projection_rows[0]["binding_id"] == "binding:T-success"

    # -----------------------------------------------------------------------
    # Effective-record assertions.
    # -----------------------------------------------------------------------
    # Both records remain effective because no compensation or supersession has
    # occurred in this test.
    assert len(effective_rows) == 2
    assert effective_rows[0]["rid"] == "success-rid-001"
    assert effective_rows[0]["effective"] == 1
    assert effective_rows[1]["rid"] == "success-rid-002"
    assert effective_rows[1]["effective"] == 1

    # -----------------------------------------------------------------------
    # Outbox assertions.
    # -----------------------------------------------------------------------
    # The outbox intent should be durably inserted and waiting for a later
    # worker/provider adapter to execute.
    assert len(outbox_rows) == 1
    assert outbox_rows[0]["outbox_id"] == "outbox-success-001"
    assert outbox_rows[0]["status"] == "pending"
    assert outbox_rows[0]["effect_type"] == "send_email"