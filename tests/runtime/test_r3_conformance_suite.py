from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from mnemosyne.runtime.admission import RuntimeAdmissionFacade
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
from mnemosyne.runtime.demo import run_local_runtime_demo
from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeAdmissionDecision,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.proposals import RuntimeProposalStore
from mnemosyne.runtime.r3_runner import run_runtime_command_demo
from mnemosyne.runtime.registry import RuntimeRegistry
from mnemosyne.runtime.session import LocalRuntimeSession


def workflow_spec() -> WorkflowSpec:
    return WorkflowSpec(
        workflow_id="workflow:r3-conformance",
        tenant_id="tenant:r3",
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        fsm="CampusTourFSM",
        workflow_type="conformance",
        created_by="user:edward",
    )


def workflow_binding() -> WorkflowBinding:
    return WorkflowBinding(
        binding_id="binding:r3-conformance",
        workflow_id="workflow:r3-conformance",
        tenant_id="tenant:r3",
        entity_id="entity:r3-conformance",
        fsm="CampusTourFSM",
        initial_state="not_started",
        created_by="user:edward",
    )


def agent_spec() -> AgentSpec:
    return AgentSpec(
        agent_id="agent:r3-conformance-planner",
        tenant_id="tenant:r3",
        agent_type="planner",
        display_name="R3 Conformance Planner",
        created_by="user:edward",
        capabilities=("propose", "repair"),
    )


def agent_binding() -> AgentBinding:
    return AgentBinding(
        agent_binding_id="agent-binding:r3-conformance-planner",
        agent_id="agent:r3-conformance-planner",
        workflow_id="workflow:r3-conformance",
        tenant_id="tenant:r3",
        binding_id="binding:r3-conformance",
        entity_id="entity:r3-conformance",
        role="planner",
        permissions=("propose", "repair"),
    )


def proposal_envelope(proposal_id: str = "proposal:r3-conformance:001") -> RuntimeProposalEnvelope:
    return RuntimeProposalEnvelope(
        proposal_id=proposal_id,
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-conformance",
        binding_id="binding:r3-conformance",
        entity_id="entity:r3-conformance",
        agent_id="agent:r3-conformance-planner",
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
            "stage": "R3.8",
            "source": "r3-conformance-suite",
        },
    )


def build_registry() -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.workflows.create_workflow(workflow_spec())
    registry.workflows.create_binding(workflow_binding())
    registry.agents.create_agent(agent_spec())
    registry.agents.create_binding(
        agent_binding(),
        workflow_registry=registry.workflows,
    )
    return registry


def bootstrap_handler(handler: RuntimeCommandHandler) -> None:
    assert handler.handle(CreateWorkflowCommand(workflow_spec())).ok is True
    assert handler.handle(BindWorkflowCommand(workflow_binding())).ok is True
    assert handler.handle(CreateAgentCommand(agent_spec())).ok is True
    assert handler.handle(BindAgentCommand(agent_binding())).ok is True


def test_r3_0_runtime_models_are_immutable_and_validate_required_identity():
    spec = workflow_spec()

    assert spec.workflow_id == "workflow:r3-conformance"

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

    proposal = proposal_envelope()
    assert proposal.proposal_id == "proposal:r3-conformance:001"
    assert proposal.agent_id == "agent:r3-conformance-planner"


def test_r3_1_registries_reject_duplicates_and_bad_scope():
    registry = RuntimeRegistry()

    registry.workflows.create_workflow(workflow_spec())

    with pytest.raises(ValueError):
        registry.workflows.create_workflow(workflow_spec())

    with pytest.raises(ValueError):
        registry.workflows.create_binding(
            WorkflowBinding(
                binding_id="binding:bad-tenant",
                workflow_id="workflow:r3-conformance",
                tenant_id="tenant:other",
                entity_id="entity:r3-conformance",
                fsm="CampusTourFSM",
                initial_state="not_started",
            )
        )

    registry.workflows.create_binding(workflow_binding())
    registry.agents.create_agent(agent_spec())

    with pytest.raises(ValueError):
        registry.agents.create_binding(
            AgentBinding(
                agent_binding_id="agent-binding:bad-entity",
                agent_id="agent:r3-conformance-planner",
                workflow_id="workflow:r3-conformance",
                tenant_id="tenant:r3",
                binding_id="binding:r3-conformance",
                entity_id="entity:other",
                role="planner",
            ),
            workflow_registry=registry.workflows,
        )


def test_r3_2_proposal_lifecycle_enforces_one_decision_per_proposal():
    registry = build_registry()
    store = RuntimeProposalStore()

    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )

    first = RuntimeAdmissionDecision(
        decision_id="decision:r3-conformance:first",
        proposal_id="proposal:r3-conformance:001",
        tenant_id="tenant:r3",
        workflow_id="workflow:r3-conformance",
        accepted=False,
        reason="first rejection",
        error_codes=("REJECTED",),
    )

    store.record_decision(first)

    with pytest.raises(ValueError):
        store.record_decision(
            RuntimeAdmissionDecision(
                decision_id="decision:r3-conformance:second",
                proposal_id="proposal:r3-conformance:001",
                tenant_id="tenant:r3",
                workflow_id="workflow:r3-conformance",
                accepted=False,
                reason="second rejection",
                error_codes=("REJECTED",),
            )
        )

    assert [event.event_type for event in store.list_trace_events()] == [
        "proposal_submitted",
        "admission_rejected",
    ]


