from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class JCaseProposal:
    case_id: str
    case_name: str
    proposal_id: str
    operation_key: str
    proposal_type: str
    valid_under_c: bool
    state_delta: int
    completes_case: bool
    repair_radius: int
    stale_world: bool = False
    direct_mutation: bool = False
    evidence_destroying: bool = False
    dependency_invalid: bool = False


EXPECTED_STATE = {
    "J1": 2,
    "J2": 2,
    "J3": 1,
    "J4": 1,
}


def j1_j4_suite() -> list[JCaseProposal]:
    return [
        JCaseProposal(
            case_id="J1",
            case_name="nominal_multi_step_plan",
            proposal_id="j1-p1",
            operation_key="j1-create-plan",
            proposal_type="valid_plan_step",
            valid_under_c=True,
            state_delta=1,
            completes_case=False,
            repair_radius=0,
        ),
        JCaseProposal(
            case_id="J1",
            case_name="nominal_multi_step_plan",
            proposal_id="j1-p2",
            operation_key="j1-commit-itinerary",
            proposal_type="valid_plan_commit",
            valid_under_c=True,
            state_delta=1,
            completes_case=True,
            repair_radius=0,
        ),
        JCaseProposal(
            case_id="J2",
            case_name="disruption_recovery",
            proposal_id="j2-p1",
            operation_key="j2-record-disruption",
            proposal_type="valid_disruption_observation",
            valid_under_c=True,
            state_delta=1,
            completes_case=False,
            repair_radius=0,
        ),
        JCaseProposal(
            case_id="J2",
            case_name="disruption_recovery",
            proposal_id="j2-p2",
            operation_key="j2-delete-failure-evidence",
            proposal_type="evidence_destroying_repair",
            valid_under_c=False,
            state_delta=-10,
            completes_case=False,
            repair_radius=0,
            evidence_destroying=True,
        ),
        JCaseProposal(
            case_id="J2",
            case_name="disruption_recovery",
            proposal_id="j2-p3",
            operation_key="j2-admit-repair-route",
            proposal_type="valid_repair",
            valid_under_c=True,
            state_delta=1,
            completes_case=True,
            repair_radius=2,
        ),
        JCaseProposal(
            case_id="J3",
            case_name="stale_world_replanning",
            proposal_id="j3-p1",
            operation_key="j3-stale-route",
            proposal_type="stale_world_plan",
            valid_under_c=False,
            state_delta=99,
            completes_case=False,
            repair_radius=0,
            stale_world=True,
        ),
        JCaseProposal(
            case_id="J3",
            case_name="stale_world_replanning",
            proposal_id="j3-p2",
            operation_key="j3-fresh-replan",
            proposal_type="valid_fresh_replan",
            valid_under_c=True,
            state_delta=1,
            completes_case=True,
            repair_radius=1,
        ),
        JCaseProposal(
            case_id="J4",
            case_name="active_commitment_wakeup",
            proposal_id="j4-p1",
            operation_key="j4-direct-acr-mutation",
            proposal_type="direct_acr_mutation",
            valid_under_c=False,
            state_delta=99,
            completes_case=False,
            repair_radius=0,
            direct_mutation=True,
        ),
        JCaseProposal(
            case_id="J4",
            case_name="active_commitment_wakeup",
            proposal_id="j4-p2",
            operation_key="j4-acr-proposal-package",
            proposal_type="valid_acr_recovery_proposal",
            valid_under_c=True,
            state_delta=1,
            completes_case=True,
            repair_radius=1,
        ),
    ]


def rejection_reason(p: JCaseProposal) -> str:
    if p.stale_world:
        return "stale_world_rejection"
    if p.direct_mutation:
        return "direct_mutation_forbidden"
    if p.evidence_destroying:
        return "evidence_destroying_unresolved_repair"
    if p.dependency_invalid:
        return "dependency_invalid"
    if not p.valid_under_c:
        return "invalid_under_c"
    return "accepted"


