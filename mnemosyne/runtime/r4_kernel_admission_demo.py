from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mnemosyne.runtime.kernel_admission import (
    KernelAdmissionAdapter,
    KernelCommitRequest,
    KernelCommitResult,
)
from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository


RESULTS_DIR = Path("results/r4")
REPORTS_DIR = Path("reports/r4")

RESULT_PATH = RESULTS_DIR / "kernel_admission_001.json"
REPORT_PATH = REPORTS_DIR / "kernel_admission_001.md"


@dataclass
class MappingCommitter:
    results_by_proposal_id: dict[str, KernelCommitResult]
    calls: list[KernelCommitRequest]

    def commit(self, request: KernelCommitRequest) -> KernelCommitResult:
        self.calls.append(request)
        return self.results_by_proposal_id[request.proposal_id]


def seed_base(repo: SQLiteRuntimeRepository) -> dict[str, str]:
    ids = {
        "tenant_id": "tenant:r4-kernel-evidence",
        "workflow_id": "workflow:r4-kernel-evidence",
        "binding_id": "binding:r4-kernel-evidence",
        "agent_id": "agent:r4-kernel-evidence",
        "agent_binding_id": "agent-binding:r4-kernel-evidence",
        "entity_id": "entity:r4-kernel-evidence",
        "fsm": "CampusTourFSM",
        "app_id": "campus_tour",
        "schema_id": "campus_tour.transition",
    }

    repo.create_workflow(
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        metadata={"stage": "R4.4"},
    )

    repo.create_workflow_binding(
        binding_id=ids["binding_id"],
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    repo.create_agent(
        agent_id=ids["agent_id"],
        tenant_id=ids["tenant_id"],
        agent_type="planner",
        display_name="R4 Kernel Evidence Planner",
    )

    repo.create_agent_binding(
        agent_binding_id=ids["agent_binding_id"],
        agent_id=ids["agent_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    return ids


def submit_case(repo: SQLiteRuntimeRepository, ids: dict[str, str], case_id: str) -> str:
    proposal_id = f"proposal:r4-kernel:{case_id}"

    repo.submit_proposal(
        proposal_id=proposal_id,
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        agent_binding_id=ids["agent_binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={
            "case_id": case_id,
            "route": ["S", "D", "A", "B", "L", "S"],
        },
        metadata={"stage": "R4.4", "case_id": case_id},
    )

    return proposal_id


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# R4.4 Kernel-Admission Evidence",
        "",
        f"- Overall status: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Kernel calls observed: `{result['kernel_call_count']}`",
        "",
        "## Cases",
        "",
        "| Case | Runtime decision | Status | Store/kernel commit? | Committed RIDs | Error codes |",
        "|---|---|---|---:|---|---|",
    ]

    for case in result["cases"]:
        lines.append(
            "| `{case_id}` | `{runtime_decision}` | `{status}` | `{kernel_commit_performed}` | `{rids}` | `{errors}` |".format(
                case_id=case["case_id"],
                runtime_decision=case["runtime_decision"],
                status=case["status"],
                kernel_commit_performed=case["kernel_commit_performed"],
                rids=", ".join(case["committed_rids"]) or "-",
                errors=", ".join(case["error_codes"]) or "-",
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "R4.4 demonstrates the runtime/kernel admission boundary.",
            "",
            "- Accepted runtime admission is recorded only when kernel commit evidence returns committed record IDs.",
            "- Rejected-before-commit does not call the kernel.",
            "- Validator rejection records runtime rejection with no committed record IDs.",
            "- Commit failure records runtime rejection with no committed record IDs.",
            "",
            "This is a small controlled kernel-admission demo for runtime validation and replay.",
            "",
        ]
    )

    return "\n".join(lines)


def run_demo(db_path: str | Path | None = None) -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "kernel_admission_001.sqlite3"
    if db_path.exists():
        db_path.unlink()

    repo = SQLiteRuntimeRepository(db_path)
    ids = seed_base(repo)

    proposal_accepted = submit_case(repo, ids, "accepted_and_committed")
    proposal_preflight = submit_case(repo, ids, "rejected_before_commit")
    proposal_validator = submit_case(repo, ids, "validator_rejected")
    proposal_commit_failed = submit_case(repo, ids, "commit_failed")

    committer = MappingCommitter(
        results_by_proposal_id={
            proposal_accepted: KernelCommitResult(
                ok=True,
                status="committed",
                committed_rids=("rid:r4-kernel:accepted",),
                audit_ref="audit:r4-kernel:accepted",
                message="kernel commit succeeded",
            ),
            proposal_validator: KernelCommitResult(
                ok=False,
                status="validator_rejected",
                committed_rids=(),
                audit_ref="audit:r4-kernel:validator",
                error_codes=("VALIDATOR_REJECTED",),
                message="validator rejected proposal",
            ),
            proposal_commit_failed: KernelCommitResult(
                ok=False,
                status="commit_failed",
                committed_rids=(),
                audit_ref="audit:r4-kernel:commit-failed",
                error_codes=("STORE_COMMIT_FAILED",),
                message="store commit failed",
            ),
        },
        calls=[],
    )

    adapter = KernelAdmissionAdapter(repo, committer)

    outcomes = []

    outcomes.append(
        adapter.accept_via_kernel(
            proposal_id=proposal_accepted,
            decision_id="decision:r4-kernel:accepted",
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            entity_id=ids["entity_id"],
            fsm=ids["fsm"],
            app_id=ids["app_id"],
            schema_id=ids["schema_id"],
            payload={"case_id": "accepted_and_committed"},
        )
    )

    outcomes.append(
        adapter.reject_before_commit(
            proposal_id=proposal_preflight,
            decision_id="decision:r4-kernel:preflight",
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            reason="preflight rejected before kernel commit",
            error_codes=("DOMAIN_FEASIBILITY_REJECTED",),
        )
    )

    outcomes.append(
        adapter.accept_via_kernel(
            proposal_id=proposal_validator,
            decision_id="decision:r4-kernel:validator",
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            entity_id=ids["entity_id"],
            fsm=ids["fsm"],
            app_id=ids["app_id"],
            schema_id=ids["schema_id"],
            payload={"case_id": "validator_rejected"},
        )
    )

    outcomes.append(
        adapter.accept_via_kernel(
            proposal_id=proposal_commit_failed,
            decision_id="decision:r4-kernel:commit-failed",
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            entity_id=ids["entity_id"],
            fsm=ids["fsm"],
            app_id=ids["app_id"],
            schema_id=ids["schema_id"],
            payload={"case_id": "commit_failed"},
        )
    )

    cases = []
    for outcome in outcomes:
        decision = repo.get_decision_for_proposal(outcome.proposal_id)
        proposal = repo.get_proposal(outcome.proposal_id)
        case_id = outcome.status

        cases.append(
            {
                "case_id": case_id,
                "proposal_id": outcome.proposal_id,
                "proposal_status": proposal["status"],
                "runtime_decision": outcome.runtime_decision,
                "status": outcome.status,
                "committed_rids": list(outcome.committed_rids),
                "error_codes": list(outcome.error_codes),
                "kernel_commit_performed": outcome.kernel_commit_performed,
                "decision_metadata": decision["metadata"],
            }
        )

    checks = {
        "accepted_has_committed_rid": cases[0]["committed_rids"] == ["rid:r4-kernel:accepted"],
        "preflight_rejection_did_not_call_kernel": len([c for c in committer.calls if c.proposal_id == proposal_preflight]) == 0,
        "validator_rejection_has_no_committed_rids": cases[2]["committed_rids"] == [] and cases[2]["error_codes"] == ["VALIDATOR_REJECTED"],
        "commit_failure_has_no_committed_rids": cases[3]["committed_rids"] == [] and cases[3]["error_codes"] == ["STORE_COMMIT_FAILED"],
        "kernel_called_three_times": len(committer.calls) == 3,
    }

    result = {
        "stage": "R4.4",
        "name": "Kernel-admission evidence",
        "cases": cases,
        "checks": checks,
        "kernel_call_count": len(committer.calls),
        "runtime_status": repo.runtime_status(),
        "pass": all(checks.values()),
    }

    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")

    if db_path.name == "kernel_admission_001.sqlite3" and db_path.exists():
        db_path.unlink()

    return result


def main() -> int:
    result = run_demo()
    print(json.dumps({"pass": result["pass"], "kernel_call_count": result["kernel_call_count"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
