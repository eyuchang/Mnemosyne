# File: mnemosyne/runtime/proposals.py
#
# Purpose:
#   R3 in-memory proposal lifecycle store.
#
# Design rule:
#   Proposal lifecycle state is runtime metadata.
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass, field

from mnemosyne.runtime.models import (
    RuntimeAdmissionDecision,
    RuntimeProposalEnvelope,
    RuntimeTraceEvent,
)
from mnemosyne.runtime.registry import RuntimeRegistry


@dataclass
class RuntimeProposalStore:
    proposals: dict[str, RuntimeProposalEnvelope] = field(default_factory=dict)
    decisions: dict[str, RuntimeAdmissionDecision] = field(default_factory=dict)
    decision_by_proposal_id: dict[str, str] = field(default_factory=dict)
    trace_events: list[RuntimeTraceEvent] = field(default_factory=list)

    def submit_proposal(
        self,
        envelope: RuntimeProposalEnvelope,
        *,
        registry: RuntimeRegistry,
    ) -> RuntimeProposalEnvelope:
        if envelope.proposal_id in self.proposals:
            raise ValueError(f"proposal already exists: {envelope.proposal_id}")

        workflow = registry.workflows.get_workflow(envelope.workflow_id)
        binding = registry.workflows.get_binding(envelope.binding_id)
        agent = registry.agents.get_agent(envelope.agent_id)

        if envelope.tenant_id != workflow.tenant_id:
            raise ValueError(
                f"proposal tenant_id does not match workflow tenant_id: "
                f"{envelope.tenant_id} != {workflow.tenant_id}"
            )

        if envelope.tenant_id != agent.tenant_id:
            raise ValueError(
                f"proposal tenant_id does not match agent tenant_id: "
                f"{envelope.tenant_id} != {agent.tenant_id}"
            )

        if envelope.workflow_id != binding.workflow_id:
            raise ValueError(
                f"proposal workflow_id does not match binding workflow_id: "
                f"{envelope.workflow_id} != {binding.workflow_id}"
            )

        if envelope.entity_id != binding.entity_id:
            raise ValueError(
                f"proposal entity_id does not match binding entity_id: "
                f"{envelope.entity_id} != {binding.entity_id}"
            )

        if envelope.app_id != workflow.app_id:
            raise ValueError(
                f"proposal app_id does not match workflow app_id: "
                f"{envelope.app_id} != {workflow.app_id}"
            )

        if envelope.schema_id != workflow.schema_id:
            raise ValueError(
                f"proposal schema_id does not match workflow schema_id: "
                f"{envelope.schema_id} != {workflow.schema_id}"
            )

        self.proposals[envelope.proposal_id] = envelope
        self.trace_events.append(
            RuntimeTraceEvent(
                event_id=f"trace:proposal-submitted:{envelope.proposal_id}",
                tenant_id=envelope.tenant_id,
                workflow_id=envelope.workflow_id,
                event_type="proposal_submitted",
                actor_id=envelope.agent_id,
                proposal_id=envelope.proposal_id,
                details={
                    "binding_id": envelope.binding_id,
                    "entity_id": envelope.entity_id,
                    "proposal_kind": envelope.proposal_kind,
                },
            )
        )

        return envelope

    def get_proposal(self, proposal_id: str) -> RuntimeProposalEnvelope:
        try:
            return self.proposals[proposal_id]
        except KeyError as exc:
            raise KeyError(f"unknown proposal_id: {proposal_id}") from exc

    def list_proposals_for_workflow(
        self,
        workflow_id: str,
    ) -> list[RuntimeProposalEnvelope]:
        return [
            proposal
            for proposal in self.proposals.values()
            if proposal.workflow_id == workflow_id
        ]

    def list_proposals_for_agent(
        self,
        agent_id: str,
    ) -> list[RuntimeProposalEnvelope]:
        return [
            proposal
            for proposal in self.proposals.values()
            if proposal.agent_id == agent_id
        ]

    def record_decision(
        self,
        decision: RuntimeAdmissionDecision,
    ) -> RuntimeAdmissionDecision:
        if decision.decision_id in self.decisions:
            raise ValueError(f"decision already exists: {decision.decision_id}")

        proposal = self.get_proposal(decision.proposal_id)

        if decision.proposal_id in self.decision_by_proposal_id:
            raise ValueError(
                f"proposal already has an admission decision: {decision.proposal_id}"
            )

        if decision.tenant_id != proposal.tenant_id:
            raise ValueError(
                f"decision tenant_id does not match proposal tenant_id: "
                f"{decision.tenant_id} != {proposal.tenant_id}"
            )

        if decision.workflow_id != proposal.workflow_id:
            raise ValueError(
                f"decision workflow_id does not match proposal workflow_id: "
                f"{decision.workflow_id} != {proposal.workflow_id}"
            )

        if decision.accepted and decision.error_codes:
            raise ValueError("accepted admission decision must not have error_codes")

        if not decision.accepted and decision.committed_rids:
            raise ValueError("rejected admission decision must not have committed_rids")

        self.decisions[decision.decision_id] = decision
        self.decision_by_proposal_id[decision.proposal_id] = decision.decision_id

        self.trace_events.append(
            RuntimeTraceEvent(
                event_id=f"trace:admission-decision:{decision.decision_id}",
                tenant_id=decision.tenant_id,
                workflow_id=decision.workflow_id,
                event_type="admission_accepted" if decision.accepted else "admission_rejected",
                actor_id="runtime:admission",
                proposal_id=decision.proposal_id,
                decision_id=decision.decision_id,
                details={
                    "accepted": decision.accepted,
                    "reason": decision.reason,
                    "error_codes": list(decision.error_codes),
                    "committed_rids": list(decision.committed_rids),
                },
            )
        )

        return decision

    def get_decision(self, decision_id: str) -> RuntimeAdmissionDecision:
        try:
            return self.decisions[decision_id]
        except KeyError as exc:
            raise KeyError(f"unknown decision_id: {decision_id}") from exc

    def get_decision_for_proposal(
        self,
        proposal_id: str,
    ) -> RuntimeAdmissionDecision | None:
        decision_id = self.decision_by_proposal_id.get(proposal_id)
        if decision_id is None:
            return None
        return self.decisions[decision_id]

    def list_trace_events(self) -> list[RuntimeTraceEvent]:
        return list(self.trace_events)
