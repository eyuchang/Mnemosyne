from __future__ import annotations

from dataclasses import replace

from mnemosyne.core.commitments import (
    CommitmentEvent,
    CommitmentEventType,
    event_to_extension,
    make_commitment_proposal_candidate,
)
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.packages import (
    RecoveryProposalPackage,
    proposal_package_contains_only_domain_candidates,
    proposal_package_event_payload,
    proposal_package_scope_is_within,
)


def make_package_proposal_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    package: RecoveryProposalPackage,
    dependency_scope: dict | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    state_before: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    """Create a commitment-FSM proposal candidate backed by a package reference.

    The package may contain proposed domain TransitionCandidates, but this
    builder records only a package reference in commitment memory. It does not
    admit or commit the domain candidates.
    """

    if not proposal_package_contains_only_domain_candidates(package):
        raise ValueError("proposal package must contain only domain candidates")

    if dependency_scope is not None and not proposal_package_scope_is_within(package, dependency_scope):
        raise ValueError("proposal package scope is outside commitment dependency scope")

    candidate = make_commitment_proposal_candidate(
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=package.commitment_id,
        proposal_ref=package.proposal_ref,
        proposal_scope=package.proposal_scope,
        workflow_id=workflow_id,
        binding_id=binding_id,
        state_before=state_before,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )

    event = CommitmentEvent(
        event_type=CommitmentEventType.PROPOSAL_EMITTED,
        commitment_id=package.commitment_id,
        payload=proposal_package_event_payload(package),
        record_id=candidate.rid,
        workflow_id=workflow_id,
    )

    metadata = dict(candidate.metadata)
    metadata.update(
        {
            "proposal_package_id": package.package_id,
            "proposal_candidate_rids": package.candidate_rids,
            "proposal_candidate_count": len(package.proposed_domain_candidates),
        }
    )

    return replace(
        candidate,
        extension=event_to_extension(event),
        metadata=metadata,
    )
