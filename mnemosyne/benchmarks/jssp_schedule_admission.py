from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.benchmarks.jssp_disruptions import (
    JSSPBaselineSchedule,
    JSSPScheduledOperation,
    JSSPScheduleViolation,
    schedule_entity_id,
    validate_baseline_schedule,
)
from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult

JSSP_APP_ID = "jssp"
JSSP_APP_VERSION = "1.0"
JSSP_FSM_ID = "JobOpFSM"
JSSP_FSM_VERSION = "1.0"
JSSP_SCHEMA_ID = "jssp.transition"
JSSP_SCHEMA_VERSION = "1.0"
JSSP_POLICY_ID = "jssp.default"
JSSP_POLICY_VERSION = "1.0"


@dataclass(frozen=True)
class JSSPBaselineScheduleAdmission:
    schedule: JSSPBaselineSchedule
    batch: CommitBatch
    schedule_violations: list[JSSPScheduleViolation]
    validation: ValidationResult | None
    records: list[CTLRecord]
    committed: list[CTLRecord]

    @property
    def ok(self) -> bool:
        return (
            not self.schedule_violations
            and self.validation is not None
            and self.validation.ok
            and len(self.committed) == len(self.batch.candidates)
        )

    @property
    def committed_rids(self) -> list[str]:
        return [record.rid for record in self.committed]

    @property
    def committed_entity_ids(self) -> list[str]:
        return [record.eid for record in self.committed]

    @property
    def committed_only_jssp_schedule_fsm(self) -> bool:
        return all(record.fsm == JSSP_FSM_ID for record in self.committed)


def schedule_operation_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    case_id: str,
    scheduled_operation: JSSPScheduledOperation,
    binding_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
) -> TransitionCandidate:
    operation_key = scheduled_operation.key
    record_id = rid or f"rid:jssp:{case_id}:schedule:{operation_key}"

    attrs = scheduled_operation.to_attrs()
    attrs["case_id"] = case_id
    attrs["operation_key"] = operation_key
    attrs["baseline_makespan"] = None

    return TransitionCandidate(
        rid=record_id,
        op_id=op_id or f"op:{record_id}",
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        binding_id=binding_id or f"binding:jssp:{case_id}",
        eid=schedule_entity_id(case_id, operation_key),
        fsm=JSSP_FSM_ID,
        fsm_version=JSSP_FSM_VERSION,
        state_before="ready",
        state_after="scheduled",
        action_type="schedule",
        triggers=[],
        dependencies=[],
        metadata={
            "case_id": case_id,
            "operation_key": operation_key,
            "job_id": scheduled_operation.job_id,
            "operation_id": scheduled_operation.operation_id,
            "machine_id": scheduled_operation.machine_id,
        },
        extension={
            "kind": "jssp.schedule_operation",
            "attrs_after": attrs,
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


def baseline_schedule_candidates(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    binding_id: str | None = None,
) -> list[TransitionCandidate]:
    candidates: list[TransitionCandidate] = []

    for scheduled_operation in schedule.operations:
        candidate = schedule_operation_candidate(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            case_id=schedule.case_id,
            scheduled_operation=scheduled_operation,
            binding_id=binding_id,
        )

        attrs = dict(candidate.extension.get("attrs_after", {}))
        attrs["baseline_makespan"] = schedule.makespan

        candidate.extension["attrs_after"] = attrs
        candidates.append(candidate)

    return candidates


def baseline_schedule_commit_batch(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    schedule: JSSPBaselineSchedule,
    batch_id: str | None = None,
    binding_id: str | None = None,
) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id or f"batch:jssp:{schedule.case_id}:baseline-schedule",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        tx_group_id=tx_group_id,
        candidates=baseline_schedule_candidates(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
            schedule=schedule,
            binding_id=binding_id,
        ),
    )


async def admit_baseline_schedule(
    *,
    store: Any,
    validator: Any,
    tenant_id: str,
    schedule: JSSPBaselineSchedule,
    workflow_id: str | None = None,
    tx_group_id: str | None = None,
    batch_id: str | None = None,
    binding_id: str | None = None,
) -> JSSPBaselineScheduleAdmission:
    resolved_workflow_id = workflow_id or f"workflow:jssp:{schedule.case_id}"
    resolved_tx_group_id = tx_group_id or f"tx:jssp:{schedule.case_id}:baseline"

    batch = baseline_schedule_commit_batch(
        tenant_id=tenant_id,
        tx_group_id=resolved_tx_group_id,
        workflow_id=resolved_workflow_id,
        schedule=schedule,
        batch_id=batch_id,
        binding_id=binding_id,
    )

    schedule_violations = validate_baseline_schedule(schedule)
    if schedule_violations:
        return JSSPBaselineScheduleAdmission(
            schedule=schedule,
            batch=batch,
            schedule_violations=schedule_violations,
            validation=None,
            records=[],
            committed=[],
        )

    validation = await validator.validate_batch(batch, store)
    if not validation.ok:
        return JSSPBaselineScheduleAdmission(
            schedule=schedule,
            batch=batch,
            schedule_violations=[],
            validation=validation,
            records=[],
            committed=[],
        )

    records = await validator.records_from_batch(batch, store)
    committed = await store.commit_batch(batch, records)

    return JSSPBaselineScheduleAdmission(
        schedule=schedule,
        batch=batch,
        schedule_violations=[],
        validation=validation,
        records=records,
        committed=committed,
    )
