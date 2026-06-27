from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from mnemosyne.benchmarks.jssp_recovery_proposals import JSSPRecoveryProposalBatch
from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult


@dataclass(frozen=True)
class JSSPSelectedRepairAdmission:
    selected_candidates: list[TransitionCandidate]
    batch: CommitBatch
    validation: ValidationResult | None
    records: list[CTLRecord]
    committed: list[CTLRecord]

    @property
    def ok(self) -> bool:
        return (
            self.validation is not None
            and self.validation.ok
            and len(self.committed) == len(self.selected_candidates)
        )

    @property
    def selected_rids(self) -> list[str]:
        return [candidate.rid for candidate in self.selected_candidates]

    @property
    def committed_rids(self) -> list[str]:
        return [record.rid for record in self.committed]

    @property
    def committed_entity_ids(self) -> list[str]:
        return [record.eid for record in self.committed]


def repair_candidates_from_proposal_batch(
    proposal_batch: JSSPRecoveryProposalBatch,
    *,
    operation_keys: list[str] | None = None,
) -> list[TransitionCandidate]:
    selected: list[TransitionCandidate] = []
    allowed = set(operation_keys or [])

    for proposal in proposal_batch.proposals:
        if operation_keys is not None and proposal.operation_key not in allowed:
            continue

        selected.extend(proposal.package.proposed_domain_candidates)

    return selected


def selected_repair_commit_batch(
    *,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    selected_candidates: list[TransitionCandidate],
    batch_id: str | None = None,
) -> CommitBatch:
    rebound_candidates = [
        replace(
            candidate,
            tenant_id=tenant_id,
            tx_group_id=tx_group_id,
            workflow_id=workflow_id,
        )
        for candidate in selected_candidates
    ]

    return CommitBatch(
        batch_id=batch_id or "batch:jssp:selected-repair-admission",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        tx_group_id=tx_group_id,
        candidates=rebound_candidates,
    )


async def admit_selected_repair_candidates(
    *,
    store: Any,
    validator: Any,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    selected_candidates: list[TransitionCandidate],
    batch_id: str | None = None,
) -> JSSPSelectedRepairAdmission:
    batch = selected_repair_commit_batch(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        selected_candidates=selected_candidates,
        batch_id=batch_id,
    )

    if not selected_candidates:
        return JSSPSelectedRepairAdmission(
            selected_candidates=[],
            batch=batch,
            validation=None,
            records=[],
            committed=[],
        )

    validation = await validator.validate_batch(batch, store)
    if not validation.ok:
        return JSSPSelectedRepairAdmission(
            selected_candidates=list(batch.candidates),
            batch=batch,
            validation=validation,
            records=[],
            committed=[],
        )

    records = await validator.records_from_batch(batch, store)
    committed = await store.commit_batch(batch, records)

    return JSSPSelectedRepairAdmission(
        selected_candidates=list(batch.candidates),
        batch=batch,
        validation=validation,
        records=records,
        committed=committed,
    )


async def admit_repair_candidates_from_proposal_batch(
    *,
    store: Any,
    validator: Any,
    tenant_id: str,
    tx_group_id: str,
    workflow_id: str,
    proposal_batch: JSSPRecoveryProposalBatch,
    operation_keys: list[str] | None = None,
    batch_id: str | None = None,
) -> JSSPSelectedRepairAdmission:
    selected = repair_candidates_from_proposal_batch(
        proposal_batch,
        operation_keys=operation_keys,
    )

    return await admit_selected_repair_candidates(
        store=store,
        validator=validator,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        workflow_id=workflow_id,
        selected_candidates=selected,
        batch_id=batch_id,
    )
