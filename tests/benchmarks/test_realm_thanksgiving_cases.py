from __future__ import annotations

from tests.benchmarks.realm_thanksgiving_cases import (
    thanksgiving_dynamic_scenario,
    thanksgiving_static_scenario,
)


def test_thanksgiving_static_scenario_materializes_core_entities():
    scenario = thanksgiving_static_scenario()

    assert scenario.case_id == "P6"
    assert scenario.short_name == "TD-static"
    assert scenario.mode == "static"
    assert scenario.dinner_deadline == "18:00"

    assert [member.name for member in scenario.family_members] == [
        "Sarah",
        "James",
        "Emily",
        "Michael",
        "Grandma",
    ]
    assert [member.name for member in scenario.host_members] == ["Sarah"]
    assert [member.name for member in scenario.pickup_members] == ["Emily", "Grandma"]

    james = next(member for member in scenario.family_members if member.name == "James")
    assert james.arrival_location == "BOS"
    assert james.arrival_time == "13:00"
    assert james.must_rent_car

    assert [(task.task, task.duration_minutes) for task in scenario.meal_tasks] == [
        ("turkey", 240),
        ("side_dishes", 120),
    ]
    assert [task.task for task in scenario.supervised_tasks] == ["turkey"]

    assert scenario.travel_times_minutes == {
        "home-BOS": 60,
        "BOS-Grandma": 60,
        "home-Grandma": 30,
    }


def test_thanksgiving_dynamic_scenario_materializes_james_delay():
    scenario = thanksgiving_dynamic_scenario()

    assert scenario.case_id == "P9"
    assert scenario.short_name == "TD-dynamic"
    assert scenario.mode == "dynamic"
    assert scenario.disruption is not None

    delay = scenario.disruption
    assert delay.person == "James"
    assert delay.original_arrival_time == "13:00"
    assert delay.new_arrival_time == "16:00"
    assert delay.notice_time_est == "10:00"

    assert delay.delay_minutes == 180
    assert delay.early_notice_minutes == 180


def test_thanksgiving_dynamic_scenario_preserves_static_operational_entities():
    static = thanksgiving_static_scenario()
    dynamic = thanksgiving_dynamic_scenario()

    assert [member.name for member in dynamic.family_members] == [
        member.name
        for member in static.family_members
    ]
    assert dynamic.meal_tasks == static.meal_tasks
    assert dynamic.travel_times_minutes == static.travel_times_minutes

    assert any(
        "React when delay notice is received" in requirement
        for requirement in dynamic.requirements
    )
    assert any(
        "Original P6 cooking and pickup constraints remain active" in constraint
        for constraint in dynamic.constraints
    )
