from __future__ import annotations

import pytest

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.registry import (
    AgentRegistry,
    RuntimeRegistry,
    WorkflowRegistry,
)


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


def test_workflow_registry_creates_and_gets_workflow():
    registry = WorkflowRegistry()

    spec = registry.create_workflow(workflow_spec())

    assert registry.get_workflow("workflow:r3-demo") == spec

    with pytest.raises(ValueError):
        registry.create_workflow(workflow_spec())

    with pytest.raises(KeyError):
        registry.get_workflow("workflow:missing")


def test_workflow_registry_creates_binding_only_for_known_workflow():
    registry = WorkflowRegistry()

    with pytest.raises(KeyError):
        registry.create_binding(workflow_binding())

    registry.create_workflow(workflow_spec())
    binding = registry.create_binding(workflow_binding())

    assert registry.get_binding("binding:r3-demo") == binding

    with pytest.raises(ValueError):
        registry.create_binding(workflow_binding())


def test_workflow_registry_rejects_tenant_or_fsm_mismatch():
    registry = WorkflowRegistry()
    registry.create_workflow(workflow_spec())

    with pytest.raises(ValueError):
        registry.create_binding(
            WorkflowBinding(
                binding_id="binding:wrong-tenant",
                workflow_id="workflow:r3-demo",
                tenant_id="tenant:other",
                entity_id="entity:r3-demo",
                fsm="CampusTourFSM",
                initial_state="not_started",
            )
        )

    with pytest.raises(ValueError):
        registry.create_binding(
            WorkflowBinding(
                binding_id="binding:wrong-fsm",
                workflow_id="workflow:r3-demo",
                tenant_id="tenant:r3",
                entity_id="entity:r3-demo",
                fsm="OtherFSM",
                initial_state="not_started",
            )
        )


def test_agent_registry_creates_and_gets_agent():
    registry = AgentRegistry()

    spec = registry.create_agent(agent_spec())

    assert registry.get_agent("agent:planner") == spec

    with pytest.raises(ValueError):
        registry.create_agent(agent_spec())

    with pytest.raises(KeyError):
        registry.get_agent("agent:missing")


def test_agent_registry_creates_binding_against_workflow_registry():
    runtime = RuntimeRegistry()
    runtime.workflows.create_workflow(workflow_spec())
    runtime.workflows.create_binding(workflow_binding())
    runtime.agents.create_agent(agent_spec())

    binding = runtime.agents.create_binding(
        agent_binding(),
        workflow_registry=runtime.workflows,
    )

    assert runtime.agents.get_binding("agent-binding:planner:r3-demo") == binding

    with pytest.raises(ValueError):
        runtime.agents.create_binding(
            agent_binding(),
            workflow_registry=runtime.workflows,
        )


def test_agent_registry_rejects_binding_to_unknown_agent():
    runtime = RuntimeRegistry()
    runtime.workflows.create_workflow(workflow_spec())
    runtime.workflows.create_binding(workflow_binding())

    with pytest.raises(KeyError):
        runtime.agents.create_binding(
            agent_binding(),
            workflow_registry=runtime.workflows,
        )


def test_agent_registry_rejects_binding_to_unknown_workflow_binding():
    runtime = RuntimeRegistry()
    runtime.workflows.create_workflow(workflow_spec())
    runtime.agents.create_agent(agent_spec())

    with pytest.raises(KeyError):
        runtime.agents.create_binding(
            agent_binding(),
            workflow_registry=runtime.workflows,
        )


def test_agent_registry_rejects_scope_mismatch():
    runtime = RuntimeRegistry()
    runtime.workflows.create_workflow(workflow_spec())
    runtime.workflows.create_binding(workflow_binding())
    runtime.agents.create_agent(agent_spec())

    with pytest.raises(ValueError):
        runtime.agents.create_binding(
            AgentBinding(
                agent_binding_id="agent-binding:wrong-entity",
                agent_id="agent:planner",
                workflow_id="workflow:r3-demo",
                tenant_id="tenant:r3",
                binding_id="binding:r3-demo",
                entity_id="entity:other",
                role="planner",
            ),
            workflow_registry=runtime.workflows,
        )
