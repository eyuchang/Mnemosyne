from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.api.proposal_packages import (
    ProposalPackageApiResult,
    create_recovery_proposal_package,
    emit_package_backed_proposal,
    package_to_dict,
)
from mnemosyne.benchmarks.jssp_disruption_commitments import (
    JSSPDisruptionSignalResult,
    active_commitment_for_scheduled_operation,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    DisruptedOperation,
    JSSPBaselineSchedule,
    JSSPScheduledOperation,
    MachineBreakdown,
    dependency_scope_for_operation,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_APP_ID,
    JSSP_APP_VERSION,
    JSSP_FSM_ID,
    JSSP_FSM_VERSION,
    JSSP_POLICY_ID,
    JSSP_POLICY_VERSION,
    JSSP_SCHEMA_ID,
    JSSP_SCHEMA_VERSION,
)
from mnemosyne.core.models import TransitionCandidate


@dataclass(frozen=True)
class JSSPRecoveryProposal:
    operation_key: str
    commitment_id: str
    proposal_ref: str
    package_id: str
    proposal_scope: dict[str, Any]
    package: Any
    result: ProposalPackageApiResult

    @property
    def ok(self) -> bool:
        return self.result.ok

    @property
    def candidate_rids(self) -> list[str]:
        return self.package.candidate_rids

    def package_dict(self) -> dict[str, Any]:
        return package_to_dict(self.package)


@dataclass(frozen=True)
class JSSPRecoveryProposalBatch:
    schedule: JSSPBaselineSchedule
    disruption: MachineBreakdown
    proposals: list[JSSPRecoveryProposal]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.proposals)

    @property
    def proposal_refs(self) -> list[str]:
        return [item.proposal_ref for item in self.proposals]

    @property
    def package_ids(self) -> list[str]:
        return [item.package_id for item in self.proposals]

    @property
    def commitment_ids(self) -> list[str]:
        return [item.commitment_id for item in self.proposals]

    @property
    def operation_keys(self) -> list[str]:
        return [item.operation_key for item in self.proposals]

    @property
    def candidate_rids(self) -> list[str]:
        return [
            rid
            for proposal in self.proposals
            for rid in proposal.candidate_rids
        ]


def _safe_operation_key(operation_key: str) -> str:
    return operation_key.replace(":", "-")


def proposal_scope_for_disrupted_operation(
    *,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    disrupted_operation: DisruptedOperation,
) -> dict[str, Any]:
    scheduled = disrupted_operation.scheduled_operation
    scope = dependency_scope_for_operation(
        case_id=schedule.case_id,
        operation=scheduled,
    )
    scope["entity_id"] = scope["schedule_entity_id"]
    return scope


def repair_details_for_disrupted_operation(
    *,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    disrupted_operation: DisruptedOperation,
    candidate_start: int | None = None,
) -> dict[str, Any]:
    scheduled = disrupted_operation.scheduled_operation
    resolved_start = (
        max(scheduled.start, disruption.unavailable_end)
        if candidate_start is None
        else candidate_start
    )
    resolved_end = resolved_start + scheduled.duration

    return {
        "case_id": schedule.case_id,
        "operation_key": scheduled.key,
        "job_id": scheduled.job_id,
        "operation_id": scheduled.operation_id,
        "machine_id": scheduled.machine_id,
        "original_start": scheduled.start,
        "original_end": scheduled.end,
        "duration": scheduled.duration,
        "disruption": disruption.to_attrs(),
        "repair_intent": "reschedule_after_machine_recovers",
        "candidate_start_not_before": max(scheduled.start, disruption.unavailable_end),
        "candidate_start": resolved_start,
        "candidate_end": resolved_end,
        "source_schedule_makespan": schedule.makespan,
        "domain_mutation": False,
    }


