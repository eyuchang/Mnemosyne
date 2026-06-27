from __future__ import annotations

import pytest

from mnemosyne.benchmarks.jssp_disruptions import (
    make_jssp_3x3_baseline_schedule,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
    baseline_schedule_commit_batch,
    schedule_operation_candidate,
)

T = "tenant:r60-jssp"
W = "workflow:r60-jssp"
G = "tx:r60-jssp"


def test_jssp_schedule_admission_candidates_are_stable():
    schedule = make_jssp_3x3_baseline_schedule()
    op = schedule.operations[0]

    candidate = schedule_operation_candidate(
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        case_id=schedule.case_id,
        scheduled_operation=op,
    )

    assert candidate.rid == "rid:jssp:jssp-3x3-smoke:schedule:J1:O1"
    assert candidate.eid == "jssp:jssp-3x3-smoke:operation:J1:O1"
    assert candidate.fsm == "JobOpFSM"
    assert candidate.state_before == "ready"
    assert candidate.state_after == "scheduled"
    assert candidate.action_type == "schedule"
    assert candidate.app_id == "jssp"
    assert candidate.schema_id == "jssp.transition"
    assert candidate.extension["attrs_after"]["machine_id"] == "M1"
    assert candidate.extension["attrs_after"]["start"] == 0
    assert candidate.extension["attrs_after"]["end"] == 3
    assert candidate.extension["attrs_after"]["duration"] == 3


def test_jssp_baseline_schedule_commit_batch_contains_all_operations():
    schedule = make_jssp_3x3_baseline_schedule()

    batch = baseline_schedule_commit_batch(
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
    )

    assert batch.batch_id == "batch:jssp:jssp-3x3-smoke:baseline-schedule"
    assert batch.tenant_id == T
    assert batch.workflow_id == W
    assert len(batch.candidates) == 9
    assert [candidate.eid for candidate in batch.candidates] == [
        schedule_entity_id(schedule.case_id, key)
        for key in schedule.operation_keys
    ]
    assert {candidate.fsm for candidate in batch.candidates} == {JSSP_FSM_ID}
    assert {candidate.action_type for candidate in batch.candidates} == {"schedule"}


@pytest.mark.asyncio
async def test_jssp_baseline_schedule_admits_to_ctl_and_stateview(store, validator):
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
    assert len(admission.records) == 9
    assert len(admission.committed) == 9
    assert admission.committed_only_jssp_schedule_fsm
    assert admission.committed_rids == [
        f"rid:jssp:jssp-3x3-smoke:schedule:{key}"
        for key in schedule.operation_keys
    ]

    for scheduled_operation in schedule.operations:
        state_view = await store.get_state_view(
            T,
            schedule_entity_id(schedule.case_id, scheduled_operation.key),
            JSSP_FSM_ID,
        )

        assert state_view.state == "scheduled"
        assert state_view.version == 1
        assert state_view.effective_records == [
            f"rid:jssp:jssp-3x3-smoke:schedule:{scheduled_operation.key}"
        ]
        assert state_view.attrs["machine_id"] == scheduled_operation.machine_id
        assert state_view.attrs["start"] == scheduled_operation.start
        assert state_view.attrs["end"] == scheduled_operation.end
        assert state_view.attrs["duration"] == scheduled_operation.duration
        assert state_view.attrs["baseline_makespan"] == 11


@pytest.mark.asyncio
async def test_jssp_baseline_schedule_admission_fails_closed_on_invalid_schedule(store, validator):
    schedule = make_jssp_3x3_baseline_schedule()

    broken = type(schedule)(
        case_id=schedule.case_id,
        operations=(
            *schedule.operations[:5],
            type(schedule.operations[5])(
                operation=schedule.operations[5].operation,
                start=6,
                end=10,
            ),
            *schedule.operations[6:],
        ),
    )

    admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=broken,
    )

    assert not admission.ok
    assert [v.violation_type for v in admission.schedule_violations] == ["machine_overlap"]
    assert admission.validation is None
    assert admission.records == []
    assert admission.committed == []

    assert await store.get_record(T, "rid:jssp:jssp-3x3-smoke:schedule:J2:O3") is None
