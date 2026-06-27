from datetime import datetime, timezone
import json

import pytest

from mnemosyne.core.models import CTLRecord, CommitBatch
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# These tests verify the distinction between:
#
#   1. Historical truth
#      - CTL keeps every committed record.
#      - Even compensated or superseded records remain in ctl_records.
#
#   2. Current effective truth
#      - effective_record_index marks which records still count toward the
#        current StateView.
#      - entity_projection should be rebuilt from effective records only.
#
# This is a core Mnemosyne/ALAS principle:
#
#   CTL is append-only historical memory.
#   Projection is current operational memory.
#
# Compensation and supersession must therefore not delete history. They only
# change which records remain effective.
# ---------------------------------------------------------------------------


# Fixed timestamp keeps tests deterministic.
FIXED_TIME = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)


def make_record(
    *,
    rid: str,
    version: int,
    state_before: str,
    state_after: str,
    metadata: dict | None = None,
    eid: str = "itinerary:T-comp",
    fsm: str = "ItineraryFSM",
    tenant_id: str = "tenant:comp",
    tx_group_id: str = "tx:comp",
    workflow_id: str = "trip:T-comp",
    binding_id: str = "binding:T-comp",
) -> CTLRecord:
    """Create a CTLRecord for compensation/supersession tests.

    API role:
        CTLRecord is the durable Control Transition Ledger entry.

    Important compensation fields:
        metadata["compensates"]:
            A list of prior CTL record ids that this record compensates.

        metadata["supersedes"]:
            A list of prior CTL record ids that this record replaces.

    Store behavior under test:
        SQLiteStore.commit_batch(...) should:
            - insert the new CTL record;
            - mark the new record effective;
            - mark compensated/superseded records ineffective;
            - update entity_projection from effective records only.

    Design:
        We use the same entity/FSM for the original and corrective record.
        Version still advances monotonically:
            original record: version 1
            corrective record: version 2
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
    tx_group_id: str = "tx:comp",
    tenant_id: str = "tenant:comp",
    workflow_id: str = "trip:T-comp",
) -> CommitBatch:
    """Create a CommitBatch with no outbox intents.

    API role:
        CommitBatch is the atomic store boundary.

    In these tests, we focus only on CTL/effective-index/projection behavior,
    so outbox_intents is empty.
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
async def test_compensation_preserves_ctl_history_but_updates_effective_projection():
    """Verify compensation keeps history but changes current effective state.

    Scenario:
        1. Commit an original transition:
              none -> flight_held

        2. Commit a later compensation transition:
              flight_held -> flight_cancelled
           with:
              metadata={"compensates": ["comp-rid-001"]}

    Expected:
        - Both CTL rows remain present.
        - Original record becomes ineffective.
        - Compensation record is effective.
        - Projection reflects flight_cancelled.
        - Projection effective_records contains only the compensation rid.
    """
    store = SQLiteStore()

    original = make_record(
        rid="comp-rid-001",
        version=1,
        state_before="none",
        state_after="flight_held",
    )

    compensation = make_record(
        rid="comp-rid-002",
        version=2,
        state_before="flight_held",
        state_after="flight_cancelled",
        metadata={"compensates": ["comp-rid-001"]},
    )

    # First commit establishes the original current state.
    await store.commit_batch(
        make_batch(batch_id="batch-comp-original"),
        [original],
    )

    # Second commit compensates the original record.
    await store.commit_batch(
        make_batch(batch_id="batch-comp-corrective"),
        [compensation],
    )

    # -----------------------------------------------------------------------
    # Historical CTL inspection.
    # -----------------------------------------------------------------------
    # CTL must preserve both records. Compensation does not delete history.
    ctl_rows = store.conn.execute(
        """
        SELECT rid, version, state_after
        FROM ctl_records
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        ORDER BY version ASC
        """,
        ("tenant:comp", "itinerary:T-comp", "ItineraryFSM"),
    ).fetchall()

    # -----------------------------------------------------------------------
    # Effective index inspection.
    # -----------------------------------------------------------------------
    # The original record should be ineffective, changed by the compensation.
    # The compensation record should remain effective.
    effective_rows = store.conn.execute(
        """
        SELECT rid, effective, changed_by_rid
        FROM effective_record_index
        WHERE tenant_id = ?
        ORDER BY rid ASC
        """,
        ("tenant:comp",),
    ).fetchall()

    # -----------------------------------------------------------------------
    # Projection inspection.
    # -----------------------------------------------------------------------
    # Projection should reflect only effective records.
    projection_row = store.conn.execute(
        """
        SELECT *
        FROM entity_projection
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        """,
        ("tenant:comp", "itinerary:T-comp", "ItineraryFSM"),
    ).fetchone()

    assert len(ctl_rows) == 2
    assert ctl_rows[0]["rid"] == "comp-rid-001"
    assert ctl_rows[0]["version"] == 1
    assert ctl_rows[0]["state_after"] == "flight_held"
    assert ctl_rows[1]["rid"] == "comp-rid-002"
    assert ctl_rows[1]["version"] == 2
    assert ctl_rows[1]["state_after"] == "flight_cancelled"

    assert len(effective_rows) == 2
    assert effective_rows[0]["rid"] == "comp-rid-001"
    assert effective_rows[0]["effective"] == 0
    assert effective_rows[0]["changed_by_rid"] == "comp-rid-002"
    assert effective_rows[1]["rid"] == "comp-rid-002"
    assert effective_rows[1]["effective"] == 1
    assert effective_rows[1]["changed_by_rid"] is None

    assert projection_row is not None
    assert projection_row["state"] == "flight_cancelled"
    assert projection_row["version"] == 2

    projection_effective_records = json.loads(projection_row["effective_records"])
    assert projection_effective_records == ["comp-rid-002"]