def repair_candidate_for_disrupted_operation(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    disrupted_operation: DisruptedOperation,
    candidate_start: int | None = None,
) -> TransitionCandidate:
    scheduled = disrupted_operation.scheduled_operation
    details = repair_details_for_disrupted_operation(
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=disrupted_operation,
        candidate_start=candidate_start,
    )

    repaired = JSSPScheduledOperation(
        operation=scheduled.operation,
        start=details["candidate_start"],
        end=details["candidate_end"],
    )

    safe_key = _safe_operation_key(scheduled.key)
    rid = f"rid:jssp:{schedule.case_id}:repair-candidate:{safe_key}"

    attrs_after = repaired.to_attrs()
    attrs_after["case_id"] = schedule.case_id
    attrs_after["operation_key"] = scheduled.key
    attrs_after["machine"] = scheduled.machine_id
    attrs_after["machine_id"] = scheduled.machine_id
    attrs_after["baseline_makespan"] = schedule.makespan
    attrs_after["repair_source_disruption_id"] = disruption.event_id
    attrs_after["repair_domain_mutation"] = False

    return TransitionCandidate(
        rid=rid,
        op_id=f"op:{rid}",
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        binding_id=f"binding:jssp:{schedule.case_id}:repair",
        eid=details["case_id"] and proposal_scope_for_disrupted_operation(
            schedule=schedule,
            disruption=disruption,
            disrupted_operation=disrupted_operation,
        )["entity_id"],
        fsm=JSSP_FSM_ID,
        fsm_version=JSSP_FSM_VERSION,
        state_before="scheduled",
        state_after="scheduled",
        action_type="reschedule",
        triggers=[],
        dependencies=[],
        metadata={
            "case_id": schedule.case_id,
            "operation_key": scheduled.key,
            "job_id": scheduled.job_id,
            "operation_id": scheduled.operation_id,
            "machine_id": scheduled.machine_id,
            "repair_source_disruption_id": disruption.event_id,
            "domain_mutation": False,
        },
        extension={
            "kind": "jssp.repair_candidate",
            "attrs_after": attrs_after,
            "repair_details": details,
        },
        app_id=JSSP_APP_ID,
        app_version=JSSP_APP_VERSION,
        schema_id=JSSP_SCHEMA_ID,
        schema_version=JSSP_SCHEMA_VERSION,
        policy_id=JSSP_POLICY_ID,
        policy_version=JSSP_POLICY_VERSION,
        validator_id=None,
        validator_version=None,
    )


def recovery_package_for_disrupted_operation(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    disrupted_operation: DisruptedOperation,
    created_from_record_id: str,
    candidate_start: int | None = None,
    created_by: str = "jssp_recovery_proposal_adapter",
) -> Any:
    scheduled = disrupted_operation.scheduled_operation
    safe_key = _safe_operation_key(scheduled.key)

    proposal_ref = f"proposal:jssp:{schedule.case_id}:repair:{safe_key}"
    package_id = f"pkg:jssp:{schedule.case_id}:repair:{safe_key}"

    repair_candidate = repair_candidate_for_disrupted_operation(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        schedule=schedule,
        disruption=disruption,
        disrupted_operation=disrupted_operation,
        candidate_start=candidate_start,
    )

    return create_recovery_proposal_package(
        package_id=package_id,
        commitment_id=disrupted_operation.commitment_id,
        proposal_ref=proposal_ref,
        proposal_scope=proposal_scope_for_disrupted_operation(
            schedule=schedule,
            disruption=disruption,
            disrupted_operation=disrupted_operation,
        ),
        proposed_domain_candidates=[repair_candidate],
        rationale=(
            "Machine breakdown overlaps the scheduled operation. "
            "Carry a concrete inert reschedule candidate; do not mutate "
            "domain schedule state until a separate domain CTL admission."
        ),
        validator_context={
            "repair_details": repair_details_for_disrupted_operation(
                schedule=schedule,
                disruption=disruption,
                disrupted_operation=disrupted_operation,
                candidate_start=candidate_start,
            )
        },
        created_from_record_id=created_from_record_id,
        created_by=created_by,
    )


async def emit_recovery_proposals_for_disruption(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    disruption_signal: JSSPDisruptionSignalResult,
    rid_prefix: str | None = None,
    batch_prefix: str | None = None,
) -> JSSPRecoveryProposalBatch:
    proposals: list[JSSPRecoveryProposal] = []
    next_start_by_machine: dict[str, int] = {
        disruption_signal.disruption.machine_id: disruption_signal.disruption.unavailable_end
    }

    for fired in disruption_signal.fired:
        scheduled = fired.disrupted_operation.scheduled_operation
        safe_key = _safe_operation_key(scheduled.key)

        candidate_start = max(
            scheduled.start,
            disruption_signal.disruption.unavailable_end,
            next_start_by_machine.get(scheduled.machine_id, scheduled.start),
        )
        next_start_by_machine[scheduled.machine_id] = candidate_start + scheduled.duration

        package = recovery_package_for_disrupted_operation(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            schedule=schedule,
            disruption=disruption_signal.disruption,
            disrupted_operation=fired.disrupted_operation,
            created_from_record_id=fired.result.records[-1].rid,
            candidate_start=candidate_start,
        )

        commitment = active_commitment_for_scheduled_operation(
            schedule=schedule,
            scheduled_operation=scheduled,
        )

        result = await emit_package_backed_proposal(
            store=store,
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            package=package,
            commitment=commitment,
            rid=f"{rid_prefix or 'rid:jssp:recovery-proposal'}:{safe_key}",
            batch_id=f"{batch_prefix or 'batch:jssp:recovery-proposal'}:{safe_key}",
        )

        proposals.append(
            JSSPRecoveryProposal(
                operation_key=scheduled.key,
                commitment_id=fired.commitment_id,
                proposal_ref=package.proposal_ref,
                package_id=package.package_id,
                proposal_scope=package.proposal_scope,
                package=package,
                result=result,
            )
        )

    return JSSPRecoveryProposalBatch(
        schedule=schedule,
        disruption=disruption_signal.disruption,
        proposals=proposals,
    )
