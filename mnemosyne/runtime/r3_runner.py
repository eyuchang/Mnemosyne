# File: mnemosyne/runtime/r3_runner.py
#
# Purpose:
#   R3.7 local runtime command/report runner.
#
# Design rule:
#   This runner exercises the command-shaped R3 runtime API.
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mnemosyne.runtime.command_handler import RuntimeCommandHandler
from mnemosyne.runtime.commands import (
    AcceptProposalCommand,
    BindAgentCommand,
    BindWorkflowCommand,
    CreateAgentCommand,
    CreateWorkflowCommand,
    ListTraceEventsCommand,
    QueryWorkflowStatusCommand,
    RejectProposalCommand,
    RuntimeCommand,
    RuntimeCommandResult,
    SubmitProposalCommand,
)
from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)


def workflow_spec() -> WorkflowSpec:
    return WorkflowSpec(
        workflow_id="workflow:r3-command-demo",
        tenant_id="tenant:r3",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        fsm="CampusTourFSM",
        workflow_type="runtime_command_demo",
        created_by="user:edward",
        metadata={
            "stage": "R3.7",
            "purpose": "command-shaped runtime evidence",
        },
    )


def workflow_binding() -> WorkflowBinding:
    return WorkflowBinding(
        binding_id="binding:r3-command-demo",
        workflow_id="workflow:r3-command-demo",
        tenant_id="tenant:r3",
        entity_id="entity:r3-command-demo",
        fsm="CampusTourFSM",
        initial_state="not_started",
        created_by="user:edward",
    )


def agent_spec() -> AgentSpec:
    return AgentSpec(
        agent_id="agent:r3-command-planner",
        tenant_id="tenant:r3",
        agent_type="planner",
        display_name="R3 Command Planner",
        created_by="user:edward",
        capabilities=("propose", "repair"),
        model_id="local-command-demo-agent",
    )


def agent_binding() -> AgentBinding:
    return AgentBinding(
        agent_binding_id="agent-binding:r3-command-planner",
        agent_id="agent:r3-command-planner",
        workflow_id="workflow:r3-command-demo",
        tenant_id="tenant:r3",
        binding_id="binding:r3-command-demo",
        entity_id="entity:r3-command-demo",
        role="planner",
        permissions=("propose", "repair"),
    )


def accepted_proposal() -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id="proposal:r3-command-demo:accepted",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-command-demo",
        binding_id="binding:r3-command-demo",
        entity_id="entity:r3-command-demo",
        agent_id="agent:r3-command-planner",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        proposal_kind="plan",
        payload={
            "route": ["S", "D", "A", "B", "L", "S"],
            "finish_time": "12:10",
            "description": "accepted command-demo proposal",
        },
        assumptions=(
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            },
        ),
        provenance={
            "stage": "R3.7",
            "source": "runtime_command_runner",
            "note": "proposal remains metadata until admitted",
        },
    )


def rejected_proposal() -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id="proposal:r3-command-demo:rejected",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-command-demo",
        binding_id="binding:r3-command-demo",
        entity_id="entity:r3-command-demo",
        agent_id="agent:r3-command-planner",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        proposal_kind="plan",
        payload={
            "route": ["S", "L", "S"],
            "finish_time": "18:30",
            "description": "intentionally rejected command-demo proposal",
        },
        assumptions=(
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            },
        ),
        provenance={
            "stage": "R3.7",
            "source": "runtime_command_runner",
            "note": "rejected proposal remains audit evidence",
        },
    )


