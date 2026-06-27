# File: mnemosyne/runtime/demo.py
#
# Purpose:
#   R3.5 local runtime demo and evidence artifact generation.
#
# Design rule:
#   This demo exercises the R3 in-memory runtime substrate.
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.session import LocalRuntimeSession


def build_demo_session() -> LocalRuntimeSession:
    session = LocalRuntimeSession()

    session.create_workflow(
        WorkflowSpec(
            workflow_id="workflow:r3-local-demo",
            tenant_id="tenant:r3",
            app_id="campus_tour",
            schema_id="campus_tour.transition",
            fsm="CampusTourFSM",
            workflow_type="local_runtime_demo",
            created_by="user:edward",
            metadata={
                "stage": "R3.5",
                "purpose": "local runtime substrate demo",
            },
        )
    )

    session.bind_workflow(
        WorkflowBinding(
            binding_id="binding:r3-local-demo",
            workflow_id="workflow:r3-local-demo",
            tenant_id="tenant:r3",
            entity_id="entity:r3-local-demo",
            fsm="CampusTourFSM",
            initial_state="not_started",
            created_by="user:edward",
        )
    )

    session.create_agent(
        AgentSpec(
            agent_id="agent:r3-planner",
            tenant_id="tenant:r3",
            agent_type="planner",
            display_name="R3 Planning Agent",
            created_by="user:edward",
            capabilities=("propose", "repair"),
            model_id="local-demo-agent",
        )
    )

    session.bind_agent(
        AgentBinding(
            agent_binding_id="agent-binding:r3-planner:local-demo",
            agent_id="agent:r3-planner",
            workflow_id="workflow:r3-local-demo",
            tenant_id="tenant:r3",
            binding_id="binding:r3-local-demo",
            entity_id="entity:r3-local-demo",
            role="planner",
            permissions=("propose", "repair"),
        )
    )

    return session


def accepted_demo_proposal() -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id="proposal:r3-local-demo:accepted",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-local-demo",
        binding_id="binding:r3-local-demo",
        entity_id="entity:r3-local-demo",
        agent_id="agent:r3-planner",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        proposal_kind="plan",
        payload={
            "route": ["S", "D", "A", "B", "L", "S"],
            "finish_time": "12:10",
            "description": "candidate campus-tour plan",
        },
        assumptions=(
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            },
        ),
        provenance={
            "stage": "R3.5",
            "source": "local_runtime_demo",
            "note": "proposal is metadata until admitted by runtime",
        },
    )


def rejected_demo_proposal() -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id="proposal:r3-local-demo:rejected",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-local-demo",
        binding_id="binding:r3-local-demo",
        entity_id="entity:r3-local-demo",
        agent_id="agent:r3-planner",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        proposal_kind="plan",
        payload={
            "route": ["S", "L", "S"],
            "finish_time": "18:30",
            "description": "candidate plan intentionally rejected by demo admission",
        },
        assumptions=(
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            },
        ),
        provenance={
            "stage": "R3.5",
            "source": "local_runtime_demo",
            "note": "rejected proposal remains audit evidence",
        },
    )


