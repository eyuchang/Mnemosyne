from __future__ import annotations

import pytest

from mnemosyne.runtime.admission import RuntimeAdmissionFacade
from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.proposals import RuntimeProposalStore
from mnemosyne.runtime.registry import RuntimeRegistry


def build_registry() -> RuntimeRegistry:
    registry = RuntimeRegistry()

    registry.workflows.create_workflow(
        WorkflowSpec(
            workflow_id="workflow:r3-demo",
            tenant_id="tenant:r3",
            app_id="campus_tour",
            schema_id="campus_tour.transition",
            fsm="CampusTourFSM",
            workflow_type="demo",
            created_by="user:edward",
        )
    )

    registry.workflows.create_binding(
        WorkflowBinding(
            binding_id="binding:r3-demo",
            workflow_id="workflow:r3-demo",
            tenant_id="tenant:r3",
            entity_id="entity:r3-demo",
            fsm="CampusTourFSM",
            initial_state="not_started",
            created_by="user:edward",
        )
    )

    registry.agents.create_agent(
        AgentSpec(
            agent_id="agent:planner",
            tenant_id="tenant:r3",
            agent_type="planner",
            display_name="Planning Agent",
            created_by="user:edward",
            capabilities=["propose", "repair"],
        )
    )

    registry.agents.create_binding(
        AgentBinding(
            agent_binding_id="agent-binding:planner:r3-demo",
            agent_id="agent:planner",
            workflow_id="workflow:r3-demo",
            tenant_id="tenant:r3",
            binding_id="binding:r3-demo",
            entity_id="entity:r3-demo",
            role="planner",
            permissions=["propose", "repair"],
        ),
        workflow_registry=registry.workflows,
    )

    return registry


def proposal_envelope() -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
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
            "stage": "R3.3",
            "source": "test",
        },
    )


def build_store_with_proposal() -> RuntimeProposalStore:
    registry = build_registry()
    store = RuntimeProposalStore()
    store.submit_proposal(proposal_envelope(), registry=registry)
    return store


def test_admission_facade_rejects_submitted_proposal():
    store = build_store_with_proposal()
    admission = RuntimeAdmissionFacade(store)

    decision = admission.reject_proposal(
        proposal_id="proposal:r3:001",
        reason="domain feasibility rejected before commit",
        error_codes=["DOMAIN_FEASIBILITY_REJECTED"],
        audit_ref="reports/r3/admission_001.md",
    )

    assert decision.accepted is False
    assert decision.tenant_id == "tenant:r3"
    assert decision.workflow_id == "workflow:r3-demo"
    assert decision.error_codes == ("DOMAIN_FEASIBILITY_REJECTED",)
    assert decision.committed_rids == ()
    assert admission.get_decision_for_proposal("proposal:r3:001") == decision

    trace_types = [event.event_type for event in store.list_trace_events()]
    assert trace_types == ["proposal_submitted", "admission_rejected"]


def test_admission_facade_accepts_submitted_proposal_with_commit_rids():
    store = build_store_with_proposal()
    admission = RuntimeAdmissionFacade(store)

    decision = admission.accept_proposal(
        proposal_id="proposal:r3:001",
        reason="proposal committed through kernel path",
        committed_rids=["rid:1", "rid:2"],
        audit_ref="reports/r3/admission_accepted_001.md",
    )

    assert decision.accepted is True
    assert decision.error_codes == ()
    assert decision.committed_rids == ("rid:1", "rid:2")

    trace_types = [event.event_type for event in store.list_trace_events()]
    assert trace_types == ["proposal_submitted", "admission_accepted"]


def test_admission_facade_reject_requires_error_codes():
    store = build_store_with_proposal()
    admission = RuntimeAdmissionFacade(store)

    with pytest.raises(ValueError):
        admission.reject_proposal(
            proposal_id="proposal:r3:001",
            reason="missing error codes",
            error_codes=[],
        )


def test_admission_facade_accept_requires_committed_rids():
    store = build_store_with_proposal()
    admission = RuntimeAdmissionFacade(store)

    with pytest.raises(ValueError):
        admission.accept_proposal(
            proposal_id="proposal:r3:001",
            reason="missing committed rids",
            committed_rids=[],
        )


def test_admission_facade_rejects_unknown_proposal():
    store = RuntimeProposalStore()
    admission = RuntimeAdmissionFacade(store)

    with pytest.raises(KeyError):
        admission.reject_proposal(
            proposal_id="proposal:missing",
            reason="unknown proposal",
            error_codes=["UNKNOWN_PROPOSAL"],
        )

    with pytest.raises(KeyError):
        admission.accept_proposal(
            proposal_id="proposal:missing",
            reason="unknown proposal",
            committed_rids=["rid:1"],
        )


def test_admission_facade_allows_only_one_decision_per_proposal():
    store = build_store_with_proposal()
    admission = RuntimeAdmissionFacade(store)

    admission.reject_proposal(
        proposal_id="proposal:r3:001",
        reason="first decision",
        error_codes=["REJECTED"],
    )

    with pytest.raises(ValueError):
        admission.reject_proposal(
            proposal_id="proposal:r3:001",
            reason="second decision",
            error_codes=["REJECTED"],
        )