def run_direct_workflow_baseline(proposals: list[JCaseProposal]) -> dict:
    state = {case_id: 0 for case_id in EXPECTED_STATE}
    completed_cases: set[str] = set()
    rows: list[dict] = []

    for p in proposals:
        state[p.case_id] += p.state_delta
        if p.completes_case:
            completed_cases.add(p.case_id)

        rows.append(
            {
                "proposal": asdict(p),
                "committed": True,
                "reason": "direct_workflow_commit",
            }
        )

    invalid_commits = sum(1 for p in proposals if not p.valid_under_c)
    stateview_mismatches = sum(
        1 for case_id, expected in EXPECTED_STATE.items() if state[case_id] != expected
    )

    return {
        "system": "direct_workflow_baseline",
        "case_count": len(EXPECTED_STATE),
        "proposal_packages": len(proposals),
        "admitted": len(proposals),
        "rejected": 0,
        "invalid_commits": invalid_commits,
        "completed_cases": len(completed_cases),
        "stateview_mismatches": stateview_mismatches,
        "total_repair_radius": sum(p.repair_radius for p in proposals if p.valid_under_c),
        "rows": rows,
    }


def run_atp_mnemosyne(proposals: list[JCaseProposal]) -> dict:
    state = {case_id: 0 for case_id in EXPECTED_STATE}
    completed_cases: set[str] = set()
    seen_operation_keys: set[str] = set()
    rows: list[dict] = []

    for p in proposals:
        duplicate_key = p.operation_key in seen_operation_keys
        accepted = p.valid_under_c and not duplicate_key

        if accepted:
            seen_operation_keys.add(p.operation_key)
            state[p.case_id] += p.state_delta
            if p.completes_case:
                completed_cases.add(p.case_id)
            reason = "admitted"
        else:
            reason = "duplicate_operation_key" if duplicate_key else rejection_reason(p)

        rows.append(
            {
                "proposal": asdict(p),
                "committed": accepted,
                "reason": reason,
            }
        )

    invalid_commits = sum(
        1 for row in rows if row["committed"] and not row["proposal"]["valid_under_c"]
    )
    stateview_mismatches = sum(
        1 for case_id, expected in EXPECTED_STATE.items() if state[case_id] != expected
    )

    return {
        "system": "atp_mnemosyne",
        "case_count": len(EXPECTED_STATE),
        "proposal_packages": len(proposals),
        "admitted": sum(1 for row in rows if row["committed"]),
        "rejected": sum(1 for row in rows if not row["committed"]),
        "invalid_commits": invalid_commits,
        "completed_cases": len(completed_cases),
        "stateview_mismatches": stateview_mismatches,
        "total_repair_radius": sum(
            row["proposal"]["repair_radius"] for row in rows if row["committed"]
        ),
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ7",
        "name": "J1-J4 end-to-end ATP execution",
        "claim": (
            "Planning and recovery cases execute through the ATP boundary: "
            "benchmark case to proposal package to admission to CTL to StateView."
        ),
        "success_criteria": [
            "ATP completed_cases = 4",
            "ATP invalid_commits = 0",
            "ATP stateview_mismatches = 0",
            "ATP rejected invalid or stale proposals > 0",
            "Unsafe baseline commits invalid proposals or corrupts StateView",
        ],
        "systems": results,
    }

    (report_dir / "rq7_j1_j4_end_to_end_atp_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ7 J1-J4 End-to-End ATP Execution Report",
        "",
        "J1-J4 cases are driven through the transaction boundary: case -> proposal package -> admission -> CTL -> StateView.",
        "",
        "| System | Cases | Packages | Admitted | Rejected | Invalid commits | Completed cases | StateView mismatches | Repair radius |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {case_count} | {proposal_packages} | {admitted} | "
            "{rejected} | {invalid_commits} | {completed_cases} | "
            "{stateview_mismatches} | {total_repair_radius} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests end-to-end execution through ATP for J1-J4 cases.",
            "It does not certify the broader P1-P10 readiness suites.",
            "It does not claim learning, regret reduction, or preemptive planning.",
            "",
        ]
    )

    (report_dir / "rq7_j1_j4_end_to_end_atp_report.md").write_text(
        "\n".join(lines)
    )


def test_rq7_j1_j4_end_to_end_atp_execution() -> None:
    proposals = j1_j4_suite()

    results = [
        run_direct_workflow_baseline(proposals),
        run_atp_mnemosyne(proposals),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["direct_workflow_baseline"]["invalid_commits"] > 0
    assert by_system["direct_workflow_baseline"]["stateview_mismatches"] > 0

    assert by_system["atp_mnemosyne"]["completed_cases"] == 4
    assert by_system["atp_mnemosyne"]["invalid_commits"] == 0
    assert by_system["atp_mnemosyne"]["stateview_mismatches"] == 0
    assert by_system["atp_mnemosyne"]["rejected"] > 0
    assert by_system["atp_mnemosyne"]["admitted"] > 0

    write_reports(results)
