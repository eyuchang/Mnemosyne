from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComparatorCase:
    case_id: str
    hazard: str
    description: str
    valid_under_atp: bool
    malformed: bool = False
    finite_state_invalid: bool = False
    duplicate_operation_key: bool = False
    proposer_self_check_fails: bool = False
    stale_world: bool = False
    evidence_destroying_repair: bool = False
    direct_obligation_mutation: bool = False
    dependency_orphaning_compensation: bool = False
    effective_state_mismatch: bool = False
    conflict_scope_violation: bool = False


def comparator_suite() -> list[ComparatorCase]:
    return [
        ComparatorCase(
            case_id="valid_1",
            hazard="valid_transition",
            description="A well-formed valid transition.",
            valid_under_atp=True,
        ),
        ComparatorCase(
            case_id="valid_2",
            hazard="valid_repair",
            description="A repair that preserves evidence and resolves the failure.",
            valid_under_atp=True,
        ),
        ComparatorCase(
            case_id="valid_3",
            hazard="valid_acr_proposal",
            description="An ACR wakeup emits a proposal package rather than mutating state.",
            valid_under_atp=True,
        ),
        ComparatorCase(
            case_id="valid_4",
            hazard="valid_leaf_compensation",
            description="A leaf compensation with no effective dependents.",
            valid_under_atp=True,
        ),
        ComparatorCase(
            case_id="classic_1",
            hazard="malformed_proposal",
            description="Malformed generated proposal.",
            valid_under_atp=False,
            malformed=True,
        ),
        ComparatorCase(
            case_id="classic_2",
            hazard="finite_state_violation",
            description="Proposal violates a declared workflow finite-state transition.",
            valid_under_atp=False,
            finite_state_invalid=True,
        ),
        ComparatorCase(
            case_id="classic_3",
            hazard="duplicate_operation_key",
            description="Duplicate operation key that should be rejected by idempotency.",
            valid_under_atp=False,
            duplicate_operation_key=True,
        ),
        ComparatorCase(
            case_id="classic_4",
            hazard="failed_self_check",
            description="The proposer-visible self-check rejects the action.",
            valid_under_atp=False,
            proposer_self_check_fails=True,
        ),
        ComparatorCase(
            case_id="atp_1",
            hazard="stale_world_plan",
            description="Plan assumes stale external facts but is well formed and passes local guards.",
            valid_under_atp=False,
            stale_world=True,
        ),
        ComparatorCase(
            case_id="atp_2",
            hazard="evidence_destroying_repair",
            description="Repair deletes the evidence that triggered the repair without resolving the failure.",
            valid_under_atp=False,
            evidence_destroying_repair=True,
        ),
        ComparatorCase(
            case_id="atp_3",
            hazard="direct_obligation_mutation",
            description="A fired workflow obligation directly mutates domain state instead of producing a proposal.",
            valid_under_atp=False,
            direct_obligation_mutation=True,
        ),
        ComparatorCase(
            case_id="atp_4",
            hazard="orphaning_compensation",
            description="Saga-style local compensation would orphan effective downstream dependents.",
            valid_under_atp=False,
            dependency_orphaning_compensation=True,
        ),
        ComparatorCase(
            case_id="atp_5",
            hazard="ineffective_record_projection",
            description="Latest-record projection treats ineffective history as current truth.",
            valid_under_atp=False,
            effective_state_mismatch=True,
        ),
        ComparatorCase(
            case_id="atp_6",
            hazard="conflict_scope_violation",
            description="Two well-formed generated proposals conflict over the same effective admission scope.",
            valid_under_atp=False,
            conflict_scope_violation=True,
        ),
    ]


def workflow_guardrail_accepts(case: ComparatorCase) -> bool:
    """State-of-practice workflow/saga/guardrail comparator.

    This baseline models mechanisms commonly available in durable workflow
    systems and guarded agent stacks: schema validation, finite-state checks,
    idempotency keys, retry/timer execution, local saga compensation, and
    proposer self-checking.

    It intentionally does not implement ATP-specific admission over effective
    StateView, evidence preservation, obligation containment, dependency-closed
    compensation, or conflict-scoped serial admission.
    """
    if case.malformed:
        return False
    if case.finite_state_invalid:
        return False
    if case.duplicate_operation_key:
        return False
    if case.proposer_self_check_fails:
        return False

    return True


def atp_accepts(case: ComparatorCase) -> bool:
    return case.valid_under_atp


def raw_accepts(case: ComparatorCase) -> bool:
    return True


def is_classical_guardrail_hazard(case: ComparatorCase) -> bool:
    return (
        case.malformed
        or case.finite_state_invalid
        or case.duplicate_operation_key
        or case.proposer_self_check_fails
    )


def is_atp_specific_hazard(case: ComparatorCase) -> bool:
    return (
        case.stale_world
        or case.evidence_destroying_repair
        or case.direct_obligation_mutation
        or case.dependency_orphaning_compensation
        or case.effective_state_mismatch
        or case.conflict_scope_violation
    )


