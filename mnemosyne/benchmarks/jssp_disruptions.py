from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JSSPOperation:
    job_id: str
    operation_id: str
    machine_id: str
    duration: int
    sequence_index: int

    @property
    def key(self) -> str:
        return f"{self.job_id}:{self.operation_id}"


@dataclass(frozen=True)
class JSSPScheduledOperation:
    operation: JSSPOperation
    start: int
    end: int

    @property
    def job_id(self) -> str:
        return self.operation.job_id

    @property
    def operation_id(self) -> str:
        return self.operation.operation_id

    @property
    def machine_id(self) -> str:
        return self.operation.machine_id

    @property
    def duration(self) -> int:
        return self.operation.duration

    @property
    def key(self) -> str:
        return self.operation.key

    def overlaps(self, start: int, end: int) -> bool:
        return self.start < end and start < self.end

    def to_attrs(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "operation_id": self.operation_id,
            "machine_id": self.machine_id,
            "duration": self.duration,
            "sequence_index": self.operation.sequence_index,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class JSSPBaselineSchedule:
    case_id: str
    operations: tuple[JSSPScheduledOperation, ...]

    @property
    def makespan(self) -> int:
        if not self.operations:
            return 0
        return max(op.end for op in self.operations)

    @property
    def operation_keys(self) -> list[str]:
        return sorted(op.key for op in self.operations)

    def operations_by_machine(self, machine_id: str) -> list[JSSPScheduledOperation]:
        return sorted(
            [op for op in self.operations if op.machine_id == machine_id],
            key=lambda op: (op.start, op.end, op.key),
        )

    def operations_by_job(self, job_id: str) -> list[JSSPScheduledOperation]:
        return sorted(
            [op for op in self.operations if op.job_id == job_id],
            key=lambda op: (op.operation.sequence_index, op.start, op.end),
        )

    def to_attrs(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "makespan": self.makespan,
            "operations": [op.to_attrs() for op in self.operations],
        }


@dataclass(frozen=True)
class MachineBreakdown:
    event_id: str
    machine_id: str
    unavailable_start: int
    unavailable_end: int
    reason: str = "machine_breakdown"

    @property
    def duration(self) -> int:
        return self.unavailable_end - self.unavailable_start

    def to_attrs(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "machine_id": self.machine_id,
            "unavailable_start": self.unavailable_start,
            "unavailable_end": self.unavailable_end,
            "duration": self.duration,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DisruptedOperation:
    scheduled_operation: JSSPScheduledOperation
    disruption: MachineBreakdown
    reason: str

    @property
    def key(self) -> str:
        return self.scheduled_operation.key

    @property
    def commitment_id(self) -> str:
        return commitment_id_for_operation(
            case_id=self.disruption.event_id.split(":")[0],
            operation=self.scheduled_operation,
        )

    def to_attrs(self) -> dict[str, Any]:
        return {
            "operation": self.scheduled_operation.to_attrs(),
            "disruption": self.disruption.to_attrs(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class JSSPScheduleViolation:
    violation_type: str
    message: str
    operation_keys: tuple[str, ...]


def commitment_id_for_operation(
    *,
    case_id: str,
    operation: JSSPScheduledOperation,
) -> str:
    return (
        f"jssp:{case_id}:commitment:"
        f"{operation.job_id}:{operation.operation_id}:machine:{operation.machine_id}"
    )


def dependency_scope_for_operation(
    *,
    case_id: str,
    operation: JSSPScheduledOperation,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "job_id": operation.job_id,
        "operation_id": operation.operation_id,
        "machine_id": operation.machine_id,
        "operation_key": operation.key,
        "schedule_entity_id": schedule_entity_id(case_id, operation.key),
    }


def schedule_entity_id(case_id: str, operation_key: str) -> str:
    return f"jssp:{case_id}:operation:{operation_key}"


def validate_baseline_schedule(
    schedule: JSSPBaselineSchedule,
) -> list[JSSPScheduleViolation]:
    violations: list[JSSPScheduleViolation] = []

    for op in schedule.operations:
        if op.end - op.start != op.duration:
            violations.append(
                JSSPScheduleViolation(
                    violation_type="duration_mismatch",
                    message="scheduled duration does not match operation duration",
                    operation_keys=(op.key,),
                )
            )

        if op.start < 0 or op.end <= op.start:
            violations.append(
                JSSPScheduleViolation(
                    violation_type="invalid_time_window",
                    message="operation has invalid start/end window",
                    operation_keys=(op.key,),
                )
            )

    machines = sorted({op.machine_id for op in schedule.operations})
    for machine_id in machines:
        machine_ops = schedule.operations_by_machine(machine_id)
        for left, right in zip(machine_ops, machine_ops[1:]):
            if left.end > right.start:
                violations.append(
                    JSSPScheduleViolation(
                        violation_type="machine_overlap",
                        message=f"machine {machine_id} has overlapping operations",
                        operation_keys=(left.key, right.key),
                    )
                )

    jobs = sorted({op.job_id for op in schedule.operations})
    for job_id in jobs:
        job_ops = schedule.operations_by_job(job_id)
        for left, right in zip(job_ops, job_ops[1:]):
            if left.end > right.start:
                violations.append(
                    JSSPScheduleViolation(
                        violation_type="job_precedence_violation",
                        message=f"job {job_id} operation order is violated",
                        operation_keys=(left.key, right.key),
                    )
                )

    return violations


def affected_operations(
    schedule: JSSPBaselineSchedule,
    disruption: MachineBreakdown,
) -> list[DisruptedOperation]:
    affected: list[DisruptedOperation] = []

    for op in schedule.operations_by_machine(disruption.machine_id):
        if op.overlaps(disruption.unavailable_start, disruption.unavailable_end):
            affected.append(
                DisruptedOperation(
                    scheduled_operation=op,
                    disruption=disruption,
                    reason="operation_overlaps_machine_unavailability",
                )
            )

    return affected


def make_jssp_3x3_baseline_schedule(
    *,
    case_id: str = "jssp-3x3-smoke",
) -> JSSPBaselineSchedule:
    """Return a small deterministic feasible 3x3 JSSP baseline schedule.

    Jobs:
        J1: M1/3 -> M2/2 -> M3/2
        J2: M2/2 -> M3/1 -> M1/4
        J3: M3/4 -> M1/3 -> M2/1

    Makespan:
        11
    """

    def op(job: str, name: str, machine: str, duration: int, index: int) -> JSSPOperation:
        return JSSPOperation(
            job_id=job,
            operation_id=name,
            machine_id=machine,
            duration=duration,
            sequence_index=index,
        )

    operations = (
        JSSPScheduledOperation(op("J1", "O1", "M1", 3, 1), start=0, end=3),
        JSSPScheduledOperation(op("J1", "O2", "M2", 2, 2), start=3, end=5),
        JSSPScheduledOperation(op("J1", "O3", "M3", 2, 3), start=5, end=7),
        JSSPScheduledOperation(op("J2", "O1", "M2", 2, 1), start=0, end=2),
        JSSPScheduledOperation(op("J2", "O2", "M3", 1, 2), start=4, end=5),
        JSSPScheduledOperation(op("J2", "O3", "M1", 4, 3), start=7, end=11),
        JSSPScheduledOperation(op("J3", "O1", "M3", 4, 1), start=0, end=4),
        JSSPScheduledOperation(op("J3", "O2", "M1", 3, 2), start=4, end=7),
        JSSPScheduledOperation(op("J3", "O3", "M2", 1, 3), start=7, end=8),
    )

    return JSSPBaselineSchedule(case_id=case_id, operations=operations)


def make_machine_breakdown_for_3x3_smoke(
    *,
    case_id: str = "jssp-3x3-smoke",
) -> MachineBreakdown:
    return MachineBreakdown(
        event_id=f"{case_id}:breakdown:M1:5-9",
        machine_id="M1",
        unavailable_start=5,
        unavailable_end=9,
    )
