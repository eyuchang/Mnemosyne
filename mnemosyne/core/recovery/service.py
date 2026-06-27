from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from mnemosyne.core.commitments import (
    ActiveCommitment,
    ActiveCommitmentIndex,
    CommitmentStatus,
    active_commitment_index_from_store,
)
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.loop import RecoveryLoopResult, run_bounded_recovery_loop
from mnemosyne.core.recovery.policy import RecoveryContext, RecoveryPolicy, RecoveryProposal

ProposalProvider = Callable[[ActiveCommitment, RecoveryContext], Iterable[RecoveryProposal]]


@dataclass(frozen=True)
class ActiveRecoveryPlan:
    """Non-mutating recovery plan.

    The candidates returned here are commitment-FSM candidates only.
    They are not domain-state mutations.
    """

    candidates: list[TransitionCandidate]
    loop_results: dict[str, RecoveryLoopResult] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def has_candidates(self) -> bool:
        return bool(self.candidates)


def plan_recovery_from_index(
    *,
    tenant_id: str,
    tx_group_id: str,
    index: ActiveCommitmentIndex,
    proposal_provider: ProposalProvider,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    contexts: dict[str, RecoveryContext] | None = None,
) -> ActiveRecoveryPlan:
    candidates: list[TransitionCandidate] = []
    loop_results: dict[str, RecoveryLoopResult] = {}
    skipped: dict[str, str] = {}

    for commitment_id in index.live_commitment_ids():
        commitment = index.get(commitment_id)
        status = index.status(commitment_id)

        if commitment is None or status is None:
            skipped[commitment_id] = "missing_commitment"
            continue

        if status not in {CommitmentStatus.FIRED, CommitmentStatus.REJECTED}:
            skipped[commitment_id] = f"status_{status.value}_not_recoverable"
            continue

        context = (
            contexts.get(commitment_id)
            if contexts and commitment_id in contexts
            else RecoveryContext(commitment_id=commitment_id)
        )

        proposals = list(proposal_provider(commitment, context))
        if not proposals:
            skipped[commitment_id] = "no_recovery_proposals"
            continue

        loop_result = run_bounded_recovery_loop(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            commitment=commitment,
            start_context=context,
            proposals=proposals,
            policy=policy,
            workflow_id=workflow_id,
            binding_id=binding_id,
            start_status=status,
        )

        candidates.extend(loop_result.candidates)
        loop_results[commitment_id] = loop_result

    return ActiveRecoveryPlan(
        candidates=candidates,
        loop_results=loop_results,
        skipped=skipped,
    )


async def plan_recovery_from_store(
    store,
    *,
    tenant_id: str,
    tx_group_id: str,
    proposal_provider: ProposalProvider,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    contexts: dict[str, RecoveryContext] | None = None,
) -> ActiveRecoveryPlan:
    index = await active_commitment_index_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )

    return plan_recovery_from_index(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        index=index,
        proposal_provider=proposal_provider,
        policy=policy,
        workflow_id=workflow_id,
        binding_id=binding_id,
        contexts=contexts,
    )