@pytest.mark.asyncio
async def test_supersession_preserves_ctl_history_but_updates_effective_projection():
    """Verify supersession keeps history but replaces current effective record.

    Scenario:
        1. Commit an original transition:
              none -> hotel_held

        2. Commit a later replacement transition:
              hotel_held -> hotel_rebooked
           with:
              metadata={"supersedes": ["super-rid-001"]}

    Expected:
        - Both CTL rows remain present.
        - Original record becomes ineffective.
        - Superseding record is effective.
        - Projection reflects hotel_rebooked.
        - Projection effective_records contains only the superseding rid.
    """
    store = SQLiteStore()

    original = make_record(
        rid="super-rid-001",
        version=1,
        state_before="none",
        state_after="hotel_held",
        eid="itinerary:T-super",
        tx_group_id="tx:super",
        workflow_id="trip:T-super",
        binding_id="binding:T-super",
    )

    superseding = make_record(
        rid="super-rid-002",
        version=2,
        state_before="hotel_held",
        state_after="hotel_rebooked",
        metadata={"supersedes": ["super-rid-001"]},
        eid="itinerary:T-super",
        tx_group_id="tx:super",
        workflow_id="trip:T-super",
        binding_id="binding:T-super",
    )

    # First commit establishes the original current state.
    await store.commit_batch(
        make_batch(
            batch_id="batch-super-original",
            tx_group_id="tx:super",
            workflow_id="trip:T-super",
        ),
        [original],
    )

    # Second commit supersedes the original record.
    await store.commit_batch(
        make_batch(
            batch_id="batch-super-replacement",
            tx_group_id="tx:super",
            workflow_id="trip:T-super",
        ),
        [superseding],
    )

    ctl_rows = store.conn.execute(
        """
        SELECT rid, version, state_after
        FROM ctl_records
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        ORDER BY version ASC
        """,
        ("tenant:comp", "itinerary:T-super", "ItineraryFSM"),
    ).fetchall()

    effective_rows = store.conn.execute(
        """
        SELECT rid, effective, changed_by_rid
        FROM effective_record_index
        WHERE tenant_id = ?
        ORDER BY rid ASC
        """,
        ("tenant:comp",),
    ).fetchall()

    projection_row = store.conn.execute(
        """
        SELECT *
        FROM entity_projection
        WHERE tenant_id = ?
          AND eid = ?
          AND fsm = ?
        """,
        ("tenant:comp", "itinerary:T-super", "ItineraryFSM"),
    ).fetchone()

    assert len(ctl_rows) == 2
    assert ctl_rows[0]["rid"] == "super-rid-001"
    assert ctl_rows[0]["version"] == 1
    assert ctl_rows[0]["state_after"] == "hotel_held"
    assert ctl_rows[1]["rid"] == "super-rid-002"
    assert ctl_rows[1]["version"] == 2
    assert ctl_rows[1]["state_after"] == "hotel_rebooked"

    assert len(effective_rows) == 2
    assert effective_rows[0]["rid"] == "super-rid-001"
    assert effective_rows[0]["effective"] == 0
    assert effective_rows[0]["changed_by_rid"] == "super-rid-002"
    assert effective_rows[1]["rid"] == "super-rid-002"
    assert effective_rows[1]["effective"] == 1
    assert effective_rows[1]["changed_by_rid"] is None

    assert projection_row is not None
    assert projection_row["state"] == "hotel_rebooked"
    assert projection_row["version"] == 2

    projection_effective_records = json.loads(projection_row["effective_records"])
    assert projection_effective_records == ["super-rid-002"]