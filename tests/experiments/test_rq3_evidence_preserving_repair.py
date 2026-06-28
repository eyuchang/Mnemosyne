from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


REPAIR_AGENTS = [
    "naive_repair_agent",
    "workflow_repair_agent",
    "llm_like_repair_agent",
    "adversarial_repair_agent",
]


@dataclass(frozen=True)
class RepairProposal:
    proposal_id: str
    repair_agent: str
    workload: str
    syntactically_valid: bool
    triggered_by_evidence_id: str
    evidence_exists_before: bool
    evidence_exists_after: bool
    failure_exists_before: bool
    failure_exists_after: bool
    action: str


@dataclass(frozen=True)
class EvidenceCheck:
    accepted: bool
    reason: str


def evidence_preserving_admission(proposal: RepairProposal) -> EvidenceCheck:
    if not proposal.syntactically_valid:
        return EvidenceCheck(False, "malformed_repair")

    if not proposal.triggered_by_evidence_id:
        return EvidenceCheck(False, "missing_trigger_evidence")

    if not proposal.evidence_exists_before:
        return EvidenceCheck(False, "trigger_evidence_missing_before_repair")

    failure_resolved = proposal.failure_exists_before and not proposal.failure_exists_after
    evidence_preserved = proposal.evidence_exists_after

    if failure_resolved or evidence_preserved:
        return EvidenceCheck(True, "accepted")

    return EvidenceCheck(False, "evidence_destroying_unresolved_repair")


def repair_suite() -> list[RepairProposal]:
    proposals: list[RepairProposal] = []

    for agent in REPAIR_AGENTS:
        base = f"{agent}:failure-42"

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:delete-failing-test",
                repair_agent=agent,
                workload="delete_failing_test",
                syntactically_valid=True,
                triggered_by_evidence_id="test:test_scheduler_deadline",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=True,
                action="delete_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:suppress-alert",
                repair_agent=agent,
                workload="suppress_alert",
                syntactically_valid=True,
                triggered_by_evidence_id="alert:machine_breakdown",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=True,
                action="suppress_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:compensate-diagnostic",
                repair_agent=agent,
                workload="compensate_diagnostic_record",
                syntactically_valid=True,
                triggered_by_evidence_id="diagnostic:material_shortage",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=True,
                action="compensate_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:overwrite-observation",
                repair_agent=agent,
                workload="overwrite_stale_world_observation",
                syntactically_valid=True,
                triggered_by_evidence_id="observation:world_version_mismatch",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=True,
                action="overwrite_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:hide-violated-guard",
                repair_agent=agent,
                workload="hide_violated_guard",
                syntactically_valid=True,
                triggered_by_evidence_id="guard:capacity_violation",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=True,
                action="hide_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:resolve-and-archive",
                repair_agent=agent,
                workload="resolve_failure_then_archive_evidence",
                syntactically_valid=True,
                triggered_by_evidence_id="test:repairable_deadline_violation",
                evidence_exists_before=True,
                evidence_exists_after=False,
                failure_exists_before=True,
                failure_exists_after=False,
                action="resolve_failure",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:preserve-evidence",
                repair_agent=agent,
                workload="repair_attempt_preserves_evidence",
                syntactically_valid=True,
                triggered_by_evidence_id="trace:machine_breakdown",
                evidence_exists_before=True,
                evidence_exists_after=True,
                failure_exists_before=True,
                failure_exists_after=True,
                action="preserve_evidence",
            )
        )

        proposals.append(
            RepairProposal(
                proposal_id=f"{base}:malformed",
                repair_agent=agent,
                workload="malformed_repair",
                syntactically_valid=False,
                triggered_by_evidence_id="trace:malformed",
                evidence_exists_before=True,
                evidence_exists_after=True,
                failure_exists_before=True,
                failure_exists_after=True,
                action="malformed",
            )
        )

    return proposals


