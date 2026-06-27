# File: mnemosyne/runtime/session.py
#
# Purpose:
#   R3 local in-memory runtime session.
#
# Design rule:
#   A LocalRuntimeSession coordinates workflow/agent metadata,
#   proposal lifecycle, and admission decisions.
#
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mnemosyne.runtime.admission import RuntimeAdmissionFacade
from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeAdmissionDecision,
    RuntimeProposalEnvelope,
    RuntimeTraceEvent,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.proposals import RuntimeProposalStore
from mnemosyne.runtime.registry import RuntimeRegistry


@dataclass
class LocalRuntimeSession:
    """In-memory R3 runtime session.

    This class is the first R3 object that connects the runtime vocabulary:

    - workflow creation
    - workflow binding
    - agent creation
    - agent-to-workflow binding
    - proposal submission
    - proposal admission
    - trace inspection

    Committed truth remains owned by the core kernel.
    """

    registry: RuntimeRegistry = field(default_factory=RuntimeRegistry)
    proposal_store: RuntimeProposalStore = field(default_factory=RuntimeProposalStore)
    admission: RuntimeAdmissionFacade = field(init=False)

    def __post_init__(self) -> None:
        self.admission = RuntimeAdmissionFacade(self.proposal_store)

    def create_workflow(self, spec: WorkflowSpec) -> WorkflowSpec:
        return self.registry.workflows.create_workflow(spec)

    def bind_workflow(self, binding: WorkflowBinding) -> WorkflowBinding:
        return self.registry.workflows.create_binding(binding)

    def create_agent(self, spec: AgentSpec) -> AgentSpec:
        return self.registry.agents.create_agent(spec)

    def bind_agent(self, binding: AgentBinding) -> AgentBinding:
        return self.registry.agents.create_binding(
            binding,
            workflow_registry=self.registry.workflows,
        )

    def submit_proposal(
        self,
        envelope: RuntimeProposalEnvelope,
    ) -> RuntimeProposalEnvelope:
        self._require_agent_bound_to_proposal_scope(envelope)
        return self.proposal_store.submit_proposal(
            envelope,
            registry=self.registry,
        )

    def reject_proposal(
        self,
        *,
        proposal_id: str,
        reason: str,
        error_codes: list[str] | tuple[str, ...],
        decision_id: str | None = None,
        audit_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeAdmissionDecision:
        return self.admission.reject_proposal(
            proposal_id=proposal_id,
            reason=reason,
            error_codes=error_codes,
            decision_id=decision_id,
            audit_ref=audit_ref,
            metadata=metadata,
        )

    def accept_proposal(
        self,
        *,
        proposal_id: str,
        reason: str,
        committed_rids: list[str] | tuple[str, ...],
        decision_id: str | None = None,
        audit_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeAdmissionDecision:
        return self.admission.accept_proposal(
            proposal_id=proposal_id,
            reason=reason,
            committed_rids=committed_rids,
            decision_id=decision_id,
            audit_ref=audit_ref,
            metadata=metadata,
        )

    def get_proposal(self, proposal_id: str) -> RuntimeProposalEnvelope:
        return self.proposal_store.get_proposal(proposal_id)

    def get_decision_for_proposal(
        self,
        proposal_id: str,
    ) -> RuntimeAdmissionDecision | None:
        return self.proposal_store.get_decision_for_proposal(proposal_id)

    def list_trace_events(self) -> list[RuntimeTraceEvent]:
        return self.proposal_store.list_trace_events()

    def runtime_status(self, workflow_id: str) -> dict[str, Any]:
        self.registry.workflows.get_workflow(workflow_id)

        proposals = self.proposal_store.list_proposals_for_workflow(workflow_id)
        decisions = [
            decision
            for proposal in proposals
            if (decision := self.proposal_store.get_decision_for_proposal(proposal.proposal_id))
            is not None
        ]

        return {
            "workflow_id": workflow_id,
            "proposal_count": len(proposals),
            "decision_count": len(decisions),
            "accepted_count": sum(1 for decision in decisions if decision.accepted),
            "rejected_count": sum(1 for decision in decisions if not decision.accepted),
            "trace_event_count": len(
                [
                    event
                    for event in self.proposal_store.list_trace_events()
                    if event.workflow_id == workflow_id
                ]
            ),
        }

    def _require_agent_bound_to_proposal_scope(
        self,
        envelope: RuntimeProposalEnvelope,
    ) -> None:
        for binding in self.registry.agents.bindings.values():
            if (
                binding.agent_id == envelope.agent_id
                and binding.tenant_id == envelope.tenant_id
                and binding.workflow_id == envelope.workflow_id
                and binding.binding_id == envelope.binding_id
                and binding.entity_id == envelope.entity_id
            ):
                return

        raise ValueError(
            "agent is not bound to proposal workflow/entity scope: "
            f"agent_id={envelope.agent_id}, "
            f"workflow_id={envelope.workflow_id}, "
            f"binding_id={envelope.binding_id}, "
            f"entity_id={envelope.entity_id}"
        )
