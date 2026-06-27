from __future__ import annotations

import pytest

from mnemosyne.api.audit import audit_active_commitments, audit_recovery_lineage
from mnemosyne.benchmarks.jssp_disruption_commitments import (
    active_commitment_statuses,
    register_schedule_commitments,
    signal_machine_breakdown,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    DisruptedOperation,
    make_jssp_3x3_baseline_schedule,
    make_machine_breakdown_for_3x3_smoke,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_recovery_proposals import (
    emit_recovery_proposals_for_disruption,
    proposal_scope_for_disrupted_operation,
    recovery_package_for_disrupted_operation,
    repair_candidate_for_disrupted_operation,
    repair_details_for_disrupted_operation,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
)

T = "tenant:r60-jssp"
W = "workflow:r60-jssp"
G = "tx:r60-jssp"


async def _seed_disrupted_schedule(store, validator):
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

    return schedule, disruption, registrations, signal


def test_jssp_recovery_proposal_scope_is_dependency_bounded_and_details_are_inert():
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    item = DisruptedOperation(
        scheduled_operation=schedule.operations_by_machine("M1")[1],
        disruption=disruption,
        reason="operation_overlaps_machine_unavailability",
    )

    scope = proposal_scope_for_disrupted_operation(
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=item,
    )
    details = repair_details_for_disrupted_operation(
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=item,
    )

    assert scope == {
        "case_id": "jssp-3x3-smoke",
        "job_id": "J3",
        "operation_id": "O2",
        "machine_id": "M1",
        "operation_key": "J3:O2",
        "schedule_entity_id": "jssp:jssp-3x3-smoke:operation:J3:O2",
        "entity_id": "jssp:jssp-3x3-smoke:operation:J3:O2",
    }

    assert details["case_id"] == "jssp-3x3-smoke"
    assert details["operation_key"] == "J3:O2"
    assert details["machine_id"] == "M1"
    assert details["original_start"] == 4
    assert details["original_end"] == 7
    assert details["candidate_start_not_before"] == 9
    assert details["candidate_start"] == 9
    assert details["candidate_end"] == 12
    assert details["repair_intent"] == "reschedule_after_machine_recovers"
    assert details["domain_mutation"] is False


def test_jssp_repair_candidate_is_concrete_domain_candidate_but_inert():
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    item = DisruptedOperation(
        scheduled_operation=schedule.operations_by_machine("M1")[1],
        disruption=disruption,
        reason="operation_overlaps_machine_unavailability",
    )

    candidate = repair_candidate_for_disrupted_operation(
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=item,
        candidate_start=9,
    )

    assert candidate.rid == "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2"
    assert candidate.eid == "jssp:jssp-3x3-smoke:operation:J3:O2"
    assert candidate.fsm == "JobOpFSM"
    assert candidate.state_before == "scheduled"
    assert candidate.state_after == "scheduled"
    assert candidate.action_type == "reschedule"
    assert candidate.metadata["domain_mutation"] is False
    assert candidate.extension["attrs_after"]["start"] == 9
    assert candidate.extension["attrs_after"]["end"] == 12
    assert candidate.extension["attrs_after"]["duration"] == 3
    assert candidate.extension["attrs_after"]["repair_domain_mutation"] is False


def test_jssp_recovery_package_is_stable_and_contains_inert_repair_candidate():
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    item = DisruptedOperation(
        scheduled_operation=schedule.operations_by_machine("M1")[1],
        disruption=disruption,
        reason="operation_overlaps_machine_unavailability",
    )

    package = recovery_package_for_disrupted_operation(
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=item,
        created_from_record_id="rid:jssp:breakdown-fire:J3-O2",
        candidate_start=9,
    )

    assert package.package_id == "pkg:jssp:jssp-3x3-smoke:repair:J3-O2"
    assert package.proposal_ref == "proposal:jssp:jssp-3x3-smoke:repair:J3-O2"
    assert package.commitment_id == "jssp:jssp-3x3-smoke:commitment:J3:O2:machine:M1"
    assert package.proposal_scope["entity_id"] == "jssp:jssp-3x3-smoke:operation:J3:O2"
    assert package.validator_context["repair_details"]["domain_mutation"] is False
    assert package.validator_context["repair_details"]["candidate_start"] == 9
    assert package.validator_context["repair_details"]["candidate_end"] == 12
    assert package.created_from_record_id == "rid:jssp:breakdown-fire:J3-O2"

    assert package.is_inert
    assert package.candidate_rids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2"
    ]
    assert len(package.proposed_domain_candidates) == 1
    assert package.proposed_domain_candidates[0].action_type == "reschedule"


@pytest.mark.asyncio
async def test_jssp_recovery_proposals_move_fired_commitments_to_proposed(store, validator):
    schedule, disruption, registrations, signal = await _seed_disrupted_schedule(
        store,
        validator,
    )

    batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption_signal=signal,
    )

    assert batch.ok
    assert batch.operation_keys == ["J3:O2", "J2:O3"]
    assert batch.package_ids == [
        "pkg:jssp:jssp-3x3-smoke:repair:J3-O2",
        "pkg:jssp:jssp-3x3-smoke:repair:J2-O3",
    ]
    assert batch.proposal_refs == [
        "proposal:jssp:jssp-3x3-smoke:repair:J3-O2",
        "proposal:jssp:jssp-3x3-smoke:repair:J2-O3",
    ]
    assert batch.candidate_rids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]

    first_candidate = batch.proposals[0].package.proposed_domain_candidates[0]
    second_candidate = batch.proposals[1].package.proposed_domain_candidates[0]

    assert first_candidate.extension["attrs_after"]["start"] == 9
    assert first_candidate.extension["attrs_after"]["end"] == 12
    assert second_candidate.extension["attrs_after"]["start"] == 12
    assert second_candidate.extension["attrs_after"]["end"] == 16

    statuses = await active_commitment_statuses(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_ids=[item.commitment_id for item in registrations],
    )

    proposed = {
        cid
        for cid, status in statuses.items()
        if status == "proposed"
    }
    live = {
        cid
        for cid, status in statuses.items()
        if status == "live"
    }

    assert proposed == set(batch.commitment_ids)
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
        if row.status == "proposed"
    } == set(batch.commitment_ids)

    lineage = await audit_recovery_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert len(lineage) == 2
    assert [row.package_id for row in lineage] == batch.package_ids
    assert [row.proposal_ref for row in lineage] == batch.proposal_refs

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
        assert state_view.attrs["baseline_makespan"] == 11


@pytest.mark.asyncio
async def test_jssp_recovery_proposal_noops_when_no_commitments_fired(store, validator):
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

    signal = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )

    batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption_signal=signal,
    )

    assert batch.ok
    assert batch.proposals == []
    assert batch.package_ids == []
    assert batch.proposal_refs == []
    assert batch.candidate_rids == []

    statuses = await active_commitment_statuses(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_ids=[item.commitment_id for item in registrations],
    )
    assert set(statuses.values()) == {"live"}
