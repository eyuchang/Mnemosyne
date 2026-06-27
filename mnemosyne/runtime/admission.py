# File: mnemosyne/runtime/admission.py
#
# Purpose:
#   R3 runtime admission facade.
#
# Design rule:
#   The facade records admission decisions for already-submitted proposals.
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.runtime.models import RuntimeAdmissionDecision
from mnemosyne.runtime.proposals import RuntimeProposalStore


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _as_tuple(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


@dataclass
class RuntimeAdmissionFacade:
    """Admission facade for R3 runtime proposals.

    The proposal store owns proposal lifecycle metadata.
    The correctness kernel still owns committed truth.
    """

    proposal_store: RuntimeProposalStore

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
        _require_nonempty(proposal_id, "proposal_id")
        _require_nonempty(reason, "reason")

        codes = _as_tuple(error_codes)
        if not codes:
            raise ValueError("rejected proposal must include at least one error_code")

        proposal = self.proposal_store.get_proposal(proposal_id)

        decision = RuntimeAdmissionDecision(
            decision_id=decision_id or f"decision:reject:{proposal_id}",
            proposal_id=proposal.proposal_id,
            tenant_id=proposal.tenant_id,
            workflow_id=proposal.workflow_id,
            accepted=False,
            reason=reason,
            error_codes=codes,
            committed_rids=(),
            audit_ref=audit_ref,
            metadata=metadata or {},
        )

        return self.proposal_store.record_decision(decision)

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
        _require_nonempty(proposal_id, "proposal_id")
        _require_nonempty(reason, "reason")

        rids = _as_tuple(committed_rids)
        if not rids:
            raise ValueError("accepted proposal must include at least one committed rid")

        proposal = self.proposal_store.get_proposal(proposal_id)

        decision = RuntimeAdmissionDecision(
            decision_id=decision_id or f"decision:accept:{proposal_id}",
            proposal_id=proposal.proposal_id,
            tenant_id=proposal.tenant_id,
            workflow_id=proposal.workflow_id,
            accepted=True,
            reason=reason,
            error_codes=(),
            committed_rids=rids,
            audit_ref=audit_ref,
            metadata=metadata or {},
        )

        return self.proposal_store.record_decision(decision)

    def get_decision_for_proposal(
        self,
        proposal_id: str,
    ) -> RuntimeAdmissionDecision | None:
        _require_nonempty(proposal_id, "proposal_id")
        return self.proposal_store.get_decision_for_proposal(proposal_id)