def test_r3_3_admission_facade_rejects_malformed_admission_calls():
    registry = build_registry()
    store = RuntimeProposalStore()
    store.submit_proposal(
        proposal_envelope(),
        registry=registry,
    )
    admission = RuntimeAdmissionFacade(store)

    with pytest.raises(ValueError):
        admission.reject_proposal(
            proposal_id="proposal:r3-conformance:001",
            reason="missing codes",
            error_codes=(),
        )

    with pytest.raises(ValueError):
        admission.accept_proposal(
            proposal_id="proposal:r3-conformance:001",
            reason="missing rids",
            committed_rids=(),
        )

    decision = admission.reject_proposal(
        proposal_id="proposal:r3-conformance:001",
        reason="domain feasibility rejected before commit",
        error_codes=("DOMAIN_FEASIBILITY_REJECTED",),
    )

    assert decision.accepted is False
    assert decision.committed_rids == ()


def test_r3_4_local_session_rejects_unbound_agent_proposal_and_reports_status():
    session = LocalRuntimeSession()
    session.create_workflow(workflow_spec())
    session.bind_workflow(workflow_binding())
    session.create_agent(agent_spec())

    with pytest.raises(ValueError):
        session.submit_proposal(proposal_envelope())

    session.bind_agent(agent_binding())
    session.submit_proposal(proposal_envelope())
    session.reject_proposal(
        proposal_id="proposal:r3-conformance:001",
        reason="domain feasibility rejected before commit",
        error_codes=("DOMAIN_FEASIBILITY_REJECTED",),
    )

    status = session.runtime_status("workflow:r3-conformance")
    assert status["proposal_count"] == 1
    assert status["decision_count"] == 1
    assert status["rejected_count"] == 1
    assert status["trace_event_count"] == 2


def test_r3_5_local_runtime_demo_produces_integrated_evidence():
    result = run_local_runtime_demo()

    assert result["stage"] == "R3.5"
    assert result["runtime_status"]["proposal_count"] == 2
    assert result["runtime_status"]["decision_count"] == 2
    assert result["runtime_status"]["accepted_count"] == 1
    assert result["runtime_status"]["rejected_count"] == 1

    trace_types = [event["event_type"] for event in result["trace_events"]]
    assert trace_types == [
        "proposal_submitted",
        "admission_accepted",
        "proposal_submitted",
        "admission_rejected",
    ]


def test_r3_6_command_api_preserves_runtime_semantics():
    handler = RuntimeCommandHandler()
    bootstrap_handler(handler)

    submit = handler.handle(SubmitProposalCommand(proposal_envelope()))
    assert submit.ok is True

    reject = handler.handle(
        RejectProposalCommand(
            proposal_id="proposal:r3-conformance:001",
            reason="deadline violation rejected before commit",
            error_codes=("DOMAIN_FEASIBILITY_REJECTED", "DEADLINE_MISSED"),
        )
    )

    assert reject.ok is True
    assert reject.value["accepted"] is False

    status = handler.handle(QueryWorkflowStatusCommand("workflow:r3-conformance"))
    assert status.ok is True
    assert status.value["proposal_count"] == 1
    assert status.value["rejected_count"] == 1

    traces = handler.handle(ListTraceEventsCommand("workflow:r3-conformance"))
    assert traces.ok is True
    assert [event["event_type"] for event in traces.value] == [
        "proposal_submitted",
        "admission_rejected",
    ]


def test_r3_6_command_api_can_record_acceptance():
    handler = RuntimeCommandHandler()
    bootstrap_handler(handler)

    assert handler.handle(
        SubmitProposalCommand(proposal_envelope("proposal:r3-conformance:accepted"))
    ).ok is True

    accepted = handler.handle(
        AcceptProposalCommand(
            proposal_id="proposal:r3-conformance:accepted",
            reason="proposal committed through kernel path",
            committed_rids=("rid:r3-conformance:001",),
        )
    )

    assert accepted.ok is True
    assert accepted.value["accepted"] is True
    assert accepted.value["committed_rids"] == ("rid:r3-conformance:001",)


def test_r3_7_command_runner_produces_reproducible_command_evidence():
    result = run_runtime_command_demo()

    assert result["stage"] == "R3.7"
    assert result["demo_id"] == "runtime_command_demo_001"
    assert result["all_commands_ok"] is True
    assert result["command_count"] == 10

    command_types = [item["command_type"] for item in result["command_results"]]
    assert command_types == [
        "CreateWorkflowCommand",
        "BindWorkflowCommand",
        "CreateAgentCommand",
        "BindAgentCommand",
        "SubmitProposalCommand",
        "AcceptProposalCommand",
        "SubmitProposalCommand",
        "RejectProposalCommand",
        "QueryWorkflowStatusCommand",
        "ListTraceEventsCommand",
    ]

    assert result["runtime_status"]["proposal_count"] == 2
    assert result["runtime_status"]["accepted_count"] == 1
    assert result["runtime_status"]["rejected_count"] == 1


def test_r3_5_and_r3_7_evidence_artifacts_exist_and_have_expected_content():
    r35_json = Path("results/r3/local_runtime_demo_001.json")
    r35_report = Path("reports/r3/local_runtime_demo_001.md")
    r37_json = Path("results/r3/runtime_command_demo_001.json")
    r37_report = Path("reports/r3/runtime_command_demo_001.md")

    for path in [r35_json, r35_report, r37_json, r37_report]:
        assert path.exists(), f"missing R3 evidence artifact: {path}"

    r35 = json.loads(r35_json.read_text(encoding="utf-8"))
    r37 = json.loads(r37_json.read_text(encoding="utf-8"))

    assert r35["stage"] == "R3.5"
    assert r35["runtime_status"]["trace_event_count"] == 4
    assert r37["stage"] == "R3.7"
    assert r37["all_commands_ok"] is True
    assert r37["runtime_status"]["trace_event_count"] == 4

    assert "R3.5 Local Runtime Demo" in r35_report.read_text(encoding="utf-8")
    assert "R3.7 Runtime Command Demo" in r37_report.read_text(encoding="utf-8")
