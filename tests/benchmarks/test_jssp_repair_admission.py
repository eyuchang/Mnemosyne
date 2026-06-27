from __future__ import annotations

import pytest

from mnemosyne.benchmarks.jssp_disruption_commitments import (
    register_schedule_commitments,
    signal_machine_breakdown,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    make_jssp_3x3_baseline_schedule,
    make_machine_breakdown_for_3x3_smoke,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_recovery_proposals import (
    emit_recovery_proposals_for_disruption,
)
from mnemosyne.benchmarks.jssp_repair_admission import (
    admit_repair_candidates_from_proposal_batch,
    repair_candidates_from_proposal_batch,
    selected_repair_commit_batch,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
)

T = "tenant:r61-jssp"
W = "workflow:r61-jssp"
G = "tx:r61-jssp"


async def _seed_recovery_proposal_batch(store, validator):
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

    signal = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )
    assert signal.ok

    proposal_batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption_signal=signal,
    )
    assert proposal_batch.ok

    return schedule, proposal_batch


def _candidate_windows(candidates):
    return [
        (
            candidate.eid,
            candidate.extension["attrs_after"]["start"],
            candidate.extension["attrs_after"]["end"],
        )
        for candidate in candidates
    ]


@pytest.mark.asyncio
async def test_selects_all_repair_candidates_from_proposal_batch(store, validator):
    schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)

    selected = repair_candidates_from_proposal_batch(proposal_batch)

    assert [candidate.rid for candidate in selected] == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]
    assert _candidate_windows(selected) == [
        ("jssp:jssp-3x3-smoke:operation:J3:O2", 9, 12),
        ("jssp:jssp-3x3-smoke:operation:J2:O3", 12, 16),
    ]

    # Selection alone must not mutate the schedule StateView.
    for op in schedule.operations:
        state_view = await store.get_state_view(
            T,
            schedule_entity_id(schedule.case_id, op.key),
            JSSP_FSM_ID,
        )
        assert state_view.state == "scheduled"
        assert state_view.attrs["start"] == op.start
        assert state_view.attrs["end"] == op.end


@pytest.mark.asyncio
async def test_selects_subset_of_repair_candidates_by_operation_key(store, validator):
    _, proposal_batch = await _seed_recovery_proposal_batch(store, validator)

    selected = repair_candidates_from_proposal_batch(
        proposal_batch,
        operation_keys=["J3:O2"],
    )

    assert [candidate.rid for candidate in selected] == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
    ]
    assert _candidate_windows(selected) == [
        ("jssp:jssp-3x3-smoke:operation:J3:O2", 9, 12),
    ]


@pytest.mark.asyncio
async def test_selected_repair_commit_batch_is_domain_ctl_batch(store, validator):
    _, proposal_batch = await _seed_recovery_proposal_batch(store, validator)
    selected = repair_candidates_from_proposal_batch(proposal_batch)

    batch = selected_repair_commit_batch(
        tenant_id=T,
        tx_group_id="tx:r61-jssp:repair-admission",
        workflow_id=W,
        selected_candidates=selected,
    )

    assert batch.batch_id == "batch:jssp:selected-repair-admission"
    assert batch.tenant_id == T
    assert batch.workflow_id == W
    assert batch.tx_group_id == "tx:r61-jssp:repair-admission"
    assert [candidate.action_type for candidate in batch.candidates] == [
        "reschedule",
        "reschedule",
    ]
    assert {candidate.fsm for candidate in batch.candidates} == {"JobOpFSM"}


