from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, now_utc
from mnemosyne.core.recovery import (
    ActiveRecoveryPlan,
    ProposalProvider,
    RecoveryContext,
    RecoveryPolicy,
    plan_recovery_from_store,
)


@dataclass(frozen=True)
class LocalActiveRecoveryExecution:
    """Result of executing local active recovery.

    This execution commits only commitment-FSM recovery records. It does not
    create or commit domain repair records.
    """

    plan: ActiveRecoveryPlan
    records: list[CTLRecord]
    committed: list[CTLRecord]

    @property
    def has_committed_records(self) -> bool:
        return bool(self.committed)


def ctl_record_from_transition_candidate(
    candidate: TransitionCandidate,
    *,
    version: int,
) -> CTLRecord:
    return CTLRecord(
        rid=candidate.rid,
        op_id=candidate.op_id or candidate.rid,
        tenant_id=candidate.tenant_id,
        tx_group_id=candidate.tx_group_id,
        workflow_id=candidate.workflow_id,
        binding_id=candidate.binding_id,
        eid=candidate.eid,
        fsm=candidate.fsm,
        version=version,
        state_before=candidate.state_before,
        state_after=candidate.state_after,
        action_type=candidate.action_type,
        triggers=list(candidate.triggers),
        dependencies=list(candidate.dependencies),
        metadata=dict(candidate.metadata),
        extension=dict(candidate.extension),
        app_id=candidate.app_id,
        app_version=candidate.app_version,
        schema_id=candidate.schema_id,
        schema_version=candidate.schema_version,
        fsm_version=candidate.fsm_version,
        policy_id=candidate.policy_id,
        policy_version=candidate.policy_version,
        validator_id=candidate.validator_id,
        validator_version=candidate.validator_version,
        timestamp=now_utc(),
    )


class LocalActiveRecoveryExecutor:
    """Local runtime wrapper for R4.5 active recovery.

    The executor is intentionally narrow:
    - it plans recovery from CTL-derived active commitments;
    - it commits only commitment-FSM records;
    - it never mutates domain state directly.
    """

    def __init__(self, store: Any) -> None:
        self.store = store

    async def plan(
        self,
        *,
        tenant_id: str,
        tx_group_id: str,
        proposal_provider: ProposalProvider,
        policy: RecoveryPolicy | None = None,
        workflow_id: str | None = None,
        binding_id: str | None = None,
        contexts: dict[str, RecoveryContext] | None = None,
    ) -> ActiveRecoveryPlan:
        return await plan_recovery_from_store(
            self.store,
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            proposal_provider=proposal_provider,
            policy=policy,
            workflow_id=workflow_id,
            binding_id=binding_id,
            contexts=contexts,
        )

    async def plan_and_commit(
        self,
        *,
        tenant_id: str,
        tx_group_id: str,
        batch_id: str,
        proposal_provider: ProposalProvider,
        policy: RecoveryPolicy | None = None,
        workflow_id: str | None = None,
        binding_id: str | None = None,
        contexts: dict[str, RecoveryContext] | None = None,
    ) -> LocalActiveRecoveryExecution:
        plan = await self.plan(
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            proposal_provider=proposal_provider,
            policy=policy,
            workflow_id=workflow_id,
            binding_id=binding_id,
            contexts=contexts,
        )

        if not plan.candidates:
            return LocalActiveRecoveryExecution(plan=plan, records=[], committed=[])

        records = await self._records_from_candidates(plan.candidates)

        batch = CommitBatch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            tx_group_id=tx_group_id,
            candidates=plan.candidates,
        )

        committed = await self.store.commit_batch(batch, records)

        return LocalActiveRecoveryExecution(
            plan=plan,
            records=records,
            committed=committed,
        )

    async def _records_from_candidates(
        self,
        candidates: list[TransitionCandidate],
    ) -> list[CTLRecord]:
        latest_by_key: dict[tuple[str, str], int] = {}
        records: list[CTLRecord] = []

        for candidate in candidates:
            key = (candidate.eid, candidate.fsm)

            if key not in latest_by_key:
                latest_by_key[key] = await self.store.get_latest_version(
                    candidate.tenant_id,
                    candidate.eid,
                    candidate.fsm,
                )

            latest_by_key[key] += 1

            records.append(
                ctl_record_from_transition_candidate(
                    candidate,
                    version=latest_by_key[key],
                )
            )

        return records
