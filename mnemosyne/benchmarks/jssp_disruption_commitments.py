from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.api.commitments import (
    CommitmentApiResult,
    fire_active_commitment,
    get_active_commitment_status,
    register_active_commitment,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    DisruptedOperation,
    JSSPBaselineSchedule,
    MachineBreakdown,
    affected_operations,
    commitment_id_for_operation,
    dependency_scope_for_operation,
)
from mnemosyne.core.commitments import ActiveCommitment


@dataclass(frozen=True)
class JSSPCommitmentRegistrationResult:
    commitment_id: str
    operation_key: str
    result: CommitmentApiResult


@dataclass(frozen=True)
class JSSPCommitmentFireResult:
    commitment_id: str
    operation_key: str
    disrupted_operation: DisruptedOperation
    result: CommitmentApiResult


@dataclass(frozen=True)
class JSSPDisruptionSignalResult:
    disruption: MachineBreakdown
    affected: list[DisruptedOperation]
    fired: list[JSSPCommitmentFireResult]

    @property
    def affected_operation_keys(self) -> list[str]:
        return [item.key for item in self.affected]

    @property
    def fired_commitment_ids(self) -> list[str]:
        return [item.commitment_id for item in self.fired]

    @property
    def ok(self) -> bool:
        return all(item.result.ok for item in self.fired)


def active_commitment_for_scheduled_operation(
    *,
    schedule: JSSPBaselineSchedule,
    scheduled_operation: Any,
) -> ActiveCommitment:
    scope = dependency_scope_for_operation(
        case_id=schedule.case_id,
        operation=scheduled_operation,
    )

    scope["entity_id"] = scope["schedule_entity_id"]

    return ActiveCommitment(
        commitment_id=commitment_id_for_operation(
            case_id=schedule.case_id,
            operation=scheduled_operation,
        ),
        commitment_type="jssp_machine_availability_guard",
        description=(
            "Scheduled operation must remain executable on its assigned machine "
            "during its scheduled time window."
        ),
        dependency_scope=scope,
    )


async def register_schedule_commitments(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    rid_prefix: str | None = None,
    batch_prefix: str | None = None,
) -> list[JSSPCommitmentRegistrationResult]:
    results: list[JSSPCommitmentRegistrationResult] = []

    for scheduled_operation in schedule.operations:
        commitment = active_commitment_for_scheduled_operation(
            schedule=schedule,
            scheduled_operation=scheduled_operation,
        )

        safe_key = scheduled_operation.key.replace(":", "-")
        result = await register_active_commitment(
            store=store,
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            commitment=commitment,
            rid=f"{rid_prefix or 'rid:jssp:commitment-register'}:{safe_key}",
            batch_id=f"{batch_prefix or 'batch:jssp:commitment-register'}:{safe_key}",
        )

        results.append(
            JSSPCommitmentRegistrationResult(
                commitment_id=commitment.commitment_id,
                operation_key=scheduled_operation.key,
                result=result,
            )
        )

    return results


async def signal_machine_breakdown(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
    rid_prefix: str | None = None,
    batch_prefix: str | None = None,
) -> JSSPDisruptionSignalResult:
    affected = affected_operations(schedule, disruption)
    fired: list[JSSPCommitmentFireResult] = []

    for item in affected:
        commitment_id = commitment_id_for_operation(
            case_id=schedule.case_id,
            operation=item.scheduled_operation,
        )

        safe_key = item.key.replace(":", "-")
        result = await fire_active_commitment(
            store=store,
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            commitment_id=commitment_id,
            reason=(
                f"{disruption.reason}:"
                f"{disruption.machine_id}:"
                f"{disruption.unavailable_start}-{disruption.unavailable_end}"
            ),
            rid=f"{rid_prefix or 'rid:jssp:breakdown-fire'}:{safe_key}",
            batch_id=f"{batch_prefix or 'batch:jssp:breakdown-fire'}:{safe_key}",
        )

        fired.append(
            JSSPCommitmentFireResult(
                commitment_id=commitment_id,
                operation_key=item.key,
                disrupted_operation=item,
                result=result,
            )
        )

    return JSSPDisruptionSignalResult(
        disruption=disruption,
        affected=affected,
        fired=fired,
    )


async def active_commitment_statuses(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str,
    commitment_ids: list[str],
) -> dict[str, str | None]:
    statuses: dict[str, str | None] = {}

    for commitment_id in commitment_ids:
        statuses[commitment_id] = await get_active_commitment_status(
            store=store,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            commitment_id=commitment_id,
        )

    return statuses
