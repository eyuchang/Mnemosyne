from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from mnemosyne.api.commitments import CommitmentApiResult, commit_commitment_candidate, default_commitment_validator
from mnemosyne.core.commitments import ActiveCommitment
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery import (
    RecoveryProposalPackage,
    make_package_proposal_candidate,
    proposal_package_contains_only_domain_candidates,
    proposal_package_event_payload,
    proposal_package_from_dict,
    proposal_package_reference_from_event_payload,
    proposal_package_reference_to_dict,
    proposal_package_scope_is_within,
    proposal_package_to_dict,
)


@dataclass(frozen=True)
class ProposalPackageApiResult:
    package: RecoveryProposalPackage
    candidate: TransitionCandidate
    commitment_result: CommitmentApiResult

    @property
    def ok(self) -> bool:
        return self.commitment_result.ok

    @property
    def committed_rids(self) -> list[str]:
        return self.commitment_result.committed_rids

    @property
    def committed_action_types(self) -> list[str]:
        return self.commitment_result.committed_action_types

    @property
    def committed_only_commitment_fsm(self) -> bool:
        return self.commitment_result.committed_only_commitment_fsm


def create_recovery_proposal_package(
    *,
    package_id: str | None = None,
    commitment_id: str,
    proposal_ref: str,
    proposal_scope: dict[str, Any],
    proposed_domain_candidates: list[TransitionCandidate] | None = None,
    rationale: str | None = None,
    validator_context: dict[str, Any] | None = None,
    created_from_record_id: str | None = None,
    created_by: str | None = None,
) -> RecoveryProposalPackage:
    """Create an inert recovery proposal package.

    The package may carry proposed domain candidates, but creating a package
    does not commit those candidates.
    """

    return RecoveryProposalPackage(
        package_id=package_id or f"pkg:{commitment_id}:{uuid4().hex}",
        commitment_id=commitment_id,
        proposal_ref=proposal_ref,
        proposal_scope=dict(proposal_scope),
        proposed_domain_candidates=list(proposed_domain_candidates or []),
        rationale=rationale,
        validator_context=dict(validator_context or {}),
        created_from_record_id=created_from_record_id,
        created_by=created_by,
    )


def validate_recovery_proposal_package(
    *,
    package: RecoveryProposalPackage,
    dependency_scope: dict[str, Any] | None = None,
) -> None:
    """Fail closed if a proposal package violates product API boundaries."""

    if not proposal_package_contains_only_domain_candidates(package):
        raise ValueError("proposal package must contain only domain candidates")

    if dependency_scope is not None and not proposal_package_scope_is_within(package, dependency_scope):
        raise ValueError("proposal package scope is outside commitment dependency scope")


def package_to_reference(package: RecoveryProposalPackage) -> dict[str, Any]:
    return proposal_package_reference_to_dict(package)


def package_to_dict(package: RecoveryProposalPackage) -> dict[str, Any]:
    return proposal_package_to_dict(package)


def package_from_dict(data: dict[str, Any]) -> RecoveryProposalPackage:
    return proposal_package_from_dict(data)


def package_event_payload(package: RecoveryProposalPackage) -> dict[str, Any]:
    return proposal_package_event_payload(package)


def package_reference_from_event_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    return proposal_package_reference_from_event_payload(payload)


def make_package_backed_proposal_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    package: RecoveryProposalPackage,
    commitment: ActiveCommitment | None = None,
    dependency_scope: dict[str, Any] | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    state_before: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    """Create a package-backed commitment proposal candidate.

    The returned candidate is a commitment-FSM candidate only. The package's
    proposed domain candidates remain inert until separately admitted.
    """

    effective_scope = dependency_scope
    if commitment is not None:
        effective_scope = commitment.dependency_scope

    return make_package_proposal_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        package=package,
        dependency_scope=effective_scope,
        workflow_id=workflow_id,
        binding_id=binding_id,
        state_before=state_before,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )


async def emit_package_backed_proposal(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    package: RecoveryProposalPackage,
    commitment: ActiveCommitment | None = None,
    dependency_scope: dict[str, Any] | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    state_before: str | None = None,
    validator: Any | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> ProposalPackageApiResult:
    """Emit and admit a package-backed commitment proposal record.

    This commits only the commitment-FSM proposal record. It does not commit the
    package's domain candidates.
    """

    candidate = make_package_backed_proposal_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        package=package,
        commitment=commitment,
        dependency_scope=dependency_scope,
        workflow_id=workflow_id,
        binding_id=binding_id,
        state_before=state_before,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    result = await commit_commitment_candidate(
        store=store,
        candidate=candidate,
        validator=validator or default_commitment_validator(),
        batch_id=batch_id,
    )

    return ProposalPackageApiResult(
        package=package,
        candidate=candidate,
        commitment_result=result,
    )
