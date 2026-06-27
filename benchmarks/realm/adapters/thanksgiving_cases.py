from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from benchmarks.realm.adapters.realm_case_loader import load_realm_bench_cases


@dataclass(frozen=True)
class ThanksgivingMealTask:
    task: str
    duration_minutes: int
    requires_supervision: bool = False


@dataclass(frozen=True)
class ThanksgivingFamilyMember:
    name: str
    role: str | None = None
    arrival_location: str | None = None
    arrival_time: str | None = None
    origin: str | None = None
    location: str | None = None
    requires_pickup: bool = False
    must_rent_car: bool = False
    host: bool = False


@dataclass(frozen=True)
class ThanksgivingFlightDelay:
    person: str
    original_arrival_time: str
    new_arrival_time: str
    notice_time_est: str

    @property
    def original_arrival_minutes(self) -> int:
        return _hhmm_to_minutes(self.original_arrival_time)

    @property
    def new_arrival_minutes(self) -> int:
        return _hhmm_to_minutes(self.new_arrival_time)

    @property
    def notice_minutes(self) -> int:
        return _hhmm_to_minutes(self.notice_time_est)

    @property
    def delay_minutes(self) -> int:
        return self.new_arrival_minutes - self.original_arrival_minutes

    @property
    def early_notice_minutes(self) -> int:
        return self.original_arrival_minutes - self.notice_minutes


@dataclass(frozen=True)
class ThanksgivingScenario:
    case_id: str
    name: str
    mode: str
    short_name: str
    family_members: list[ThanksgivingFamilyMember]
    meal_tasks: list[ThanksgivingMealTask]
    travel_times_minutes: dict[str, int]
    requirements: list[str]
    constraints: list[str]
    disruption: ThanksgivingFlightDelay | None = None

    @property
    def pickup_members(self) -> list[ThanksgivingFamilyMember]:
        return [
            member
            for member in self.family_members
            if member.requires_pickup
        ]

    @property
    def host_members(self) -> list[ThanksgivingFamilyMember]:
        return [
            member
            for member in self.family_members
            if member.host
        ]

    @property
    def supervised_tasks(self) -> list[ThanksgivingMealTask]:
        return [
            task
            for task in self.meal_tasks
            if task.requires_supervision
        ]

    @property
    def dinner_deadline(self) -> str:
        return "18:00"


def _hhmm_to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _member_from_raw(raw: dict[str, Any]) -> ThanksgivingFamilyMember:
    return ThanksgivingFamilyMember(
        name=raw["name"],
        role=raw.get("role"),
        arrival_location=raw.get("arrival_location"),
        arrival_time=raw.get("arrival_time"),
        origin=raw.get("origin"),
        location=raw.get("location"),
        requires_pickup=bool(raw.get("requires_pickup", False)),
        must_rent_car=bool(raw.get("must_rent_car", False)),
        host=bool(raw.get("host", False)),
    )


def _meal_task_from_raw(raw: dict[str, Any]) -> ThanksgivingMealTask:
    return ThanksgivingMealTask(
        task=raw["task"],
        duration_minutes=int(raw["duration_minutes"]),
        requires_supervision=bool(raw.get("requires_supervision", False)),
    )


def _flight_delay_from_raw(raw: dict[str, Any]) -> ThanksgivingFlightDelay:
    return ThanksgivingFlightDelay(
        person=raw["person"],
        original_arrival_time=raw["original_arrival_time"],
        new_arrival_time=raw["new_arrival_time"],
        notice_time_est=raw["notice_time_est"],
    )


def thanksgiving_static_scenario() -> ThanksgivingScenario:
    case = load_realm_bench_cases().by_id("P6")
    return _scenario_from_case(case)


def thanksgiving_dynamic_scenario() -> ThanksgivingScenario:
    case = load_realm_bench_cases().by_id("P9")
    static_case = load_realm_bench_cases().by_id("P6")

    merged = dict(static_case)
    merged.update(
        {
            "case_id": case["case_id"],
            "name": case["name"],
            "short_name": case["short_name"],
            "mode": case["mode"],
            "requirements": case["requirements"],
            "constraints": case["constraints"],
            "disruptions": case["disruptions"],
        }
    )
    return _scenario_from_case(merged)


def _scenario_from_case(case: dict[str, Any]) -> ThanksgivingScenario:
    entities = case["entities"]
    disruptions = case.get("disruptions") or []

    return ThanksgivingScenario(
        case_id=case["case_id"],
        name=case["name"],
        mode=case["mode"],
        short_name=case["short_name"],
        family_members=[
            _member_from_raw(member)
            for member in entities["family_members"]
        ],
        meal_tasks=[
            _meal_task_from_raw(task)
            for task in entities["meal_tasks"]
        ],
        travel_times_minutes=dict(case["travel_times_minutes"]),
        requirements=list(case["requirements"]),
        constraints=list(case["constraints"]),
        disruption=_flight_delay_from_raw(disruptions[0]) if disruptions else None,
    )
