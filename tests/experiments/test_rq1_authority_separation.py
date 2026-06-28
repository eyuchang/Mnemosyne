from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


CURRENT_WORLD_VERSION = 7
VALID_STATES = {"scheduled", "running", "repaired"}
PROPOSERS = ["random", "rule_based", "solver_like", "llm_like", "adversarial"]


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    proposer: str
    workload: str
    action: str
    observed_version: int
    tenant_id: str
    entity_id: str
    declared_scope_tenant_id: str
    declared_scope_entity_id: str
    new_state: str | None = None
    proposer_self_approval: bool = True
    malformed: bool = False
    destroys_evidence: bool = False
    failure_resolved: bool = True
    has_live_dependents: bool = False


@dataclass(frozen=True)
class AdmissionCheck:
    accepted: bool
    reason: str


def validate_under_constraint_set_c(
    proposal: Proposal,
    committed_ids: set[str],
) -> AdmissionCheck:
    if proposal.malformed:
        return AdmissionCheck(False, "malformed_proposal")

    if proposal.proposal_id in committed_ids:
        return AdmissionCheck(False, "replay_or_duplicate_proposal")

    if proposal.observed_version != CURRENT_WORLD_VERSION:
        return AdmissionCheck(False, "stale_world_assumption")

    if (
        proposal.tenant_id != proposal.declared_scope_tenant_id
        or proposal.entity_id != proposal.declared_scope_entity_id
    ):
        return AdmissionCheck(False, "scope_spoofing")

    if proposal.action == "transition":
        if proposal.new_state not in VALID_STATES:
            return AdmissionCheck(False, "invalid_transition")

    elif proposal.action == "compensate":
        if proposal.has_live_dependents:
            return AdmissionCheck(False, "unsafe_compensation_with_live_dependents")

    elif proposal.action == "repair":
        if proposal.destroys_evidence and not proposal.failure_resolved:
            return AdmissionCheck(False, "evidence_masking_repair")

    else:
        return AdmissionCheck(False, "unknown_action")

    return AdmissionCheck(True, "accepted")


def proposal_suite() -> list[Proposal]:
    proposals: list[Proposal] = []

    for proposer in PROPOSERS:
        base = f"{proposer}:job-17"

        proposals.append(
            Proposal(
                proposal_id=f"{base}:valid",
                proposer=proposer,
                workload="valid_transition",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                new_state="scheduled",
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:malformed",
                proposer=proposer,
                workload="malformed_proposal",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                new_state="scheduled",
                malformed=True,
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:invalid-transition",
                proposer=proposer,
                workload="invalid_transition",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                new_state="impossible_state",
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:stale-world",
                proposer=proposer,
                workload="stale_world",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION - 1,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                new_state="scheduled",
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:unsafe-compensation",
                proposer=proposer,
                workload="unsafe_compensation",
                action="compensate",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                has_live_dependents=True,
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:valid",
                proposer=proposer,
                workload="replay_duplicate",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                new_state="scheduled",
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:scope-spoof",
                proposer=proposer,
                workload="scope_spoofing",
                action="transition",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-b",
                declared_scope_entity_id="job-17",
                new_state="scheduled",
            )
        )

        proposals.append(
            Proposal(
                proposal_id=f"{base}:evidence-masking",
                proposer=proposer,
                workload="evidence_masking_repair",
                action="repair",
                observed_version=CURRENT_WORLD_VERSION,
                tenant_id="tenant-a",
                entity_id="job-17",
                declared_scope_tenant_id="tenant-a",
                declared_scope_entity_id="job-17",
                destroys_evidence=True,
                failure_resolved=False,
            )
        )

    return proposals


def run_system(system_name: str, proposals: list[Proposal]) -> dict:
    committed_ids: set[str] = set()
    rows: list[dict] = []

    for proposal in proposals:
        check = validate_under_constraint_set_c(proposal, committed_ids)

        if system_name == "raw_append":
            committed = True
            decision = "committed_without_admission"
        elif system_name == "self_validation":
            committed = proposal.proposer_self_approval
            decision = "self_approved" if committed else "self_rejected"
        elif system_name == "atp_mnemosyne":
            committed = check.accepted
            decision = "admitted" if committed else "rejected_before_commit"
        else:
            raise ValueError(f"unknown system: {system_name}")

        valid_under_c = check.accepted

        rows.append(
            {
                "system": system_name,
                "proposal": asdict(proposal),
                "valid_under_C": valid_under_c,
                "constraint_reason": check.reason,
                "committed": committed,
                "decision": decision,
            }
        )

        if committed:
            committed_ids.add(proposal.proposal_id)

    invalid_commits = sum(1 for row in rows if row["committed"] and not row["valid_under_C"])
    valid_commits = sum(1 for row in rows if row["committed"] and row["valid_under_C"])
    rejected_invalid = sum(
        1 for row in rows if not row["committed"] and not row["valid_under_C"]
    )
    rejected_valid = sum(
        1 for row in rows if not row["committed"] and row["valid_under_C"]
    )

    return {
        "system": system_name,
        "proposal_count": len(rows),
        "proposer_count": len(PROPOSERS),
        "workload_count_per_proposer": len(rows) // len(PROPOSERS),
        "invalid_commits": invalid_commits,
        "valid_commits": valid_commits,
        "rejected_invalid_proposals": rejected_invalid,
        "rejected_valid_proposals": rejected_valid,
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ1",
        "name": "Authority separation",
        "claim": (
            "Generated proposer quality changes utility, but ATP/Mnemosyne keeps "
            "invalid committed transitions at zero relative to constraint set C."
        ),
        "success_criteria": [
            "ATP invalid_commits = 0",
            "At least one unsafe baseline has invalid_commits > 0",
            "ATP valid_commits > 0",
        ],
        "systems": results,
    }

    json_path = report_dir / "rq1_authority_separation_report.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    summary_lines = [
        "# RQ1 Authority Separation Report",
        "",
        "Generated proposers may be wrong, weak, or adversarial. The ATP boundary should preserve committed-state correctness relative to constraint set C.",
        "",
        "| System | Proposers | Workloads per proposer | Invalid commits | Rejected invalid proposals | Valid commits |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        summary_lines.append(
            "| {system} | {proposer_count} | {workload_count_per_proposer} | "
            "{invalid_commits} | {rejected_invalid_proposals} | {valid_commits} |".format(
                **result
            )
        )

    summary_lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests authority separation, not learning, regret reduction, or preemptive planning.",
            "The guarantee is relative to the declared constraint set C.",
            "",
        ]
    )

    md_path = report_dir / "rq1_authority_separation_report.md"
    md_path.write_text("\n".join(summary_lines))


def test_rq1_authority_separation() -> None:
    proposals = proposal_suite()

    results = [
        run_system("raw_append", proposals),
        run_system("self_validation", proposals),
        run_system("atp_mnemosyne", proposals),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["raw_append"]["invalid_commits"] > 0
    assert by_system["self_validation"]["invalid_commits"] > 0

    assert by_system["atp_mnemosyne"]["invalid_commits"] == 0
    assert by_system["atp_mnemosyne"]["rejected_invalid_proposals"] > 0
    assert by_system["atp_mnemosyne"]["valid_commits"] > 0

    write_reports(results)
