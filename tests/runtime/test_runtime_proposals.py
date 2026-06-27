from __future__ import annotations

import pytest

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeAdmissionDecision,
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


def proposal_envelope(
    *,
    proposal_id: str = "proposal:r3:001",
    tenant_id: str = "tenant:r3",
    workflow_id: str = "workflow:r3-demo",
    binding_id: str = "binding:r3-demo",
    entity_id: str = "entity:r3-demo",
    agent_id: str = "agent:planner",
    app_id: str = "campus_tour",
    schema_id: str = "campus_tour.transition",
) -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id=proposal_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        binding_id=binding_id,
        entity_id=entity_id,
        agent_id=agent_id,
        app_id=app_id,
        schema_id=schema_id,
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
            "stage": "R3.2",
            "source": "test",
        },
    )


def test_runtime_proposal_store_submits_and_gets_proposal():
    registry = build_registry()
    store = RuntimeProposalStore()

    envelope = store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    assert store.get_proposal("proposal:r3:001") == envelope
    assert store.list_proposals_for_workflow("workflow:r3-demo") == [envelope]
    assert store.list_proposals_for_agent("agent:planner") == [envelope]

    trace = store.list_trace_events()
    assert len(trace) == 1
    assert trace[0].event_type == "proposal_submitted"
    assert trace[0].proposal_id == "proposal:r3:001"


def test_runtime_proposal_store_rejects_duplicate_proposal():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    with pytest.raises(ValueError):
        store.submit_proposal(
            proposal_envelope(),
            registry=registry,
        )


def test_runtime_proposal_store_rejects_unknown_scope():
    registry = build_registry()
    store = RuntimeProposalStore()

    with pytest.raises(KeyError):
        store.submit_proposal(
            proposal_envelope(workflow_id="workflow:missing"),
            registry=registry,
        )

    with pytest.raises(KeyError):
        store.submit_proposal(
            proposal_envelope(agent_id="agent:missing"),
            registry=registry,
        )


def test_runtime_proposal_store_rejects_scope_mismatch():
    registry = build_registry()
    store = RuntimeProposalStore()

    with pytest.raises(ValueError):
        store.submit_proposal(
            proposal_envelope(tenant_id="tenant:other"),
            registry=registry,
        )

    with pytest.raises(ValueError):
        store.submit_proposal(
            proposal_envelope(entity_id="entity:other"),
            registry=registry,
        )

    with pytest.raises(ValueError):
        store.submit_proposal(
            proposal_envelope(app_id="wrong_app"),
            registry=registry,
        )

    with pytest.raises(ValueError):
        store.submit_proposal(
            proposal_envelope(schema_id="wrong_schema"),
            registry=registry,
        )


def test_runtime_proposal_store_records_rejection_decision():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

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

    stored = store.record_decision(decision)

    assert store.get_decision("decision:r3:reject:001") == stored
    assert store.get_decision_for_proposal("proposal:r3:001") == stored

    trace = store.list_trace_events()
    assert [event.event_type for event in trace] == [
        "proposal_submitted",
        "admission_rejected",
    ]
    assert trace[-1].decision_id == "decision:r3:reject:001"
    assert trace[-1].details["error_codes"] == ["DOMAIN_FEASIBILITY_REJECTED"]


def test_runtime_proposal_store_records_acceptance_decision():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    decision = RuntimeAdmissionDecision(
        decision_id="decision:r3:accept:001",
        proposal_id="proposal:r3:001",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-demo",
        accepted=True,
        reason="proposal committed through kernel path",
        committed_rids=["rid:1", "rid:2"],
    )

    stored = store.record_decision(decision)

    assert stored.accepted is True
    assert stored.committed_rids == ("rid:1", "rid:2")
    assert store.list_trace_events()[-1].event_type == "admission_accepted"


def test_runtime_proposal_store_rejects_invalid_decision_state():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:bad-accepted",
                proposal_id="proposal:r3:001",
                tenant_id="tenant:r3",
                workflow_id="workflow:r3-demo",
                accepted=True,
                reason="bad accepted decision",
                error_codes=["SHOULD_NOT_BE_HERE"],
            )
        )

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:bad-rejected",
                proposal_id="proposal:r3:001",
                tenant_id="tenant:r3",
                workflow_id="workflow:r3-demo",
                accepted=False,
                reason="bad rejected decision",
                error_codes=["REJECTED"],
                committed_rids=["rid:should-not-exist"],
            )
        )


def test_runtime_proposal_store_allows_only_one_decision_per_proposal():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    store.record_decision(
        RuntimeAdmissionDecision(
            decision_id="decision:r3:first",
            proposal_id="proposal:r3:001",
            tenant_id="tenant:r3",
            workflow_id="workflow:r3-demo",
            accepted=False,
            reason="first decision",
            error_codes=["REJECTED"],
        )
    )

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:second",
                proposal_id="proposal:r3:001",
                tenant_id="tenant:r3",
                workflow_id="workflow:r3-demo",
                accepted=False,
                reason="second decision",
                error_codes=["REJECTED"],
            )
        )


def test_runtime_proposal_store_rejects_decision_for_unknown_or_mismatched_proposal():
    registry = build_registry()
    store = RuntimeProposalStore()

    with pytest.raises(KeyError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:missing",
                proposal_id="proposal:missing",
                tenant_id="tenant:r3",
                workflow_id="workflow:r3-demo",
                accepted=False,
                reason="missing proposal",
                error_codes=["MISSING"],
            )
        )

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:wrong-tenant",
                proposal_id="proposal:r3:001",
                tenant_id="tenant:other",
                workflow_id="workflow:r3-demo",
                accepted=False,
                reason="wrong tenant",
                error_codes=["WRONG_TENANT"],
            )
        )

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3:wrong-workflow",
                proposal_id="proposal:r3:001",
                tenant_id="tenant:r3",
                workflow_id="workflow:other",
                accepted=False,
                reason="wrong workflow",
                error_codes=["WRONG_WORKFLOW"],
            )
        )
