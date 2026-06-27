from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from mnemosyne.core.commitments import ActiveCommitment, CommitmentStatus
from mnemosyne.core.recovery.orchestrator import (
    RecoveryOrchestrationResult,
    orchestrate_recovery,
)
from mnemosyne.core.recovery.policy import (
    RecoveryContext,
    RecoveryDecision,
    RecoveryPolicy,
    RecoveryProposal,
)


@dataclass(frozen=True)
class RecoveryLoopResult:
    results: list[RecoveryOrchestrationResult]
    terminal_status: CommitmentStatus
    exhausted: bool

    @property
    def candidates(self):
        return [result.candidate for result in self.results]

    @property
    def allowed(self) -> bool:
        return any(result.allowed for result in self.results)


def run_bounded_recovery_loop(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment: ActiveCommitment,
    start_context: RecoveryContext,
    proposals: Iterable[RecoveryProposal],
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    dependency_rid: str | None = None,
    start_status: CommitmentStatus = CommitmentStatus.FIRED,
) -> RecoveryLoopResult:
    """Run bounded recovery attempts without mutating domain state.

    Each attempt emits exactly one commitment-FSM candidate:
    - PROPOSED when the proposal is allowed by policy
    - REJECTED when policy denies it

    Domain-state mutation remains outside this loop and must go through normal admission.
    """
    results: list[RecoveryOrchestrationResult] = []
    current_status = start_status

    for offset, proposal in enumerate(proposals):
        context = RecoveryContext(
            commitment_id=start_context.commitment_id,
            depth=start_context.depth,
            attempt_index=start_context.attempt_index + offset,
            triggering_record_id=start_context.triggering_record_id,
            triggering_error=start_context.triggering_error,
            history=[*start_context.history, proposal.proposal_ref],
        )

        result = orchestrate_recovery(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            commitment=commitment,
            context=context,
            proposal=proposal,
            policy=policy,
            workflow_id=workflow_id,
            binding_id=binding_id,
            dependency_rid=dependency_rid,
            commitment_state_before=current_status.value,
        )
        results.append(result)

        if result.allowed:
            return RecoveryLoopResult(
                results=results,
                terminal_status=CommitmentStatus.PROPOSED,
                exhausted=False,
            )

        current_status = CommitmentStatus.REJECTED

        if result.check.decision in {
            RecoveryDecision.DENY_ATTEMPTS_EXCEEDED,
            RecoveryDecision.DENY_DEPTH_EXCEEDED,
        }:
            return RecoveryLoopResult(
                results=results,
                terminal_status=CommitmentStatus.REJECTED,
                exhausted=True,
            )

    return RecoveryLoopResult(
        results=results,
        terminal_status=current_status,
        exhausted=True,
    )
