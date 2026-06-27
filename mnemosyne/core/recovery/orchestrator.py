from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEventType,
    CommitmentStatus,
    make_commitment_proposal_candidate,
    make_commitment_rejected_candidate,
)
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.policy import (
    RecoveryCheck,
    RecoveryContext,
    RecoveryPolicy,
    RecoveryProposal,
    check_recovery_allowed,
)


@dataclass(frozen=True)
class RecoveryOrchestrationResult:
    check: RecoveryCheck
    candidate: TransitionCandidate

    @property
    def allowed(self) -> bool:
        return self.check.ok


def orchestrate_recovery(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment: ActiveCommitment,
    context: RecoveryContext,
    proposal: RecoveryProposal,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
    rejection_evidence_extra: dict[str, Any] | None = None,
) -> RecoveryOrchestrationResult:
    """Turn a fired commitment recovery attempt into a CTL candidate.

    This function intentionally never returns a domain-state transition.
    It returns only a commitment-FSM transition:

    - commitment_proposal_emitted if policy allows the proposal
    - commitment_rejected if policy denies the proposal

    Domain mutation must happen later through the normal admission path.
    """
    check = check_recovery_allowed(
        commitment=commitment,
        context=context,
        proposal=proposal,
        policy=policy,
    )

    if check.ok:
        candidate = make_commitment_proposal_candidate(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            commitment_id=commitment.commitment_id,
            proposal_ref=proposal.proposal_ref,
            proposal_scope=proposal.proposal_scope,
            workflow_id=workflow_id,
            binding_id=binding_id,
            rid=rid,
            op_id=op_id,
            dependency_rid=dependency_rid,
        )
        return RecoveryOrchestrationResult(check=check, candidate=candidate)

    evidence = dict(check.evidence)
    if rejection_evidence_extra:
        evidence.update(rejection_evidence_extra)

    candidate = make_commitment_rejected_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment.commitment_id,
        rejection_code=check.decision.value,
        rejection_evidence=evidence,
        state_before=CommitmentStatus.FIRED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    # The action type check is defensive: denied recovery must be recorded as
    # rejected commitment recovery, not silently transformed into domain state.
    assert candidate.action_type == CommitmentEventType.REJECTED.value

    return RecoveryOrchestrationResult(check=check, candidate=candidate)