def command_sequence() -> list[RuntimeCommand]:
    return [
        CreateWorkflowCommand(workflow_spec()),
        BindWorkflowCommand(workflow_binding()),
        CreateAgentCommand(agent_spec()),
        BindAgentCommand(agent_binding()),
        SubmitProposalCommand(accepted_proposal()),
        AcceptProposalCommand(
            proposal_id="proposal:r3-command-demo:accepted",
            reason="proposal admitted by command-shaped runtime API",
            committed_rids=("rid:r3-command-demo:001", "rid:r3-command-demo:002"),
            audit_ref="reports/r3/runtime_command_demo_001.md",
            metadata={
                "demo_only": True,
                "kernel_commit_performed": False,
            },
        ),
        SubmitProposalCommand(rejected_proposal()),
        RejectProposalCommand(
            proposal_id="proposal:r3-command-demo:rejected",
            reason="deadline violation rejected before commit",
            error_codes=("DOMAIN_FEASIBILITY_REJECTED", "DEADLINE_MISSED"),
            audit_ref="reports/r3/runtime_command_demo_001.md",
            metadata={
                "demo_only": True,
                "kernel_commit_performed": False,
            },
        ),
        QueryWorkflowStatusCommand(workflow_id="workflow:r3-command-demo"),
        ListTraceEventsCommand(workflow_id="workflow:r3-command-demo"),
    ]


def _result_to_dict(result: RuntimeCommandResult) -> dict[str, Any]:
    return asdict(result)


def run_runtime_command_demo() -> dict[str, Any]:
    handler = RuntimeCommandHandler()
    command_results: list[dict[str, Any]] = []

    for command in command_sequence():
        result = handler.handle(command)
        command_results.append(_result_to_dict(result))
        if not result.ok:
            break

    status_result = command_results[-2]
    trace_result = command_results[-1]

    return {
        "stage": "R3.7",
        "demo_id": "runtime_command_demo_001",
        "design_rule": "command-shaped local runtime only; no Store/CTL/Validator/Temporal/kernel commit-path changes",
        "workflow_id": "workflow:r3-command-demo",
        "agent_id": "agent:r3-command-planner",
        "command_count": len(command_results),
        "all_commands_ok": all(result["ok"] for result in command_results),
        "command_results": command_results,
        "runtime_status": status_result["value"],
        "trace_events": trace_result["value"],
    }


def render_markdown_report(result: dict[str, Any]) -> str:
    status = result["runtime_status"]
    trace_events = result["trace_events"]
    command_results = result["command_results"]

    lines = [
        "# R3.7 Runtime Command Demo",
        "",
        "## Summary",
        "",
        "This report is generated by the R3.7 command-shaped local runtime runner.",
        "",
        "It exercises the runtime through commands rather than direct session method calls.",
        "",
        "## Design rule",
        "",
        result["design_rule"],
        "",
        "Committed truth remains owned by the core kernel. This command demo does not write to Store and does not bypass admission.",
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
        "## Command sequence",
        "",
    ]

    for index, command_result in enumerate(command_results, start=1):
        lines.append(
            f"{index}. `{command_result['command_type']}` -> ok=`{command_result['ok']}`"
        )

    lines.extend(
        [
            "",
            "## Trace events",
            "",
        ]
    )

    for event in trace_events:
        lines.append(
            f"- `{event['event_type']}`: proposal=`{event.get('proposal_id')}`, decision=`{event.get('decision_id')}`"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "R3.7 demonstrates that the local runtime substrate can be driven through a stable command-shaped interface.",
            "",
            "This closes the gap between object-level runtime models and a future persistent or distributed runtime backend.",
            "",
            "This is still not production runtime. It is local R3 evidence.",
            "",
        ]
    )

    return "\n".join(lines)


def write_runtime_command_demo_artifacts(
    *,
    results_path: str | Path = "results/r3/runtime_command_demo_001.json",
    report_path: str | Path = "reports/r3/runtime_command_demo_001.md",
) -> dict[str, Any]:
    result = run_runtime_command_demo()

    results = Path(results_path)
    report = Path(report_path)

    results.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    results.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report.write_text(render_markdown_report(result), encoding="utf-8")

    return result


def main() -> int:
    result = write_runtime_command_demo_artifacts()
    return 0 if result["all_commands_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
