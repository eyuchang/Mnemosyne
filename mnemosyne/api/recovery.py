from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.api.commitments import default_commitment_validator
from mnemosyne.core.models import CTLRecord, ValidationResult
from mnemosyne.core.recovery import (
    ActiveRecoveryPlan,
    ProposalProvider,
    RecoveryContext,
    RecoveryPolicy,
)
from mnemosyne.runtime.local import LocalActiveRecoveryExecution, LocalActiveRecoveryExecutor


@dataclass(frozen=True)
class RecoveryApiExecution:
    """Product-facing active recovery execution result.

    The API commits only commitment-FSM recovery records. It does not create or
    commit domain repair records directly.
    """

    execution: LocalActiveRecoveryExecution

    @property
    def plan(self) -> ActiveRecoveryPlan:
        return self.execution.plan

    @property
    def records(self) -> list[CTLRecord]:
        return self.execution.records

    @property
    def committed(self) -> list[CTLRecord]:
        return self.execution.committed

    @property
    def validation_results(self) -> list[ValidationResult]:
        return self.execution.validation_results

    @property
    def has_committed_records(self) -> bool:
        return bool(self.execution.committed)

    @property
    def committed_rids(self) -> list[str]:
        return [record.rid for record in self.execution.committed]

    @property
    def committed_fsms(self) -> list[str]:
        return [record.fsm for record in self.execution.committed]

    @property
    def committed_action_types(self) -> list[str]:
        return [record.action_type for record in self.execution.committed]

    @property
    def committed_only_commitment_fsm(self) -> bool:
        return all(record.fsm == "mnemosyne.commitment" for record in self.execution.committed)

    @property
    def validation_ok(self) -> list[bool]:
        return [result.ok for result in self.execution.validation_results]

    @property
    def skipped(self) -> dict[str, str]:
        return dict(self.execution.plan.skipped)


async def plan_active_recovery(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    proposal_provider: ProposalProvider,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    contexts: dict[str, RecoveryContext] | None = None,
) -> ActiveRecoveryPlan:
    """Plan active recovery from CTL-derived commitment memory.

    This function is non-mutating. It returns commitment-FSM candidates only.
    """

    executor = LocalActiveRecoveryExecutor(store)
    return await executor.plan(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        proposal_provider=proposal_provider,
        policy=policy,
        workflow_id=workflow_id,
        binding_id=binding_id,
        contexts=contexts,
    )


async def validate_and_commit_active_recovery(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    batch_id: str,
    proposal_provider: ProposalProvider,
    validator: Any | None = None,
    policy: RecoveryPolicy | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    contexts: dict[str, RecoveryContext] | None = None,
) -> RecoveryApiExecution:
    """Plan, validate, and commit active recovery through the product API.

    The execution path commits only commitment-FSM records. Domain repair still
    requires a separate domain CTL admission path.
    """

    executor = LocalActiveRecoveryExecutor(store)
    execution = await executor.plan_validate_and_commit(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        batch_id=batch_id,
        proposal_provider=proposal_provider,
        validator=validator or default_commitment_validator(),
        policy=policy,
        workflow_id=workflow_id,
        binding_id=binding_id,
        contexts=contexts,
    )

    return RecoveryApiExecution(execution=execution)
