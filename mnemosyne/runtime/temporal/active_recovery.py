# File: mnemosyne/runtime/temporal/active_recovery.py
#
# Purpose:
#   Define a Temporal-style activity boundary for active recovery.
#
# Contract:
#   Temporal workflow/runtime code orchestrates only.
#   Active recovery planning, validation, and CTL commit happen through this
#   activity-like boundary.
#
# Source-of-truth rule:
#   CTL/store remains truth. Temporal remains orchestration.

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    active_commitment_index_from_store,
)
from mnemosyne.core.recovery import RecoveryContext, RecoveryPolicy, RecoveryProposal
from mnemosyne.runtime.local import LocalActiveRecoveryExecutor

TemporalRecoveryProposalProvider = Callable[
    [ActiveCommitment, RecoveryContext],
    Iterable[RecoveryProposal],
]


@dataclass(frozen=True)
class ActiveRecoveryActivityResult:
    """Result returned by the Temporal active recovery activity boundary.

    The activity may commit commitment-FSM recovery records. It must not commit
    domain repair records directly.
    """

    batch_id: str
    tenant_id: str
    workflow_id: str | None
    committed_rids: list[str]
    committed_fsms: list[str]
    committed_action_types: list[str]
    validation_ok: list[bool]
    skipped: dict[str, str] = field(default_factory=dict)
    commitment_statuses: dict[str, str] = field(default_factory=dict)

    @property
    def has_committed_records(self) -> bool:
        return bool(self.committed_rids)

    @property
    def committed_only_commitment_fsm(self) -> bool:
        return all(fsm == "mnemosyne.commitment" for fsm in self.committed_fsms)


async def plan_validate_and_commit_active_recovery_activity(
    *,
    tenant_id: str,
    tx_group_id: str,
    batch_id: str,
    store: Any,
    validator: Any,
    proposal_provider: TemporalRecoveryProposalProvider,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    contexts: dict[str, RecoveryContext] | None = None,
) -> ActiveRecoveryActivityResult:
    """Plan, validate, and commit active recovery through an activity boundary.

    This function is intentionally Temporal-SDK-free. A future temporalio
    activity can call this boundary from inside a real Temporal activity.

    Behavior:
        1. Load active commitments from CTL/store.
        2. Plan bounded recovery for fired/rejected commitments.
        3. Validate commitment-FSM recovery candidates.
        4. Commit admitted commitment-FSM records.
        5. Return deterministic summary data to workflow orchestration.

    Important:
        Domain repair candidates must not be committed here. Domain repair still
        requires a separate domain CTL admission path.
    """

    executor = LocalActiveRecoveryExecutor(store)

    execution = await executor.plan_validate_and_commit(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        batch_id=batch_id,
        proposal_provider=proposal_provider,
        policy=policy,
        workflow_id=workflow_id,
        binding_id=binding_id,
        contexts=contexts,
        validator=validator,
    )

    index = await active_commitment_index_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )

    commitment_statuses: dict[str, str] = {}
    for commitment_id in index.live_commitment_ids():
        status = index.status(commitment_id)
        if isinstance(status, CommitmentStatus):
            commitment_statuses[commitment_id] = status.value

    return ActiveRecoveryActivityResult(
        batch_id=batch_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        committed_rids=[record.rid for record in execution.committed],
        committed_fsms=[record.fsm for record in execution.committed],
        committed_action_types=[record.action_type for record in execution.committed],
        validation_ok=[result.ok for result in execution.validation_results],
        skipped=dict(execution.plan.skipped),
        commitment_statuses=commitment_statuses,
    )
