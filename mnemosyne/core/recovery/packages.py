from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.policy import RecoveryProposal


@dataclass(frozen=True)
class RecoveryProposalPackage:
    """Inert package describing a proposed recovery.

    A proposal package may contain proposed domain TransitionCandidates, but it
    does not commit them. Domain state can change only if those candidates are
    later admitted through the normal CTL admission path.
    """

    package_id: str
    commitment_id: str
    proposal_ref: str
    proposal_scope: dict[str, Any]
    proposed_domain_candidates: list[TransitionCandidate] = field(default_factory=list)
    rationale: str | None = None
    validator_context: dict[str, Any] = field(default_factory=dict)
    created_from_record_id: str | None = None
    created_by: str | None = None

    @property
    def candidate_rids(self) -> list[str]:
        return [candidate.rid for candidate in self.proposed_domain_candidates]

    @property
    def is_inert(self) -> bool:
        """Packages are descriptions only; they do not imply CTL admission."""
        return True

    def to_recovery_proposal(self) -> RecoveryProposal:
        return RecoveryProposal(
            proposal_ref=self.proposal_ref,
            proposal_scope=dict(self.proposal_scope),
            rationale=self.rationale,
        )


def transition_candidate_to_dict(candidate: TransitionCandidate) -> dict[str, Any]:
    return asdict(candidate)


def transition_candidate_from_dict(data: dict[str, Any]) -> TransitionCandidate:
    valid_fields = {field.name for field in fields(TransitionCandidate)}
    filtered = {key: value for key, value in data.items() if key in valid_fields}
    return TransitionCandidate(**filtered)


def proposal_package_to_dict(package: RecoveryProposalPackage) -> dict[str, Any]:
    return {
        "package_id": package.package_id,
        "commitment_id": package.commitment_id,
        "proposal_ref": package.proposal_ref,
        "proposal_scope": dict(package.proposal_scope),
        "proposed_domain_candidates": [
            transition_candidate_to_dict(candidate)
            for candidate in package.proposed_domain_candidates
        ],
        "rationale": package.rationale,
        "validator_context": dict(package.validator_context),
        "created_from_record_id": package.created_from_record_id,
        "created_by": package.created_by,
    }


def proposal_package_from_dict(data: dict[str, Any]) -> RecoveryProposalPackage:
    return RecoveryProposalPackage(
        package_id=data["package_id"],
        commitment_id=data["commitment_id"],
        proposal_ref=data["proposal_ref"],
        proposal_scope=dict(data.get("proposal_scope", {})),
        proposed_domain_candidates=[
            transition_candidate_from_dict(candidate)
            for candidate in data.get("proposed_domain_candidates", [])
        ],
        rationale=data.get("rationale"),
        validator_context=dict(data.get("validator_context", {})),
        created_from_record_id=data.get("created_from_record_id"),
        created_by=data.get("created_by"),
    )


def proposal_package_scope_is_within(
    package: RecoveryProposalPackage,
    dependency_scope: dict[str, Any],
) -> bool:
    """Return true if every proposed scope key is allowed by dependency_scope."""

    for key, value in package.proposal_scope.items():
        if key not in dependency_scope:
            return False
        if dependency_scope[key] != value:
            return False
    return True


def proposal_package_contains_only_domain_candidates(
    package: RecoveryProposalPackage,
    *,
    commitment_fsm: str = "mnemosyne.commitment",
) -> bool:
    """Packages should carry domain repair candidates, not commitment FSM records."""

    return all(candidate.fsm != commitment_fsm for candidate in package.proposed_domain_candidates)


PROPOSAL_PACKAGE_PAYLOAD_KEY = "proposal_package"


def proposal_package_reference_to_dict(package: RecoveryProposalPackage) -> dict[str, Any]:
    """Return the commitment-event-safe reference to a proposal package.

    This intentionally includes candidate RIDs, not full domain candidate objects.
    The commitment event records that a package was proposed; it does not admit
    the package's domain candidates.
    """

    return {
        "package_id": package.package_id,
        "commitment_id": package.commitment_id,
        "proposal_ref": package.proposal_ref,
        "proposal_scope": dict(package.proposal_scope),
        "candidate_rids": package.candidate_rids,
        "candidate_count": len(package.proposed_domain_candidates),
        "rationale": package.rationale,
        "created_from_record_id": package.created_from_record_id,
        "created_by": package.created_by,
    }


def proposal_package_reference_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a package reference recovered from a commitment event payload."""

    return {
        "package_id": data["package_id"],
        "commitment_id": data["commitment_id"],
        "proposal_ref": data["proposal_ref"],
        "proposal_scope": dict(data.get("proposal_scope", {})),
        "candidate_rids": list(data.get("candidate_rids", [])),
        "candidate_count": int(data.get("candidate_count", len(data.get("candidate_rids", [])))),
        "rationale": data.get("rationale"),
        "created_from_record_id": data.get("created_from_record_id"),
        "created_by": data.get("created_by"),
    }


def proposal_package_event_payload(package: RecoveryProposalPackage) -> dict[str, Any]:
    """Payload for a commitment_proposal_emitted event backed by a package."""

    return {
        "proposal_ref": package.proposal_ref,
        "proposal_scope": dict(package.proposal_scope),
        "rationale": package.rationale,
        PROPOSAL_PACKAGE_PAYLOAD_KEY: proposal_package_reference_to_dict(package),
    }


def proposal_package_reference_from_event_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a proposal-package reference from a commitment event payload."""

    raw = payload.get(PROPOSAL_PACKAGE_PAYLOAD_KEY)
    if raw is None:
        return None
    return proposal_package_reference_from_dict(raw)
