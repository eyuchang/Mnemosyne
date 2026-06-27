# File: mnemosyne/runtime/registry.py
#
# Purpose:
#   R3 in-memory workflow and agent registries.
#
# Design rule:
#   Registries create and look up runtime substrate objects.
#   They do not commit records and do not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass, field

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    WorkflowBinding,
    WorkflowSpec,
)


@dataclass
class WorkflowRegistry:
    workflows: dict[str, WorkflowSpec] = field(default_factory=dict)
    bindings: dict[str, WorkflowBinding] = field(default_factory=dict)

    def create_workflow(self, spec: WorkflowSpec) -> WorkflowSpec:
        if spec.workflow_id in self.workflows:
            raise ValueError(f"workflow already exists: {spec.workflow_id}")

        self.workflows[spec.workflow_id] = spec
        return spec

    def get_workflow(self, workflow_id: str) -> WorkflowSpec:
        try:
            return self.workflows[workflow_id]
        except KeyError as exc:
            raise KeyError(f"unknown workflow_id: {workflow_id}") from exc

    def create_binding(self, binding: WorkflowBinding) -> WorkflowBinding:
        if binding.binding_id in self.bindings:
            raise ValueError(f"workflow binding already exists: {binding.binding_id}")

        if binding.workflow_id not in self.workflows:
            raise KeyError(f"unknown workflow_id: {binding.workflow_id}")

        workflow = self.workflows[binding.workflow_id]

        if binding.tenant_id != workflow.tenant_id:
            raise ValueError(
                f"binding tenant_id does not match workflow tenant_id: "
                f"{binding.tenant_id} != {workflow.tenant_id}"
            )

        if binding.fsm != workflow.fsm:
            raise ValueError(
                f"binding fsm does not match workflow fsm: "
                f"{binding.fsm} != {workflow.fsm}"
            )

        self.bindings[binding.binding_id] = binding
        return binding

    def get_binding(self, binding_id: str) -> WorkflowBinding:
        try:
            return self.bindings[binding_id]
        except KeyError as exc:
            raise KeyError(f"unknown binding_id: {binding_id}") from exc


@dataclass
class AgentRegistry:
    agents: dict[str, AgentSpec] = field(default_factory=dict)
    bindings: dict[str, AgentBinding] = field(default_factory=dict)

    def create_agent(self, spec: AgentSpec) -> AgentSpec:
        if spec.agent_id in self.agents:
            raise ValueError(f"agent already exists: {spec.agent_id}")

        self.agents[spec.agent_id] = spec
        return spec

    def get_agent(self, agent_id: str) -> AgentSpec:
        try:
            return self.agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"unknown agent_id: {agent_id}") from exc

    def create_binding(
        self,
        binding: AgentBinding,
        *,
        workflow_registry: WorkflowRegistry,
    ) -> AgentBinding:
        if binding.agent_binding_id in self.bindings:
            raise ValueError(
                f"agent binding already exists: {binding.agent_binding_id}"
            )

        if binding.agent_id not in self.agents:
            raise KeyError(f"unknown agent_id: {binding.agent_id}")

        workflow_binding = workflow_registry.get_binding(binding.binding_id)
        workflow = workflow_registry.get_workflow(binding.workflow_id)
        agent = self.agents[binding.agent_id]

        if binding.tenant_id != agent.tenant_id:
            raise ValueError(
                f"agent binding tenant_id does not match agent tenant_id: "
                f"{binding.tenant_id} != {agent.tenant_id}"
            )

        if binding.tenant_id != workflow.tenant_id:
            raise ValueError(
                f"agent binding tenant_id does not match workflow tenant_id: "
                f"{binding.tenant_id} != {workflow.tenant_id}"
            )

        if binding.workflow_id != workflow_binding.workflow_id:
            raise ValueError(
                f"agent binding workflow_id does not match workflow binding: "
                f"{binding.workflow_id} != {workflow_binding.workflow_id}"
            )

        if binding.entity_id != workflow_binding.entity_id:
            raise ValueError(
                f"agent binding entity_id does not match workflow binding: "
                f"{binding.entity_id} != {workflow_binding.entity_id}"
            )

        self.bindings[binding.agent_binding_id] = binding
        return binding

    def get_binding(self, agent_binding_id: str) -> AgentBinding:
        try:
            return self.bindings[agent_binding_id]
        except KeyError as exc:
            raise KeyError(f"unknown agent_binding_id: {agent_binding_id}") from exc


@dataclass
class RuntimeRegistry:
    workflows: WorkflowRegistry = field(default_factory=WorkflowRegistry)
    agents: AgentRegistry = field(default_factory=AgentRegistry)