def run_local_runtime_demo() -> dict[str, Any]:
    session = build_demo_session()

    accepted = session.submit_proposal(accepted_demo_proposal())
    accepted_decision = session.accept_proposal(
        proposal_id=accepted.proposal_id,
        reason="proposal admitted by local R3 demo facade",
        committed_rids=("rid:r3-demo:001", "rid:r3-demo:002"),
        audit_ref="reports/r3/local_runtime_demo_001.md",
        metadata={
            "demo_only": True,
            "kernel_commit_performed": False,
            "note": "committed_rids are demo evidence handles, not a Store commit",
        },
    )

    rejected = session.submit_proposal(rejected_demo_proposal())
    rejected_decision = session.reject_proposal(
        proposal_id=rejected.proposal_id,
        reason="deadline violation rejected before commit",
        error_codes=("DOMAIN_FEASIBILITY_REJECTED", "DEADLINE_MISSED"),
        audit_ref="reports/r3/local_runtime_demo_001.md",
        metadata={
            "demo_only": True,
            "kernel_commit_performed": False,
        },
    )

    status = session.runtime_status("workflow:r3-local-demo")
    trace_events = session.list_trace_events()

    return {
        "stage": "R3.5",
        "demo_id": "local_runtime_demo_001",
        "design_rule": "runtime metadata only; no Store/CTL/Validator/Temporal/kernel commit-path changes",
        "workflow_id": "workflow:r3-local-demo",
        "agent_id": "agent:r3-planner",
        "accepted_proposal": asdict(accepted),
        "accepted_decision": asdict(accepted_decision),
        "rejected_proposal": asdict(rejected),
        "rejected_decision": asdict(rejected_decision),
        "runtime_status": status,
        "trace_events": [asdict(event) for event in trace_events],
    }


def render_markdown_report(result: dict[str, Any]) -> str:
    status = result["runtime_status"]
    trace_events = result["trace_events"]

    lines = [
        "# R3.5 Local Runtime Demo",
        "",
        "## Summary",
        "",
        "This report is generated by the R3.5 local runtime demo.",
        "",
        "It exercises the in-memory runtime substrate:",
        "",
        "- workflow creation",
        "- workflow binding",
        "- agent creation",
        "- agent-to-workflow binding",
        "- proposal submission",
        "- admission acceptance",
        "- admission rejection",
        "- trace evidence",
        "",
        "## Design rule",
        "",
        result["design_rule"],
        "",
        "Committed truth remains owned by the core kernel. This demo does not write to Store and does not bypass admission.",
        "",
        "## Runtime status",
        "",
        f"- Workflow ID: `{status['workflow_id']}`",
        f"- Proposal count: `{status['proposal_count']}`",
        f"- Decision count: `{status['decision_count']}`",
        f"- Accepted count: `{status['accepted_count']}`",
        f"- Rejected count: `{status['rejected_count']}`",
        f"- Trace event count: `{status['trace_event_count']}`",
        "",
        "## Accepted proposal",
        "",
        f"- Proposal ID: `{result['accepted_proposal']['proposal_id']}`",
        f"- Decision ID: `{result['accepted_decision']['decision_id']}`",
        f"- Reason: `{result['accepted_decision']['reason']}`",
        f"- Demo committed_rids: `{result['accepted_decision']['committed_rids']}`",
        "",
        "## Rejected proposal",
        "",
        f"- Proposal ID: `{result['rejected_proposal']['proposal_id']}`",
        f"- Decision ID: `{result['rejected_decision']['decision_id']}`",
        f"- Reason: `{result['rejected_decision']['reason']}`",
        f"- Error codes: `{result['rejected_decision']['error_codes']}`",
        "",
        "## Trace events",
        "",
    ]

    for event in trace_events:
        lines.append(
            f"- `{event['event_type']}`: proposal=`{event.get('proposal_id')}`, decision=`{event.get('decision_id')}`"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "R3.5 demonstrates that the runtime substrate can coordinate workflows, agents, proposal lifecycle metadata, admission decisions, and trace evidence in one local session.",
            "",
            "This is not production runtime yet. It is the first integrated R3 evidence artifact.",
            "",
        ]
    )

    return "\n".join(lines)


def write_local_runtime_demo_artifacts(
    *,
    results_path: str | Path = "results/r3/local_runtime_demo_001.json",
    report_path: str | Path = "reports/r3/local_runtime_demo_001.md",
) -> dict[str, Any]:
    result = run_local_runtime_demo()

    results = Path(results_path)
    report = Path(report_path)

    results.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    results.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report.write_text(render_markdown_report(result), encoding="utf-8")

    return result


def main() -> int:
    write_local_runtime_demo_artifacts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
