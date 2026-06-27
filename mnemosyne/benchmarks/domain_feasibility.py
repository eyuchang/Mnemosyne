# File: mnemosyne/benchmarks/domain_feasibility.py
#
# Purpose:
#   Runtime-side domain feasibility checks for benchmark admission.
#
# Design rule:
#   A solver certificate is not truth.
#   Runtime admission may independently reject a proposal before commit.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mnemosyne.benchmarks.models import BenchmarkCase
from mnemosyne.benchmarks.solver import PlanProposal


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class DomainFeasibilityReport:
    ok: bool
    app_id: str | None
    schema_id: str | None
    error_codes: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def _time_to_minutes(value: Any) -> int | None:
    if value is None:
        return None

    parts = str(value).split(":")
    if len(parts) != 2:
        return None

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None

    if hour < 0 or minute < 0 or minute >= 60:
        return None

    return hour * 60 + minute


def _attrs_after(step: Any) -> JsonDict:
    attrs = getattr(step, "attrs_after", None)
    if isinstance(attrs, dict):
        return attrs
    return {}


def check_domain_feasibility(
    benchmark_case: BenchmarkCase | None,
    plan_proposal: PlanProposal | None = None,
) -> DomainFeasibilityReport:
    """Independently check app-level feasibility before commit admission.

    This is deliberately narrow for the post-R2 review patch: it covers
    Campus Tour deadline and time-window feasibility using the proposed
    benchmark steps, independent of the solver certificate.
    """
    if benchmark_case is None:
        return DomainFeasibilityReport(
            ok=False,
            app_id=None,
            schema_id=None,
            error_codes=["DOMAIN_BENCHMARK_CASE_MISSING"],
            violations=["solver produced no benchmark case for domain feasibility check"],
        )

    if benchmark_case.app_id != "campus_tour":
        return DomainFeasibilityReport(
            ok=True,
            app_id=benchmark_case.app_id,
            schema_id=benchmark_case.schema_id,
        )

    violations: list[str] = []

    for step in benchmark_case.steps:
        attrs = _attrs_after(step)

        arrive = attrs.get("arrive")
        depart = attrs.get("depart")
        finish_time = attrs.get("finish_time")
        deadline = attrs.get("deadline")
        window_not_before = attrs.get("window_not_before")
        window_not_after = attrs.get("window_not_after")

        arrive_minutes = _time_to_minutes(arrive)
        depart_minutes = _time_to_minutes(depart)
        finish_minutes = _time_to_minutes(finish_time)
        deadline_minutes = _time_to_minutes(deadline)
        not_before_minutes = _time_to_minutes(window_not_before)
        not_after_minutes = _time_to_minutes(window_not_after)

        if arrive is not None and arrive_minutes is None:
            violations.append(f"INVALID_TIME:{step.step_id}:arrive={arrive}")

        if depart is not None and depart_minutes is None:
            violations.append(f"INVALID_TIME:{step.step_id}:depart={depart}")

        if (
            arrive_minutes is not None
            and depart_minutes is not None
            and depart_minutes < arrive_minutes
        ):
            violations.append(
                f"DEPART_BEFORE_ARRIVE:{step.step_id}:"
                f"arrive={arrive}:depart={depart}"
            )

        if (
            arrive_minutes is not None
            and not_before_minutes is not None
            and arrive_minutes < not_before_minutes
        ):
            violations.append(
                f"TIME_WINDOW_EARLY:{step.step_id}:"
                f"arrive={arrive}:not_before={window_not_before}"
            )

        if (
            depart_minutes is not None
            and not_after_minutes is not None
            and depart_minutes > not_after_minutes
        ):
            violations.append(
                f"TIME_WINDOW_LATE:{step.step_id}:"
                f"depart={depart}:not_after={window_not_after}"
            )

        if (
            finish_minutes is not None
            and deadline_minutes is not None
            and finish_minutes > deadline_minutes
        ):
            violations.append(
                f"DEADLINE_MISSED:{step.step_id}:"
                f"finish_time={finish_time}:deadline={deadline}"
            )

    if not violations:
        return DomainFeasibilityReport(
            ok=True,
            app_id=benchmark_case.app_id,
            schema_id=benchmark_case.schema_id,
        )

    return DomainFeasibilityReport(
        ok=False,
        app_id=benchmark_case.app_id,
        schema_id=benchmark_case.schema_id,
        error_codes=["DOMAIN_FEASIBILITY_REJECTED"],
        violations=violations,
    )
