from __future__ import annotations

from mnemosyne.benchmarks.jssp_disruptions import (
    affected_operations,
    commitment_id_for_operation,
    dependency_scope_for_operation,
    make_jssp_3x3_baseline_schedule,
    make_machine_breakdown_for_3x3_smoke,
    schedule_entity_id,
    validate_baseline_schedule,
)


def test_jssp_3x3_baseline_schedule_is_feasible():
    schedule = make_jssp_3x3_baseline_schedule()

    assert schedule.case_id == "jssp-3x3-smoke"
    assert schedule.makespan == 11
    assert len(schedule.operations) == 9
    assert validate_baseline_schedule(schedule) == []

    assert schedule.operation_keys == [
        "J1:O1",
        "J1:O2",
        "J1:O3",
        "J2:O1",
        "J2:O2",
        "J2:O3",
        "J3:O1",
        "J3:O2",
        "J3:O3",
    ]


def test_jssp_3x3_machine_breakdown_finds_affected_operations():
    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    affected = affected_operations(schedule, disruption)

    assert [item.key for item in affected] == ["J3:O2", "J2:O3"]
    assert [item.reason for item in affected] == [
        "operation_overlaps_machine_unavailability",
        "operation_overlaps_machine_unavailability",
    ]

    assert affected[0].scheduled_operation.start == 4
    assert affected[0].scheduled_operation.end == 7
    assert affected[1].scheduled_operation.start == 7
    assert affected[1].scheduled_operation.end == 11


def test_jssp_operation_dependency_scope_and_commitment_ids_are_stable():
    schedule = make_jssp_3x3_baseline_schedule()
    operation = schedule.operations_by_machine("M1")[1]

    assert operation.key == "J3:O2"

    assert schedule_entity_id(schedule.case_id, operation.key) == (
        "jssp:jssp-3x3-smoke:operation:J3:O2"
    )

    assert commitment_id_for_operation(
        case_id=schedule.case_id,
        operation=operation,
    ) == "jssp:jssp-3x3-smoke:commitment:J3:O2:machine:M1"

    assert dependency_scope_for_operation(
        case_id=schedule.case_id,
        operation=operation,
    ) == {
        "case_id": "jssp-3x3-smoke",
        "job_id": "J3",
        "operation_id": "O2",
        "machine_id": "M1",
        "operation_key": "J3:O2",
        "schedule_entity_id": "jssp:jssp-3x3-smoke:operation:J3:O2",
    }


def test_jssp_schedule_validation_detects_machine_overlap():
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

    violations = validate_baseline_schedule(broken)

    assert [v.violation_type for v in violations] == ["machine_overlap"]
    assert violations[0].operation_keys == ("J3:O2", "J2:O3")
