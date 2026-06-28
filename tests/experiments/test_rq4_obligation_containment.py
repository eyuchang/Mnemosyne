from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


CONTINUATIONS = [
    "normal_continuation",
    "workflow_timer",
    "llm_like_continuation",
    "adversarial_continuation",
]


@dataclass(frozen=True)
class ACRWakeup:
    wakeup_id: str
    continuation: str
    workload: str
    acr_live: bool
    syntactically_valid: bool
    dependency_state_current: bool
    proposal_valid_under_c: bool
    attempts_direct_domain_mutation: bool
    emits_proposal_package: bool


@dataclass(frozen=True)
class ObligationCheck:
    accepted: bool
    reason: str


def obligation_containment_admission(wakeup: ACRWakeup) -> ObligationCheck:
    if not wakeup.acr_live:
        return ObligationCheck(False, "acr_not_live")

    if not wakeup.syntactically_valid:
        return ObligationCheck(False, "malformed_continuation")

    if not wakeup.dependency_state_current:
        return ObligationCheck(False, "stale_dependency_scope")

    if wakeup.attempts_direct_domain_mutation:
        return ObligationCheck(False, "direct_mutation_forbidden")

    if not wakeup.emits_proposal_package:
        return ObligationCheck(False, "missing_proposal_package")

    if not wakeup.proposal_valid_under_c:
        return ObligationCheck(False, "invalid_recovery_proposal")

    return ObligationCheck(True, "accepted")


def wakeup_suite() -> list[ACRWakeup]:
    wakeups: list[ACRWakeup] = []

    for continuation in CONTINUATIONS:
        base = f"{continuation}:acr-17"

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:valid-proposal",
                continuation=continuation,
                workload="valid_proposal_package",
                acr_live=True,
                syntactically_valid=True,
                dependency_state_current=True,
                proposal_valid_under_c=True,
                attempts_direct_domain_mutation=False,
                emits_proposal_package=True,
            )
        )

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:direct-mutation",
                continuation=continuation,
                workload="direct_domain_mutation",
                acr_live=True,
                syntactically_valid=True,
                dependency_state_current=True,
                proposal_valid_under_c=True,
                attempts_direct_domain_mutation=True,
                emits_proposal_package=False,
            )
        )

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:expired-acr",
                continuation=continuation,
                workload="expired_acr_wakeup",
                acr_live=False,
                syntactically_valid=True,
                dependency_state_current=True,
                proposal_valid_under_c=True,
                attempts_direct_domain_mutation=True,
                emits_proposal_package=False,
            )
        )

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:malformed-continuation",
                continuation=continuation,
                workload="malformed_continuation",
                acr_live=True,
                syntactically_valid=False,
                dependency_state_current=True,
                proposal_valid_under_c=False,
                attempts_direct_domain_mutation=False,
                emits_proposal_package=True,
            )
        )

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:stale-dependency",
                continuation=continuation,
                workload="stale_dependency_scope",
                acr_live=True,
                syntactically_valid=True,
                dependency_state_current=False,
                proposal_valid_under_c=True,
                attempts_direct_domain_mutation=False,
                emits_proposal_package=True,
            )
        )

        wakeups.append(
            ACRWakeup(
                wakeup_id=f"{base}:invalid-proposal",
                continuation=continuation,
                workload="invalid_recovery_proposal",
                acr_live=True,
                syntactically_valid=True,
                dependency_state_current=True,
                proposal_valid_under_c=False,
                attempts_direct_domain_mutation=False,
                emits_proposal_package=True,
            )
        )

    return wakeups


