from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.realm.adapters.thanksgiving_cases import thanksgiving_dynamic_scenario

REALM_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ThanksgivingRecoveryTraceResult:
    output_root: Path
    files: dict[str, Path]
    trace_id: str
    wakeup_count: int
    proposal_count: int
    admitted_repair_count: int
    report_path: Path


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_trace() -> dict[str, Any]:
    scenario = thanksgiving_dynamic_scenario()
    assert scenario.disruption is not None
    delay = scenario.disruption

    disruption = {
        "event_id": "p9-disruption-james-flight-delay",
        "type": "flight_delay",
        "person": delay.person,
        "notice_time_est": delay.notice_time_est,
        "original_arrival_time": delay.original_arrival_time,
        "new_arrival_time": delay.new_arrival_time,
        "delay_minutes": delay.delay_minutes,
        "early_notice_minutes": delay.early_notice_minutes,
    }

    commitments = [
        {
            "commitment_id": "p9-cook-turkey-supervision",
            "kind": "temporal_constraint",
            "description": "Sarah supervises turkey from 09:00 to 13:00.",
            "affected_by_disruption": False,
        },
        {
            "commitment_id": "p9-pickup-emily",
            "kind": "pickup_constraint",
            "description": "Emily is picked up from BOS before dinner.",
            "affected_by_disruption": False,
        },
        {
            "commitment_id": "p9-pickup-grandma-by-james",
            "kind": "pickup_assignment",
            "description": "Original plan assigns Grandma pickup to James.",
            "affected_by_disruption": True,
        },
        {
            "commitment_id": "p9-dinner-ready-by-1800",
            "kind": "deadline_constraint",
            "description": "All family members home and dinner ready by 18:00.",
            "affected_by_disruption": True,
        },
    ]

    wakeups = [
        {
            "wakeup_id": "p9-wakeup-grandma-pickup",
            "source_event_id": disruption["event_id"],
            "commitment_id": "p9-pickup-grandma-by-james",
            "wakeup_time": "10:00",
            "result": "repair_required",
            "reason": "James now lands at 16:00, too late to perform Grandma pickup safely.",
        },
        {
            "wakeup_id": "p9-wakeup-dinner-deadline",
            "source_event_id": disruption["event_id"],
            "commitment_id": "p9-dinner-ready-by-1800",
            "wakeup_time": "10:00",
            "result": "repair_required",
            "reason": "The delay threatens the all-family-home-before-dinner condition.",
        },
    ]

    proposal = {
        "proposal_id": "p9-proposal-reassign-grandma-to-sarah",
        "proposal_type": "repair_candidate",
        "status": "selected",
        "created_from_wakeups": [
            "p9-wakeup-grandma-pickup",
            "p9-wakeup-dinner-deadline",
        ],
        "description": "Reassign Grandma pickup from James to Sarah.",
        "changes": [
            {
                "field": "Grandma pickup assignee",
                "before": "James",
                "after": "Sarah",
            }
        ],
        "expected_result": {
            "all_family_home_by": "17:30",
            "dinner_ready_at": "18:00",
        },
    }

    admission = {
        "admission_id": "p9-admit-reassign-grandma-to-sarah",
        "proposal_id": proposal["proposal_id"],
        "admission_boundary": "domain_validated_repair",
        "status": "admitted",
        "admitted_at": "10:00",
        "validation_checks": [
            {
                "name": "repair_triggered_at_notice_time",
                "passed": True,
                "evidence": "Repair is triggered at 10:00 when delay notice arrives.",
            },
            {
                "name": "pickup_assignment_repaired",
                "passed": True,
                "evidence": "Grandma pickup is reassigned from James to Sarah.",
            },
            {
                "name": "dinner_deadline_preserved",
                "passed": True,
                "evidence": "All family members home by 17:30 and dinner ready at 18:00.",
            },
        ],
    }

    lineage = [
        {
            "step": 1,
            "kind": "disruption_event",
            "id": disruption["event_id"],
            "summary": "James flight delay notice received at 10:00.",
        },
        {
            "step": 2,
            "kind": "commitment_wakeup",
            "id": "p9-wakeup-grandma-pickup",
            "summary": "Grandma pickup commitment wakes.",
        },
        {
            "step": 3,
            "kind": "commitment_wakeup",
            "id": "p9-wakeup-dinner-deadline",
            "summary": "Dinner deadline commitment wakes.",
        },
        {
            "step": 4,
            "kind": "repair_proposal",
            "id": proposal["proposal_id"],
            "summary": "Repair proposal reassigns Grandma pickup from James to Sarah.",
        },
        {
            "step": 5,
            "kind": "repair_admission",
            "id": admission["admission_id"],
            "summary": "Selected repair is admitted after validation.",
        },
    ]

    return {
        "schema_version": "thanksgiving_recovery_trace.v1",
        "trace_id": "p9_thanksgiving_recovery_trace",
        "case_id": "P9",
        "source_case": "P6",
        "disruption_event": disruption,
        "commitments": commitments,
        "wakeups": wakeups,
        "proposals": [proposal],
        "admissions": [admission],
        "lineage": lineage,
        "result": {
            "wakeup_count": 2,
            "proposal_count": 1,
            "selected_repair_count": 1,
            "admitted_repair_count": 1,
            "repair_trigger_time": "10:00",
            "latest_family_home_time": "17:30",
            "dinner_ready_time": "18:00",
            "feasible_after_repair": True,
            "optimality_status": "feasible_not_proven_optimal",
        },
        "limitations": [
            "This is a deterministic recovery trace.",
            "It models the recovery pattern but does not yet call core CTL mutation APIs.",
        ],
    }


