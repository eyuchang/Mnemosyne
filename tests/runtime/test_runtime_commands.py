from __future__ import annotations

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
        workflow_type="command_demo",
        created_by="user:edward",
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


def proposal_envelope(proposal_id: str = "proposal:r3-command:001") -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id=proposal_id,
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
        },
        assumptions=(
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            },
        ),
        provenance={
            "stage": "R3.6",
            "source": "command-api-test",
        },
    )


def bootstrap(handler: RuntimeCommandHandler) -> None:
    assert handler.handle(CreateWorkflowCommand(workflow_spec())).ok is True
    assert handler.handle(BindWorkflowCommand(workflow_binding())).ok is True
    assert handler.handle(CreateAgentCommand(agent_spec())).ok is True
    assert handler.handle(BindAgentCommand(agent_binding())).ok is True


def test_runtime_command_handler_bootstraps_workflow_and_agent_scope():
    handler = RuntimeCommandHandler()

    bootstrap(handler)

    status = handler.handle(
        QueryWorkflowStatusCommand(workflow_id="workflow:r3-command-demo")
    )

    assert status.ok is True
    assert status.value["workflow_id"] == "workflow:r3-command-demo"
    assert status.value["proposal_count"] == 0
    assert status.value["decision_count"] == 0


def test_runtime_command_handler_submits_and_rejects_proposal():
    handler = RuntimeCommandHandler()
    bootstrap(handler)

    submit = handler.handle(SubmitProposalCommand(proposal_envelope()))
    assert submit.ok is True
    assert submit.value["proposal_id"] == "proposal:r3-command:001"

    reject = handler.handle(
        RejectProposalCommand(
            proposal_id="proposal:r3-command:001",
            reason="deadline violation rejected before commit",
            error_codes=("DOMAIN_FEASIBILITY_REJECTED", "DEADLINE_MISSED"),
            audit_ref="reports/r3/runtime_command_demo_001.md",
        )
    )

    assert reject.ok is True
    assert reject.value["accepted"] is False
    assert reject.value["committed_rids"] == ()
    assert "DOMAIN_FEASIBILITY_REJECTED" in reject.value["error_codes"]

    status = handler.handle(
        QueryWorkflowStatusCommand(workflow_id="workflow:r3-command-demo")
    )
    assert status.value["proposal_count"] == 1
    assert status.value["decision_count"] == 1
    assert status.value["rejected_count"] == 1

    traces = handler.handle(
        ListTraceEventsCommand(workflow_id="workflow:r3-command-demo")
    )
    assert traces.ok is True
    assert [event["event_type"] for event in traces.value] == [
        "proposal_submitted",
        "admission_rejected",
    ]


def test_runtime_command_handler_submits_and_accepts_proposal():
    handler = RuntimeCommandHandler()
    bootstrap(handler)

    assert handler.handle(
        SubmitProposalCommand(proposal_envelope("proposal:r3-command:accepted"))
    ).ok is True

    accepted = handler.handle(
        AcceptProposalCommand(
            proposal_id="proposal:r3-command:accepted",
            reason="proposal committed through kernel path",
            committed_rids=("rid:r3-command:001",),
            audit_ref="reports/r3/runtime_command_demo_001.md",
        )
    )

    assert accepted.ok is True
    assert accepted.value["accepted"] is True
    assert accepted.value["committed_rids"] == ("rid:r3-command:001",)

    status = handler.handle(
        QueryWorkflowStatusCommand(workflow_id="workflow:r3-command-demo")
    )
    assert status.value["accepted_count"] == 1
    assert status.value["rejected_count"] == 0


def test_runtime_command_handler_returns_failure_result_for_bad_command():
    handler = RuntimeCommandHandler()
    bootstrap(handler)

    duplicate = handler.handle(CreateWorkflowCommand(workflow_spec()))

    assert duplicate.ok is False
    assert duplicate.command_type == "CreateWorkflowCommand"
    assert duplicate.error_code == "COMMAND_FAILED"
    assert "workflow already exists" in duplicate.error_message


def test_runtime_command_handler_rejects_unbound_agent_proposal():
    handler = RuntimeCommandHandler()

    assert handler.handle(CreateWorkflowCommand(workflow_spec())).ok is True
    assert handler.handle(BindWorkflowCommand(workflow_binding())).ok is True
    assert handler.handle(CreateAgentCommand(agent_spec())).ok is True

    result = handler.handle(SubmitProposalCommand(proposal_envelope()))

    assert result.ok is False
    assert result.error_code == "COMMAND_FAILED"
    assert "agent is not bound" in result.error_message