def run_system(system_name: str, proposals: list[RepairProposal]) -> dict:
    rows: list[dict] = []

    for proposal in proposals:
        check = evidence_preserving_admission(proposal)

        if system_name == "naive_repair":
            # Naive repair considers the visible failure cleared if the evidence
            # disappears, even when the underlying failure remains.
            committed = proposal.syntactically_valid and (
                not proposal.evidence_exists_after or not proposal.failure_exists_after
            )
            decision = "committed_if_visible_failure_cleared" if committed else "rejected"
        elif system_name == "workflow_without_evidence_rule":
            # A conventional workflow baseline accepts any syntactically valid
            # repair action; it does not know that trigger evidence is protected.
            committed = proposal.syntactically_valid
            decision = "committed_if_syntactically_valid" if committed else "rejected"
        elif system_name == "atp_mnemosyne":
            committed = check.accepted
            decision = "admitted" if committed else "rejected_before_commit"
        else:
            raise ValueError(f"unknown system: {system_name}")

        evidence_destroying_unresolved = (
            proposal.evidence_exists_before
            and not proposal.evidence_exists_after
            and proposal.failure_exists_after
        )

        rows.append(
            {
                "system": system_name,
                "proposal": asdict(proposal),
                "accepted_by_evidence_rule": check.accepted,
                "evidence_rule_reason": check.reason,
                "committed": committed,
                "decision": decision,
                "evidence_destroying_unresolved": evidence_destroying_unresolved,
            }
        )

    evidence_destroying_repairs = sum(
        1 for row in rows if row["committed"] and row["evidence_destroying_unresolved"]
    )
    valid_repairs_committed = sum(
        1
        for row in rows
        if row["committed"]
        and row["accepted_by_evidence_rule"]
        and not row["evidence_destroying_unresolved"]
    )
    rejected_evidence_destroying_repairs = sum(
        1
        for row in rows
        if not row["committed"] and row["evidence_destroying_unresolved"]
    )
    rejected_valid_repairs = sum(
        1
        for row in rows
        if not row["committed"]
        and row["accepted_by_evidence_rule"]
        and not row["evidence_destroying_unresolved"]
    )

    return {
        "system": system_name,
        "repair_agent_count": len(REPAIR_AGENTS),
        "workload_count_per_agent": len(rows) // len(REPAIR_AGENTS),
        "proposal_count": len(rows),
        "evidence_destroying_repairs": evidence_destroying_repairs,
        "rejected_evidence_destroying_repairs": rejected_evidence_destroying_repairs,
        "valid_repairs_committed": valid_repairs_committed,
        "rejected_valid_repairs": rejected_valid_repairs,
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ3",
        "name": "Evidence-preserving repair",
        "claim": (
            "Repairs triggered by evidence cannot be admitted if they merely "
            "destroy, suppress, compensate, overwrite, or obscure that evidence "
            "while leaving the underlying failure unresolved."
        ),
        "success_criteria": [
            "ATP evidence_destroying_repairs = 0",
            "At least one unsafe baseline has evidence_destroying_repairs > 0",
            "ATP valid_repairs_committed > 0",
        ],
        "systems": results,
    }

    json_path = report_dir / "rq3_evidence_preserving_repair_report.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    lines = [
        "# RQ3 Evidence-Preserving Repair Report",
        "",
        "A repair triggered by evidence must either resolve the underlying failure or preserve the evidence that justified the repair.",
        "",
        "| System | Repair agents | Workloads per agent | Evidence-destroying repairs | Rejected evidence-destroying repairs | Valid repairs committed |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {repair_agent_count} | {workload_count_per_agent} | "
            "{evidence_destroying_repairs} | {rejected_evidence_destroying_repairs} | "
            "{valid_repairs_committed} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests evidence-preserving repair safety.",
            "It does not claim learning, regret reduction, or preemptive planning.",
            "The guarantee is relative to the declared evidence and failure predicates.",
            "",
        ]
    )

    md_path = report_dir / "rq3_evidence_preserving_repair_report.md"
    md_path.write_text("\n".join(lines))


def test_rq3_evidence_preserving_repair() -> None:
    proposals = repair_suite()

    results = [
        run_system("naive_repair", proposals),
        run_system("workflow_without_evidence_rule", proposals),
        run_system("atp_mnemosyne", proposals),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["naive_repair"]["evidence_destroying_repairs"] > 0
    assert by_system["workflow_without_evidence_rule"]["evidence_destroying_repairs"] > 0

    assert by_system["atp_mnemosyne"]["evidence_destroying_repairs"] == 0
    assert by_system["atp_mnemosyne"]["rejected_evidence_destroying_repairs"] > 0
    assert by_system["atp_mnemosyne"]["valid_repairs_committed"] > 0
    assert by_system["atp_mnemosyne"]["rejected_valid_repairs"] == 0

    write_reports(results)
