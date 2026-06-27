from __future__ import annotations

import pytest

from mnemosyne.api.audit import audit_active_commitments
from mnemosyne.benchmarks.jssp_disruption_commitments import (
    active_commitment_for_scheduled_operation,
    active_commitment_statuses,
    register_schedule_commitments,
    signal_machine_breakdown,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    commitment_id_for_operation,
    make_jssp_3x3_baseline_schedule,
    make_machine_breakdown_for_3x3_smoke,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
)

T = "tenant:r60-jssp"
W = "workflow:r60-jssp"
G = "tx:r60-jssp"


def test_jssp_active_commitment_for_scheduled_operation_is_stable():
    schedule = make_jssp_3x3_baseline_schedule()
    scheduled_operation = schedule.operations_by_machine("M1")[1]

    commitment = active_commitment_for_scheduled_operation(
        schedule=schedule,
        scheduled_operation=scheduled_operation,
    )

    assert commitment.commitment_id == (
        "jssp:jssp-3x3-smoke:commitment:J3:O2:machine:M1"
    )
    assert commitment.commitment_type == "jssp_machine_availability_guard"
    assert commitment.dependency_scope["entity_id"] == (
        "jssp:jssp-3x3-smoke:operation:J3:O2"
    )
    assert commitment.dependency_scope["machine_id"] == "M1"
    assert commitment.dependency_scope["operation_key"] == "J3:O2"


@pytest.mark.asyncio
async def test_jssp_registers_schedule_commitments_for_all_baseline_operations(store, validator):
    schedule = make_jssp_3x3_baseline_schedule()

    admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=schedule,
    )
    assert admission.ok

    registrations = await register_schedule_commitments(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
    )

    assert len(registrations) == 9
    assert all(item.result.ok for item in registrations)
    assert [item.operation_key for item in registrations] == schedule.operation_keys

    statuses = await active_commitment_statuses(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_ids=[item.commitment_id for item in registrations],
    )

    assert set(statuses.values()) == {"live"}

    audit_rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert len(audit_rows) == 9
    assert {row.status for row in audit_rows} == {"live"}


@pytest.mark.asyncio
async def test_jssp_machine_breakdown_fires_only_affected_commitments_without_mutating_schedule(
    store,
    validator,
):
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=schedule,
    )
    assert admission.ok

    registrations = await register_schedule_commitments(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
    )
    assert all(item.result.ok for item in registrations)

    result = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )

    assert result.ok
    assert result.affected_operation_keys == ["J3:O2", "J2:O3"]
    assert result.fired_commitment_ids == [
        commitment_id_for_operation(
            case_id=schedule.case_id,
            operation=schedule.operations_by_machine("M1")[1],
        ),
        commitment_id_for_operation(
            case_id=schedule.case_id,
            operation=schedule.operations_by_machine("M1")[2],
        ),
    ]

    statuses = await active_commitment_statuses(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_ids=[item.commitment_id for item in registrations],
    )

    fired = {
        cid
        for cid, status in statuses.items()
        if status == "fired"
    }
    live = {
        cid
        for cid, status in statuses.items()
        if status == "live"
    }

    assert fired == set(result.fired_commitment_ids)
    assert len(live) == 7

    audit_rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert len(audit_rows) == 9
    assert {
        row.commitment_id
        for row in audit_rows
        if row.status == "fired"
    } == set(result.fired_commitment_ids)

    # The disruption fires commitments only. It must not mutate the admitted
    # schedule StateView.
    for scheduled_operation in schedule.operations:
        state_view = await store.get_state_view(
            T,
            schedule_entity_id(schedule.case_id, scheduled_operation.key),
            JSSP_FSM_ID,
        )

        assert state_view.state == "scheduled"
        assert state_view.attrs["machine_id"] == scheduled_operation.machine_id
        assert state_view.attrs["start"] == scheduled_operation.start
        assert state_view.attrs["end"] == scheduled_operation.end
        assert state_view.attrs["duration"] == scheduled_operation.duration


@pytest.mark.asyncio
async def test_jssp_machine_breakdown_with_no_overlap_fires_nothing(store, validator):
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = type(make_machine_breakdown_for_3x3_smoke())(
        event_id="jssp-3x3-smoke:breakdown:M2:9-12",
        machine_id="M2",
        unavailable_start=9,
        unavailable_end=12,
    )

    admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=schedule,
    )
    assert admission.ok

    registrations = await register_schedule_commitments(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
    )
    assert all(item.result.ok for item in registrations)

    result = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )

    assert result.ok
    assert result.affected == []
    assert result.fired == []

    statuses = await active_commitment_statuses(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_ids=[item.commitment_id for item in registrations],
    )

    assert set(statuses.values()) == {"live"}