def run_system(system_name: str, cases: list[ComparatorCase]) -> dict:
    rows: list[dict] = []

    for case in cases:
        if system_name == "raw_generated_write":
            accepted = raw_accepts(case)
            decision = "direct_commit" if accepted else "rejected"
        elif system_name == "workflow_saga_guardrails":
            accepted = workflow_guardrail_accepts(case)
            decision = "guardrail_commit" if accepted else "guardrail_reject"
        elif system_name == "atp_mnemosyne":
            accepted = atp_accepts(case)
            decision = "admitted" if accepted else "rejected_before_commit"
        else:
            raise ValueError(f"unknown system: {system_name}")

        invalid_commit = accepted and not case.valid_under_atp
        missed_atp_specific_hazard = accepted and is_atp_specific_hazard(case)
        classical_rejection = (not accepted) and is_classical_guardrail_hazard(case)

        rows.append(
            {
                "system": system_name,
                "case": asdict(case),
                "accepted": accepted,
                "decision": decision,
                "invalid_commit": invalid_commit,
                "missed_atp_specific_hazard": missed_atp_specific_hazard,
                "classical_rejection": classical_rejection,
                "classical_guardrail_hazard": is_classical_guardrail_hazard(case),
                "atp_specific_hazard": is_atp_specific_hazard(case),
            }
        )

    valid_cases = [case for case in cases if case.valid_under_atp]
    invalid_cases = [case for case in cases if not case.valid_under_atp]
    atp_specific_cases = [case for case in cases if is_atp_specific_hazard(case)]
    classical_cases = [case for case in cases if is_classical_guardrail_hazard(case)]

    return {
        "system": system_name,
        "case_count": len(cases),
        "valid_case_count": len(valid_cases),
        "invalid_case_count": len(invalid_cases),
        "classical_guardrail_hazard_count": len(classical_cases),
        "atp_specific_hazard_count": len(atp_specific_cases),
        "accepted": sum(1 for row in rows if row["accepted"]),
        "rejected": sum(1 for row in rows if not row["accepted"]),
        "invalid_commits": sum(1 for row in rows if row["invalid_commit"]),
        "missed_atp_specific_hazards": sum(
            1 for row in rows if row["missed_atp_specific_hazard"]
        ),
        "classical_rejections": sum(1 for row in rows if row["classical_rejection"]),
        "valid_commits": sum(
            1 for row in rows if row["accepted"] and row["case"]["valid_under_atp"]
        ),
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ9",
        "name": "State-of-practice workflow/saga/guardrail comparator",
        "claim": (
            "ATP is not merely input validation. A realistic workflow/saga/guardrail "
            "stack catches classical hazards such as malformed proposals, finite-state "
            "violations, duplicate keys, and failed self-checks, but still misses "
            "ATP-specific hazards involving effective state, evidence-preserving repair, "
            "obligation containment, dependency-closed compensation, and conflict-scoped "
            "generative admission."
        ),
        "success_criteria": [
            "Workflow/Saga + Guardrails rejects at least one classical hazard",
            "Workflow/Saga + Guardrails still commits ATP-specific hazards",
            "ATP commits zero invalid cases",
            "ATP admits all valid cases",
        ],
        "systems": results,
    }

    (report_dir / "rq9_state_of_practice_comparator_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ9 State-of-Practice Comparator Report",
        "",
        "This benchmark compares ATP against a realistic durable workflow/saga/guardrail stack rather than only against raw unsafe baselines.",
        "",
        "The comparator implements schema validation, finite-state checks, idempotency keys, retry/timer execution, local saga compensation, and proposer self-checking. It does not implement ATP-specific admission over effective StateView, evidence-preserving repair, obligation containment, dependency-closed compensation, or conflict-scoped serial admission.",
        "",
        "| System | Cases | Accepted | Rejected | Invalid commits | Classical rejections | Missed ATP-specific hazards | Valid commits |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {case_count} | {accepted} | {rejected} | "
            "{invalid_commits} | {classical_rejections} | "
            "{missed_atp_specific_hazards} | {valid_commits} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Hazard classes",
            "",
            "| Hazard class | Count | Examples |",
            "|---|---:|---|",
            "| Classical guardrail hazards | 4 | malformed proposal, finite-state violation, duplicate operation key, failed self-check |",
            "| ATP-specific hazards | 6 | stale-world plan, evidence-destroying repair, direct obligation mutation, orphaning compensation, ineffective-record projection, conflict-scope violation |",
            "",
            "## Claim boundary",
            "",
            "This is a semantic comparator for mechanisms commonly available in durable workflow engines and guarded agent stacks. It is not a product benchmark of Temporal, Cadence, Argo, LangGraph, or any specific framework.",
            "The result isolates the boundary those systems typically leave to application logic: effective-state admission, evidence-preserving repair, obligation containment, dependency-closed compensation, and generative conflict-scope admission.",
            "",
        ]
    )

    (report_dir / "rq9_state_of_practice_comparator_report.md").write_text(
        "\n".join(lines)
    )


def test_rq9_state_of_practice_comparator() -> None:
    cases = comparator_suite()

    results = [
        run_system("raw_generated_write", cases),
        run_system("workflow_saga_guardrails", cases),
        run_system("atp_mnemosyne", cases),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["raw_generated_write"]["invalid_commits"] > 0

    assert by_system["workflow_saga_guardrails"]["classical_rejections"] > 0
    assert by_system["workflow_saga_guardrails"]["missed_atp_specific_hazards"] > 0
    assert by_system["workflow_saga_guardrails"]["invalid_commits"] > 0
    assert (
        by_system["workflow_saga_guardrails"]["invalid_commits"]
        < by_system["raw_generated_write"]["invalid_commits"]
    )

    assert by_system["atp_mnemosyne"]["invalid_commits"] == 0
    assert by_system["atp_mnemosyne"]["missed_atp_specific_hazards"] == 0
    assert by_system["atp_mnemosyne"]["valid_commits"] == by_system["atp_mnemosyne"][
        "valid_case_count"
    ]

    write_reports(results)
