from __future__ import annotations

from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.packages import (
    RecoveryProposalPackage,
    proposal_package_contains_only_domain_candidates,
    proposal_package_from_dict,
    proposal_package_scope_is_within,
    proposal_package_to_dict,
)


def domain_candidate(rid: str = "rid:domain-repair") -> TransitionCandidate:
    return TransitionCandidate(
        rid=rid,
        op_id=rid,
        tenant_id="tenant:r47",
        tx_group_id="tx:r47",
        workflow_id="workflow:r47",
        binding_id=None,
        eid="domain:entity:1",
        fsm="domain.fsm",
        fsm_version="1.0",
        state_before="stale",
        state_after="repaired",
        action_type="domain_repair",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_repair", "repair": "refresh_stale_state"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.repair",
        schema_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id=None,
        validator_version=None,
    )


def commitment_candidate() -> TransitionCandidate:
    return TransitionCandidate(
        rid="rid:commitment-proposal",
        op_id="rid:commitment-proposal",
        tenant_id="tenant:r47",
        tx_group_id="tx:r47",
        workflow_id="workflow:r47",
        binding_id=None,
        eid="commitment:c1",
        fsm="mnemosyne.commitment",
        fsm_version="1.0",
        state_before="fired",
        state_after="proposed",
        action_type="commitment_proposal_emitted",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "mnemosyne.active_commitment_event"},
        app_id="mnemosyne",
        app_version="1.0",
        schema_id="mnemosyne.active_commitment_event",
        schema_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id=None,
        validator_version=None,
    )


def package() -> RecoveryProposalPackage:
    return RecoveryProposalPackage(
        package_id="pkg:c1:repair:1",
        commitment_id="c1",
        proposal_ref="proposal:repair:1",
        proposal_scope={"entity_id": "domain:entity:1"},
        proposed_domain_candidates=[domain_candidate()],
        rationale="Repair stale dependent entity.",
        validator_context={"source": "runtime"},
        created_from_record_id="rid:commitment-fire",
        created_by="r47.test",
    )


def test_recovery_proposal_package_is_inert_and_tracks_candidate_rids():
    pkg = package()

    assert pkg.is_inert
    assert pkg.candidate_rids == ["rid:domain-repair"]
    assert pkg.proposed_domain_candidates[0].fsm == "domain.fsm"


def test_recovery_proposal_package_converts_to_recovery_proposal():
    proposal = package().to_recovery_proposal()

    assert proposal.proposal_ref == "proposal:repair:1"
    assert proposal.proposal_scope == {"entity_id": "domain:entity:1"}
    assert proposal.rationale == "Repair stale dependent entity."


def test_recovery_proposal_package_round_trips_through_dict():
    pkg = package()

    restored = proposal_package_from_dict(proposal_package_to_dict(pkg))

    assert restored.package_id == pkg.package_id
    assert restored.commitment_id == pkg.commitment_id
    assert restored.proposal_ref == pkg.proposal_ref
    assert restored.proposal_scope == pkg.proposal_scope
    assert restored.rationale == pkg.rationale
    assert restored.validator_context == pkg.validator_context
    assert restored.created_from_record_id == "rid:commitment-fire"
    assert restored.created_by == "r47.test"
    assert restored.candidate_rids == ["rid:domain-repair"]
    assert restored.proposed_domain_candidates[0].state_after == "repaired"


def test_recovery_proposal_package_scope_must_be_within_dependency_scope():
    pkg = package()

    assert proposal_package_scope_is_within(
        pkg,
        {"entity_id": "domain:entity:1", "workflow_id": "workflow:r47"},
    )

    assert not proposal_package_scope_is_within(
        pkg,
        {"entity_id": "domain:outside"},
    )

    assert not proposal_package_scope_is_within(
        pkg,
        {},
    )


def test_recovery_proposal_package_contains_only_domain_candidates():
    assert proposal_package_contains_only_domain_candidates(package())

    bad_package = RecoveryProposalPackage(
        package_id="pkg:bad",
        commitment_id="c1",
        proposal_ref="proposal:bad",
        proposal_scope={"entity_id": "domain:entity:1"},
        proposed_domain_candidates=[commitment_candidate()],
    )

    assert not proposal_package_contains_only_domain_candidates(bad_package)
