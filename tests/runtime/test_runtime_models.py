from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeAdmissionDecision,
    RuntimeProposalEnvelope,
    RuntimeTraceEvent,
    WorkflowBinding,
    WorkflowSpec,
)


def test_workflow_spec_requires_identity_and_is_frozen():
    spec = WorkflowSpec(
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        fsm="CampusTourFSM",
        workflow_type="demo",
        created_by="user:edward",
        metadata={"purpose": "R3.0"},
    )

    assert spec.workflow_id == "workflow:r3-demo"
    assert spec.tenant_id == "tenant:r3"
    assert spec.metadata == {"purpose": "R3.0"}

    with pytest.raises(FrozenInstanceError):
        spec.workflow_id = "workflow:changed"  # type: ignore[misc]

    with pytest.raises(ValueError):
        WorkflowSpec(
            workflow_id="",
            tenant_id="tenant:r3",
            app_id="campus_tour",
            schema_id="campus_tour.transition",
            fsm="CampusTourFSM",
        )


def test_workflow_binding_names_entity_scope():
    binding = WorkflowBinding(
        binding_id="binding:r3-demo",
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        entity_id="entity:r3-demo",
        fsm="CampusTourFSM",
        initial_state="not_started",
        created_by="user:edward",
    )

    assert binding.binding_id == "binding:r3-demo"
    assert binding.workflow_id == "workflow:r3-demo"
    assert binding.entity_id == "entity:r3-demo"
    assert binding.initial_state == "not_started"


def test_agent_spec_and_binding_define_agent_workflow_scope():
    agent = AgentSpec(
        agent_id="agent:planner",
        tenant_id="tenant:r3",
        agent_type="planner",
        display_name="Planning Agent",
        created_by="user:edward",
        capabilities=["propose_plan", "repair_plan"],
        model_id="local-test-agent",
    )

    assert agent.capabilities == ("propose_plan", "repair_plan")

    binding = AgentBinding(
        agent_binding_id="agent-binding:planner:r3-demo",
        agent_id=agent.agent_id,
        workflow_id="workflow:r3-demo",
        tenant_id="tenant:r3",
        binding_id="binding:r3-demo",
        entity_id="entity:r3-demo",
        role="planner",
        permissions=["propose", "repair"],
    )

    assert binding.agent_id == "agent:planner"
    assert binding.workflow_id == "workflow:r3-demo"
    assert binding.permissions == ("propose", "repair")


def test_runtime_proposal_envelope_carries_agent_and_provenance():
    envelope = RuntimeProposalEnvelope(
        proposal_id="proposal:r3:001",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        binding_id="binding:r3-demo",
        entity_id="entity:r3-demo",
        agent_id="agent:planner",
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
            "source": "runtime-model-test",
            "stage": "R3.0",
        },
    )

    assert envelope.proposal_id == "proposal:r3:001"
    assert envelope.agent_id == "agent:planner"
    assert envelope.payload["finish_time"] == "12:10"
    assert envelope.assumptions[0]["key"] == "deadline"
    assert envelope.provenance["stage"] == "R3.0"


def test_runtime_admission_decision_records_rejection_without_commit():
    decision = RuntimeAdmissionDecision(
        decision_id="decision:r3:reject:001",
        proposal_id="proposal:r3:001",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        accepted=False,
        reason="domain feasibility rejected before commit",
        error_codes=["DOMAIN_FEASIBILITY_REJECTED"],
        committed_rids=[],
        audit_ref="reports/r3/admission_001.md",
    )

    assert decision.accepted is False
    assert decision.error_codes == ("DOMAIN_FEASIBILITY_REJECTED",)
    assert decision.committed_rids == ()
    assert decision.audit_ref == "reports/r3/admission_001.md"


def test_runtime_admission_decision_records_commit_rids_when_accepted():
    decision = RuntimeAdmissionDecision(
        decision_id="decision:r3:accept:001",
        proposal_id="proposal:r3:002",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        accepted=True,
        reason="proposal committed through kernel path",
        committed_rids=["rid:1", "rid:2"],
    )

    assert decision.accepted is True
    assert decision.error_codes == ()
    assert decision.committed_rids == ("rid:1", "rid:2")


def test_runtime_trace_event_serializes_to_json():
    event = RuntimeTraceEvent(
        event_id="trace:r3:001",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        event_type="proposal_rejected",
        actor_id="agent:planner",
        proposal_id="proposal:r3:001",
        decision_id="decision:r3:reject:001",
        details={
            "error_codes": ["DOMAIN_FEASIBILITY_REJECTED"],
        },
    )

    encoded = json.dumps(asdict(event), sort_keys=True)

    assert "proposal_rejected" in encoded
    assert "DOMAIN_FEASIBILITY_REJECTED" in encoded