@pytest.mark.asyncio
async def test_admitting_selected_repair_candidates_mutates_only_selected_stateviews(
    store,
    validator,
):
    schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)

    before_j3 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J3:O2"),
        JSSP_FSM_ID,
    )
    before_j2 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J2:O3"),
        JSSP_FSM_ID,
    )
    before_j1 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J1:O1"),
        JSSP_FSM_ID,
    )

    assert before_j3.attrs["start"] == 4
    assert before_j3.attrs["end"] == 7
    assert before_j2.attrs["start"] == 7
    assert before_j2.attrs["end"] == 11
    assert before_j1.attrs["start"] == 0
    assert before_j1.attrs["end"] == 3

    repair_admission = await admit_repair_candidates_from_proposal_batch(
        store=store,
        validator=validator,
        tenant_id=T,
        tx_group_id="tx:r61-jssp:repair-admission",
        workflow_id=W,
        proposal_batch=proposal_batch,
    )

    assert repair_admission.ok
    assert repair_admission.selected_rids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]
    assert repair_admission.committed_rids == repair_admission.selected_rids

    after_j3 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J3:O2"),
        JSSP_FSM_ID,
    )
    after_j2 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J2:O3"),
        JSSP_FSM_ID,
    )
    after_j1 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J1:O1"),
        JSSP_FSM_ID,
    )

    assert after_j3.state == "scheduled"
    assert after_j3.version == 2
    assert after_j3.attrs["start"] == 9
    assert after_j3.attrs["end"] == 12

    assert after_j2.state == "scheduled"
    assert after_j2.version == 2
    assert after_j2.attrs["start"] == 12
    assert after_j2.attrs["end"] == 16

    # Unselected operation remains unchanged.
    assert after_j1.version == 1
    assert after_j1.attrs["start"] == 0
    assert after_j1.attrs["end"] == 3


@pytest.mark.asyncio
async def test_finalizing_repaired_commitments_marks_selected_commitments_admitted(
    store,
    validator,
):
    from mnemosyne.api.audit import audit_active_commitments, list_unresolved_commitments
    from mnemosyne.benchmarks.jssp_repair_admission import (
        admit_and_finalize_repair_candidates_from_proposal_batch,
        finalize_commitments_for_repair_admission,
    )

    schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)

    unresolved_before = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert unresolved_before.count == 9

    repair_admission = await admit_repair_candidates_from_proposal_batch(
        store=store,
        validator=validator,
        tenant_id=T,
        tx_group_id="tx:r61-jssp:repair-admission",
        workflow_id=W,
        proposal_batch=proposal_batch,
    )
    assert repair_admission.ok

    unresolved_after_domain_repair = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    # Domain repair admission mutates schedule truth, but commitment finalization
    # is a separate commitment-FSM admission step.
    assert unresolved_after_domain_repair.count == 9

    finalization = await finalize_commitments_for_repair_admission(
        store=store,
        tenant_id=T,
        tx_group_id="tx:r61-jssp:commitment-finalization",
        workflow_id=W,
        proposal_batch=proposal_batch,
        repair_admission=repair_admission,
    )

    assert finalization.ok
    assert finalization.admitted_record_ids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]
    assert finalization.commitment_ids == proposal_batch.commitment_ids

    active_rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    admitted = {
        row.commitment_id
        for row in active_rows
        if row.status == "admitted"
    }
    live = {
        row.commitment_id
        for row in active_rows
        if row.status == "live"
    }

    assert admitted == set(proposal_batch.commitment_ids)
    assert len(live) == 7

    unresolved_after_finalization = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert unresolved_after_finalization.count == 7

    after_j3 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J3:O2"),
        JSSP_FSM_ID,
    )
    after_j2 = await store.get_state_view(
        T,
        schedule_entity_id(schedule.case_id, "J2:O3"),
        JSSP_FSM_ID,
    )

    assert after_j3.attrs["start"] == 9
    assert after_j3.attrs["end"] == 12
    assert after_j2.attrs["start"] == 12
    assert after_j2.attrs["end"] == 16


@pytest.mark.asyncio
async def test_admit_and_finalize_repair_candidates_one_step_helper(store, validator):
    from mnemosyne.api.audit import audit_active_commitments, list_unresolved_commitments
    from mnemosyne.benchmarks.jssp_repair_admission import (
        admit_and_finalize_repair_candidates_from_proposal_batch,
    )

    _, proposal_batch = await _seed_recovery_proposal_batch(store, validator)

    repair_admission, finalization = await admit_and_finalize_repair_candidates_from_proposal_batch(
        store=store,
        validator=validator,
        tenant_id=T,
        repair_tx_group_id="tx:r61-jssp:repair-admission",
        finalize_tx_group_id="tx:r61-jssp:commitment-finalization",
        workflow_id=W,
        proposal_batch=proposal_batch,
    )

    assert repair_admission.ok
    assert finalization.ok
    assert repair_admission.committed_rids == finalization.admitted_record_ids

    active_rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert {
        row.status
        for row in active_rows
    } == {"live", "admitted"}

    unresolved = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert unresolved.count == 7