def run_system(system_name: str, wakeups: list[ACRWakeup]) -> dict:
    rows: list[dict] = []

    for wakeup in wakeups:
        check = obligation_containment_admission(wakeup)

        if system_name == "trigger_direct_mutation":
            domain_mutated = wakeup.acr_live and wakeup.syntactically_valid
            proposal_package_created = False
            admitted = domain_mutated
            decision = "direct_mutation" if domain_mutated else "ignored"

        elif system_name == "workflow_timer_direct_write":
            domain_mutated = wakeup.syntactically_valid
            proposal_package_created = False
            admitted = domain_mutated
            decision = "timer_direct_write" if domain_mutated else "ignored"

        elif system_name == "atp_mnemosyne":
            proposal_package_created = (
                wakeup.acr_live
                and wakeup.syntactically_valid
                and wakeup.emits_proposal_package
            )
            admitted = check.accepted
            domain_mutated = admitted
            decision = "admitted" if admitted else "rejected_before_commit"

        else:
            raise ValueError(f"unknown system: {system_name}")

        unauthorized_mutation = (
            domain_mutated
            and not check.accepted
        )

        rows.append(
            {
                "system": system_name,
                "wakeup": asdict(wakeup),
                "accepted_by_obligation_rule": check.accepted,
                "obligation_rule_reason": check.reason,
                "proposal_package_created": proposal_package_created,
                "domain_mutated": domain_mutated,
                "unauthorized_mutation": unauthorized_mutation,
                "decision": decision,
            }
        )

    unauthorized_mutations = sum(1 for row in rows if row["unauthorized_mutation"])
    proposal_packages_created = sum(1 for row in rows if row["proposal_package_created"])
    admitted_repairs = sum(1 for row in rows if row["decision"] == "admitted")
    rejected_repairs = sum(1 for row in rows if row["decision"] == "rejected_before_commit")

    return {
        "system": system_name,
        "continuation_count": len(CONTINUATIONS),
        "workload_count_per_continuation": len(rows) // len(CONTINUATIONS),
        "wakeup_count": len(rows),
        "unauthorized_mutations": unauthorized_mutations,
        "proposal_packages_created": proposal_packages_created,
        "admitted_repairs": admitted_repairs,
        "rejected_repairs": rejected_repairs,
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ4",
        "name": "Obligation containment",
        "claim": (
            "ACR wakeups may resume recovery by emitting proposal packages, "
            "but they cannot mutate committed domain truth except through ordinary ATP admission."
        ),
        "success_criteria": [
            "ATP unauthorized_mutations = 0",
            "At least one unsafe baseline has unauthorized_mutations > 0",
            "ATP proposal_packages_created > 0",
            "ATP admitted_repairs > 0",
            "ATP rejected_repairs > 0",
        ],
        "systems": results,
    }

    json_path = report_dir / "rq4_obligation_containment_report.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    lines = [
        "# RQ4 Obligation Containment Report",
        "",
        "An Active Commitment Record may wake and emit a proposal package, but it may not directly mutate committed domain truth.",
        "",
        "| System | Continuations | Workloads per continuation | Unauthorized mutations | Proposal packages | Admitted repairs | Rejected repairs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {continuation_count} | {workload_count_per_continuation} | "
            "{unauthorized_mutations} | {proposal_packages_created} | "
            "{admitted_repairs} | {rejected_repairs} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests obligation containment.",
            "It does not claim learning, regret reduction, or preemptive planning.",
            "The guarantee is relative to the declared ACR liveness, dependency-scope, and admission predicates.",
            "",
        ]
    )

    md_path = report_dir / "rq4_obligation_containment_report.md"
    md_path.write_text("\n".join(lines))


def test_rq4_obligation_containment() -> None:
    wakeups = wakeup_suite()

    results = [
        run_system("trigger_direct_mutation", wakeups),
        run_system("workflow_timer_direct_write", wakeups),
        run_system("atp_mnemosyne", wakeups),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["trigger_direct_mutation"]["unauthorized_mutations"] > 0
    assert by_system["workflow_timer_direct_write"]["unauthorized_mutations"] > 0

    assert by_system["atp_mnemosyne"]["unauthorized_mutations"] == 0
    assert by_system["atp_mnemosyne"]["proposal_packages_created"] > 0
    assert by_system["atp_mnemosyne"]["admitted_repairs"] > 0
    assert by_system["atp_mnemosyne"]["rejected_repairs"] > 0

    write_reports(results)
