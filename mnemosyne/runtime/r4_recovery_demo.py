from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository


RESULTS_DIR = Path("results/r4")
REPORTS_DIR = Path("reports/r4")

RESULT_PATH = RESULTS_DIR / "runtime_recovery_001.json"
REPORT_PATH = REPORTS_DIR / "runtime_recovery_001.md"


def seed_runtime(repo: SQLiteRuntimeRepository) -> dict[str, str]:
    ids = {
        "tenant_id": "tenant:r4-recovery",
        "workflow_id": "workflow:r4-recovery",
        "binding_id": "binding:r4-recovery",
        "agent_id": "agent:r4-recovery",
        "agent_binding_id": "agent-binding:r4-recovery",
        "entity_id": "entity:r4-recovery",
        "proposal_id": "proposal:r4-recovery",
        "decision_id": "decision:r4-recovery",
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
        metadata={"stage": "R4.2", "purpose": "runtime recovery evidence"},
    )

    repo.create_workflow_binding(
        binding_id=ids["binding_id"],
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        metadata={"binding_kind": "demo"},
    )

    repo.create_agent(
        agent_id=ids["agent_id"],
        tenant_id=ids["tenant_id"],
        agent_type="planner",
        display_name="R4 Recovery Planner",
        metadata={"stage": "R4.2"},
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
        metadata={"binding_kind": "planner-to-workflow"},
    )

    repo.submit_proposal(
        proposal_id=ids["proposal_id"],
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
            "route": ["S", "D", "A", "B", "L", "S"],
            "note": "proposal payload is runtime metadata, not committed truth",
        },
        metadata={"stage": "R4.2"},
    )

    repo.record_decision(
        decision_id=ids["decision_id"],
        proposal_id=ids["proposal_id"],
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        decision="accepted",
        reason="accepted for R4.2 recovery evidence",
        committed_rids=["rid:r4-recovery-demo"],
        error_codes=[],
        metadata={
            "stage": "R4.2",
            "kernel_commit_performed": False,
            "note": "R4.2 tests durable runtime metadata, not kernel-integrated admission",
        },
    )

    return ids


def snapshot(repo: SQLiteRuntimeRepository, ids: dict[str, str]) -> dict[str, Any]:
    return {
        "workflow": repo.get_workflow(ids["workflow_id"]),
        "workflow_binding": repo.get_workflow_binding(ids["binding_id"]),
        "agent": repo.get_agent(ids["agent_id"]),
        "agent_binding": repo.get_agent_binding(ids["agent_binding_id"]),
        "proposal": repo.get_proposal(ids["proposal_id"]),
        "decision": repo.get_decision_for_proposal(ids["proposal_id"]),
        "trace_events": repo.list_trace_events(proposal_id=ids["proposal_id"]),
        "runtime_status": repo.runtime_status(),
    }


def recovery_checks(before: dict[str, Any], after: dict[str, Any]) -> dict[str, bool]:
    return {
        "workflow_recovered": after["workflow"] is not None,
        "workflow_binding_recovered": after["workflow_binding"] is not None,
        "agent_recovered": after["agent"] is not None,
        "agent_binding_recovered": after["agent_binding"] is not None,
        "proposal_recovered": after["proposal"] is not None,
        "decision_recovered": after["decision"] is not None,
        "trace_events_recovered": len(after["trace_events"]) == 2,
        "status_counts_match": before["runtime_status"] == after["runtime_status"],
        "proposal_status_recovered": after["proposal"]["status"] == "accepted",
        "decision_committed_rids_recovered": after["decision"]["committed_rids"] == ["rid:r4-recovery-demo"],
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# R4.2 Runtime Recovery Evidence",
        "",
        "## Result",
        "",
        f"- Overall status: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Database path: `{result['db_path']}`",
        "",
        "## Recovery checks",
        "",
        "| Check | Status |",
        "|---|---:|",
    ]

    for key, value in result["checks"].items():
        lines.append(f"| `{key}` | `{'PASS' if value else 'FAIL'}` |")

    lines.extend(
        [
            "",
            "## Runtime status before reopen",
            "",
        ]
    )

    for key, value in result["before"]["runtime_status"].items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Runtime status after reopen",
            "",
        ]
    )

    for key, value in result["after"]["runtime_status"].items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "R4.2 proves that runtime metadata survives repository reopening. The recovered records include workflow, workflow binding, agent, agent binding, proposal, admission decision, and trace events.",
            "",
            "This is persistence/recovery evidence for runtime metadata. It does not yet claim kernel-integrated runtime admission; that is R4.3.",
            "",
        ]
    )

    return "\n".join(lines)


def run_demo(db_path: str | Path | None = None) -> dict[str, Any]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "runtime_recovery_001.sqlite3"

    if db_path.exists():
        db_path.unlink()

    repo1 = SQLiteRuntimeRepository(db_path)
    ids = seed_runtime(repo1)
    before = snapshot(repo1, ids)

    # Simulate process restart by constructing a new repository instance over
    # the same durable SQLite database.
    repo2 = SQLiteRuntimeRepository(db_path)
    after = snapshot(repo2, ids)

    checks = recovery_checks(before, after)

    result = {
        "stage": "R4.2",
        "name": "Runtime recovery evidence",
        "db_path": str(db_path),
        "ids": ids,
        "before": before,
        "after": after,
        "checks": checks,
        "pass": all(checks.values()),
        "scope_note": "R4.2 tests durable runtime metadata, not kernel-integrated admission.",
    }

    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")

    return result


def main() -> int:
    result = run_demo()
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
