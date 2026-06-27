from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from mnemosyne.core.commitments import (
    ActiveCommitment,
    ActiveCommitmentIndex,
    CommitmentStatus,
    active_commitment_index_from_store,
    build_commitment_fsm_registry,
    make_commitment_admitted_candidate,
    make_commitment_rejected_candidate,
    make_discharge_commitment_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult
from mnemosyne.core.validation import Validator


@dataclass(frozen=True)
class CommitmentApiResult:
    """Result of a product-facing commitment API operation.

    The API commits only commitment-FSM records. It does not create or commit
    domain repair records.
    """

    batch: CommitBatch
    candidate: TransitionCandidate
    validation: ValidationResult
    records: list[CTLRecord]
    committed: list[CTLRecord]

    @property
    def ok(self) -> bool:
        return self.validation.ok and bool(self.committed)

    @property
    def committed_rids(self) -> list[str]:
        return [record.rid for record in self.committed]

    @property
    def committed_action_types(self) -> list[str]:
        return [record.action_type for record in self.committed]

    @property
    def committed_fsms(self) -> list[str]:
        return [record.fsm for record in self.committed]

    @property
    def committed_only_commitment_fsm(self) -> bool:
        return all(record.fsm == "mnemosyne.commitment" for record in self.committed)


def default_commitment_validator() -> Validator:
    """Build the default validator for commitment-FSM API calls."""

    return Validator(build_commitment_fsm_registry())


def _batch_id(prefix: str, candidate: TransitionCandidate) -> str:
    return f"{prefix}:{candidate.rid}:{uuid4().hex}"


async def commit_commitment_candidate(
    *,
    store: Any,
    candidate: TransitionCandidate,
    validator: Validator | None = None,
    batch_id: str | None = None,
) -> CommitmentApiResult:
    """Validate and commit one commitment-FSM candidate.

    This is the product-facing admission helper for active commitment records.
    It fails closed: if validation fails, nothing is committed.
    """

    validator = validator or default_commitment_validator()

    batch = CommitBatch(
        batch_id=batch_id or _batch_id("batch:commitment-api", candidate),
        tenant_id=candidate.tenant_id,
        workflow_id=candidate.workflow_id,
        tx_group_id=candidate.tx_group_id,
        candidates=[candidate],
    )

    validation = await validator.validate_batch(batch, store)
    if not validation.ok:
        return CommitmentApiResult(
            batch=batch,
            candidate=candidate,
            validation=validation,
            records=[],
            committed=[],
        )

    records = await validator.records_from_batch(batch, store)
    committed = await store.commit_batch(batch, records)

    return CommitmentApiResult(
        batch=batch,
        candidate=candidate,
        validation=validation,
        records=records,
        committed=committed,
    )


async def register_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment: ActiveCommitment,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    validator: Validator | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
) -> CommitmentApiResult:
    candidate = make_register_commitment_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment=commitment,
        workflow_id=workflow_id,
        binding_id=binding_id,
        rid=rid,
        op_id=op_id,
    )

    return await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator,
        batch_id=batch_id,
    )


async def fire_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    reason: str = "trigger_true",
    validator: Validator | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> CommitmentApiResult:
    candidate = make_fire_commitment_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment_id,
        workflow_id=workflow_id,
        binding_id=binding_id,
        reason=reason,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    return await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator,
        batch_id=batch_id,
    )


async def discharge_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    reason: str = "obligation_satisfied",
    validator: Validator | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> CommitmentApiResult:
    candidate = make_discharge_commitment_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment_id,
        workflow_id=workflow_id,
        binding_id=binding_id,
        reason=reason,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    return await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator,
        batch_id=batch_id,
    )


async def admit_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    admitted_record_ids: list[str],
    workflow_id: str | None = None,
    binding_id: str | None = None,
    validator: Validator | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> CommitmentApiResult:
    candidate = make_commitment_admitted_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment_id,
        admitted_record_ids=admitted_record_ids,
        workflow_id=workflow_id,
        binding_id=binding_id,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    return await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator,
        batch_id=batch_id,
    )


async def reject_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    rejection_code: str,
    rejection_evidence: dict | None = None,
    state_before: str | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    validator: Validator | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> CommitmentApiResult:
    candidate = make_commitment_rejected_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment_id,
        rejection_code=rejection_code,
        rejection_evidence=rejection_evidence,
        state_before=state_before,
        workflow_id=workflow_id,
        binding_id=binding_id,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    return await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator,
        batch_id=batch_id,
    )


async def load_active_commitments(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
) -> ActiveCommitmentIndex:
    return await active_commitment_index_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )


async def get_active_commitment_status(
    *,
    store: Any,
    tenant_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
) -> CommitmentStatus | None:
    index = await load_active_commitments(
        store=store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    return index.status(commitment_id)


async def list_live_active_commitments(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
) -> list[ActiveCommitment]:
    index = await load_active_commitments(
        store=store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )

    commitments: list[ActiveCommitment] = []
    for commitment_id in index.live_commitment_ids():
        commitment = index.get(commitment_id)
        if commitment is not None:
            commitments.append(commitment)

    return commitments


async def list_live_active_commitment_ids(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
) -> list[str]:
    index = await load_active_commitments(
        store=store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    return index.live_commitment_ids()
