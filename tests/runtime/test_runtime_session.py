from __future__ import annotations

import pytest

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.session import LocalRuntimeSession


def workflow_spec() -> WorkflowSpec:
    return WorkflowSpec(
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        fsm="CampusTourFSM",
        workflow_type="demo",
        created_by="user:edward",
    )


def workflow_binding() -> WorkflowBinding:
    return WorkflowBinding(
        binding_id="binding:r3-demo",
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        entity_id="entity:r3-demo",
        fsm="CampusTourFSM",
        initial_state="not_started",
        created_by="user:edward",
    )


def agent_spec() -> AgentSpec:
    return AgentSpec(
        agent_id="agent:planner",
        tenant_id="tenant:r3",
        agent_type="planner",
        display_name="Planning Agent",
        created_by="user:edward",
        capabilities=["propose", "repair"],
    )


def agent_binding() -> AgentBinding:
    return AgentBinding(
        agent_binding_id="agent-binding:planner:r3-demo",
        agent_id="agent:planner",
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        binding_id="binding:r3-demo",
        entity_id="entity:r3-demo",
        role="planner",
        permissions=["propose", "repair"],
    )


def proposal_envelope(
    *,
    proposal_id: str = "proposal:r3:001",
    agent_id: str = "agent:planner",
) -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id=proposal_id,
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        binding_id="binding:r3-demo",
        entity_id="entity:r3-demo",
        agent_id=agent_id,
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        proposal_kind="plan",
        payload={
            "route": ["S", "D", "A", "B", "L", "S"],
            "finish_time": "12:10",
        },
        assumptions=[
            {
                "key": "deadline",
                "value": "17:00",
                "source": "user_request",
            }
        ],
        provenance={
            "stage": "R3.4",
            "source": "test",
        },
    )


def build_bound_session() -> LocalRuntimeSession:
    session = LocalRuntimeSession()

    session.create_workflow(workflow_spec())
    session.bind_workflow(workflow_binding())
    session.create_agent(agent_spec())
    session.bind_agent(agent_binding())

    return session


def test_local_runtime_session_creates_workflow_agent_and_bindings():
    session = build_bound_session()

    assert session.registry.workflows.get_workflow("workflow:r3-demo").app_id == "campus_tour"
    assert session.registry.workflows.get_binding("binding:r3-demo").entity_id == "entity:r3-demo"
    assert session.registry.agents.get_agent("agent:planner").agent_type == "planner"
    assert (
        session.registry.agents.get_binding("agent-binding:planner:r3-demo").role
        == "planner"
    )


def test_local_runtime_session_submits_proposal_only_for_bound_agent():
    session = build_bound_session()

    proposal = session.submit_proposal(proposal_envelope())

    assert session.get_proposal("proposal:r3:001") == proposal

    trace = session.list_trace_events()
    assert len(trace) == 1
    assert trace[0].event_type == "proposal_submitted"


def test_local_runtime_session_rejects_unbound_agent_proposal():
    session = LocalRuntimeSession()

    session.create_workflow(workflow_spec())
    session.bind_workflow(workflow_binding())
    session.create_agent(agent_spec())

    with pytest.raises(ValueError):
        session.submit_proposal(proposal_envelope())


def test_local_runtime_session_rejects_unknown_agent_proposal_before_store_submit():
    session = build_bound_session()

    with pytest.raises(ValueError):
        session.submit_proposal(
            proposal_envelope(
                proposal_id="proposal:r3:unknown-agent",
                agent_id="agent:missing",
            )
        )


def test_local_runtime_session_records_rejection_decision_and_status():
    session = build_bound_session()
    session.submit_proposal(proposal_envelope())

    decision = session.reject_proposal(
        proposal_id="proposal:r3:001",
        reason="domain feasibility rejected before commit",
        error_codes=["DOMAIN_FEASIBILITY_REJECTED"],
        audit_ref="reports/r3/admission_001.md",
    )

    assert decision.accepted is False
    assert session.get_decision_for_proposal("proposal:r3:001") == decision

    status = session.runtime_status("workflow:r3-demo")
    assert status == {
        "workflow_id": "workflow:r3-demo",
        "proposal_count": 1,
        "decision_count": 1,
        "accepted_count": 0,
        "rejected_count": 1,
        "trace_event_count": 2,
    }

    assert [event.event_type for event in session.list_trace_events()] == [
        "proposal_submitted",
        "admission_rejected",
    ]


def test_local_runtime_session_records_acceptance_decision_and_status():
    session = build_bound_session()
    session.submit_proposal(proposal_envelope())

    decision = session.accept_proposal(
        proposal_id="proposal:r3:001",
        reason="proposal committed through kernel path",
        committed_rids=["rid:1", "rid:2"],
        audit_ref="reports/r3/admission_accept_001.md",
    )

    assert decision.accepted is True
    assert decision.committed_rids == ("rid:1", "rid:2")

    status = session.runtime_status("workflow:r3-demo")
    assert status["proposal_count"] == 1
    assert status["decision_count"] == 1
    assert status["accepted_count"] == 1
    assert status["rejected_count"] == 0
    assert status["trace_event_count"] == 2

    assert [event.event_type for event in session.list_trace_events()] == [
        "proposal_submitted",
        "admission_accepted",
    ]


def test_local_runtime_session_runtime_status_rejects_unknown_workflow():
    session = LocalRuntimeSession()

    with pytest.raises(KeyError):
        session.runtime_status("workflow:missing")