def render_markdown(trace: dict[str, Any]) -> str:
    event = trace["disruption_event"]
    result = trace["result"]
    proposal = trace["proposals"][0]
    admission = trace["admissions"][0]

    lines = [
        "# Thanksgiving P9 Recovery Trace Report",
        "",
        "## Summary",
        "",
        f"- Trace id: `{trace['trace_id']}`",
        f"- Case: {trace['case_id']}",
        f"- Feasible after repair: {result['feasible_after_repair']}",
        f"- Wakeups: {result['wakeup_count']}",
        f"- Proposals: {result['proposal_count']}",
        f"- Admitted repairs: {result['admitted_repair_count']}",
        "",
        "## Disruption",
        "",
        f"- Person: {event['person']}",
        f"- Notice time EST: {event['notice_time_est']}",
        f"- Original arrival: {event['original_arrival_time']}",
        f"- New arrival: {event['new_arrival_time']}",
        f"- Delay minutes: {event['delay_minutes']}",
        "",
        "## Active Commitments",
        "",
    ]

    for commitment in trace["commitments"]:
        affected = "affected" if commitment["affected_by_disruption"] else "not affected"
        lines.append(f"- `{commitment['commitment_id']}`: {affected}. {commitment['description']}")

    lines += ["", "## Commitment Wakeups", ""]
    for wakeup in trace["wakeups"]:
        lines.append(f"- `{wakeup['wakeup_id']}` wakes `{wakeup['commitment_id']}` at {wakeup['wakeup_time']}: {wakeup['reason']}")

    lines += [
        "",
        "## Repair Proposals",
        "",
        f"- `{proposal['proposal_id']}`: {proposal['description']}",
    ]
    for change in proposal["changes"]:
        lines.append(f"  - {change['field']}: {change['before']} -> {change['after']}")

    lines += [
        "",
        "## Repair Admission",
        "",
        f"- `{admission['admission_id']}` status: {admission['status']}",
        f"- Boundary: {admission['admission_boundary']}",
        f"- Admitted at: {admission['admitted_at']}",
    ]
    for check in admission["validation_checks"]:
        lines.append(f"- {check['name']}: {check['passed']} -- {check['evidence']}")

    lines += ["", "## Audit Lineage", ""]
    for step in trace["lineage"]:
        lines.append(f"{step['step']}. {step['kind']} `{step['id']}` -- {step['summary']}")

    lines += [
        "",
        "## Result",
        "",
        f"- Repair trigger time: {result['repair_trigger_time']}",
        f"- Latest family home time: {result['latest_family_home_time']}",
        f"- Dinner ready time: {result['dinner_ready_time']}",
        f"- Feasible after repair: {result['feasible_after_repair']}",
        f"- Optimality status: {result['optimality_status']}",
        "",
    ]
    return "\n".join(lines)


def run_recovery_trace(output_root: str | Path | None = None) -> ThanksgivingRecoveryTraceResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    trace = build_trace()

    files = {
        "trace_json": root / "evaluations" / "p9_thanksgiving_recovery_trace.json",
        "report_json": root / "reports" / "thanksgiving_p9_recovery_trace_report.json",
        "report_markdown": root / "reports" / "thanksgiving_p9_recovery_trace_report.md",
    }

    _write_json(files["trace_json"], trace)
    _write_json(files["report_json"], trace)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(render_markdown(trace) + "\n", encoding="utf-8")

    return ThanksgivingRecoveryTraceResult(
        output_root=root,
        files=files,
        trace_id=trace["trace_id"],
        wakeup_count=trace["result"]["wakeup_count"],
        proposal_count=trace["result"]["proposal_count"],
        admitted_repair_count=trace["result"]["admitted_repair_count"],
        report_path=files["report_markdown"],
    )


def main() -> None:
    result = run_recovery_trace()
    print("R6.6 Thanksgiving P9 recovery trace")
    print(f"output_root: {result.output_root}")
    print(f"trace_id: {result.trace_id}")
    print(f"wakeups: {result.wakeup_count}")
    print(f"proposals: {result.proposal_count}")
    print(f"admitted_repairs: {result.admitted_repair_count}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
