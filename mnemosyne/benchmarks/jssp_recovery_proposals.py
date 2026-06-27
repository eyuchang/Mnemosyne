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
    MachineBreakdown,
    dependency_scope_for_operation,
)


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
) -> dict[str, Any]:
    scheduled = disrupted_operation.scheduled_operation

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
        "source_schedule_makespan": schedule.makespan,
        "domain_mutation": False,
    }


def recovery_package_for_disrupted_operation(
    *,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    disrupted_operation: DisruptedOperation,
    created_from_record_id: str,
    created_by: str = "jssp_recovery_proposal_adapter",
) -> Any:
    scheduled = disrupted_operation.scheduled_operation
    safe_key = _safe_operation_key(scheduled.key)

    proposal_ref = f"proposal:jssp:{schedule.case_id}:repair:{safe_key}"
    package_id = f"pkg:jssp:{schedule.case_id}:repair:{safe_key}"

    return create_recovery_proposal_package(
        package_id=package_id,
        commitment_id=disrupted_operation.commitment_id,
        proposal_ref=proposal_ref,
        proposal_scope=proposal_scope_for_disrupted_operation(
            schedule=schedule,
            disruption=disruption,
            disrupted_operation=disrupted_operation,
        ),
        rationale=(
            "Machine breakdown overlaps the scheduled operation. "
            "Propose an inert rescheduling repair package; do not mutate "
            "domain schedule state until a separate domain CTL admission."
        ),
        validator_context={
            "repair_details": repair_details_for_disrupted_operation(
                schedule=schedule,
                disruption=disruption,
                disrupted_operation=disrupted_operation,
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

    for fired in disruption_signal.fired:
        scheduled = fired.disrupted_operation.scheduled_operation
        safe_key = _safe_operation_key(scheduled.key)

        package = recovery_package_for_disrupted_operation(
            schedule=schedule,
            disruption=disruption_signal.disruption,
            disrupted_operation=fired.disrupted_operation,
            created_from_record_id=fired.result.records[-1].rid,
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
