from __future__ import annotations

from mnemosyne.core.commitments import (
    CommitmentEvent,
    CommitmentEventType,
    event_from_extension,
    event_to_extension,
)
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery.packages import (
    PROPOSAL_PACKAGE_PAYLOAD_KEY,
    RecoveryProposalPackage,
    proposal_package_event_payload,
    proposal_package_reference_from_event_payload,
    proposal_package_reference_to_dict,
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
        extension={"kind": "domain_repair"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.repair",
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
        proposed_domain_candidates=[
            domain_candidate("rid:domain-repair:1"),
            domain_candidate("rid:domain-repair:2"),
        ],
        rationale="Repair stale dependent entity.",
        validator_context={"source": "runtime"},
        created_from_record_id="rid:commitment-fire",
        created_by="r47.test",
    )


def test_proposal_package_reference_contains_rids_not_domain_candidates():
    ref = proposal_package_reference_to_dict(package())

    assert ref["package_id"] == "pkg:c1:repair:1"
    assert ref["commitment_id"] == "c1"
    assert ref["proposal_ref"] == "proposal:repair:1"
    assert ref["candidate_rids"] == ["rid:domain-repair:1", "rid:domain-repair:2"]
    assert ref["candidate_count"] == 2

    # The commitment event stores a reference, not the full domain candidates.
    assert "proposed_domain_candidates" not in ref


def test_proposal_package_event_payload_embeds_package_reference():
    payload = proposal_package_event_payload(package())

    assert payload["proposal_ref"] == "proposal:repair:1"
    assert payload["proposal_scope"] == {"entity_id": "domain:entity:1"}
    assert payload["rationale"] == "Repair stale dependent entity."
    assert payload[PROPOSAL_PACKAGE_PAYLOAD_KEY]["package_id"] == "pkg:c1:repair:1"
    assert payload[PROPOSAL_PACKAGE_PAYLOAD_KEY]["candidate_rids"] == [
        "rid:domain-repair:1",
        "rid:domain-repair:2",
    ]


def test_proposal_package_reference_round_trips_through_commitment_event_extension():
    event = CommitmentEvent(
        event_type=CommitmentEventType.PROPOSAL_EMITTED,
        commitment_id="c1",
        payload=proposal_package_event_payload(package()),
        record_id="rid:commitment-proposal",
        workflow_id="workflow:r47",
    )

    extension = event_to_extension(event)
    restored = event_from_extension(extension)

    ref = proposal_package_reference_from_event_payload(restored.payload)

    assert restored.event_type == CommitmentEventType.PROPOSAL_EMITTED
    assert restored.commitment_id == "c1"
    assert restored.payload["proposal_ref"] == "proposal:repair:1"
    assert ref is not None
    assert ref["package_id"] == "pkg:c1:repair:1"
    assert ref["candidate_rids"] == ["rid:domain-repair:1", "rid:domain-repair:2"]
    assert ref["created_from_record_id"] == "rid:commitment-fire"


def test_commitment_event_payload_does_not_admit_domain_candidate_truth():
    event = CommitmentEvent(
        event_type=CommitmentEventType.PROPOSAL_EMITTED,
        commitment_id="c1",
        payload=proposal_package_event_payload(package()),
        record_id="rid:commitment-proposal",
        workflow_id="workflow:r47",
    )

    extension = event_to_extension(event)
    restored = event_from_extension(extension)

    ref = proposal_package_reference_from_event_payload(restored.payload)

    assert ref is not None
    assert ref["candidate_count"] == 2

    # Only the reference is in commitment memory. The domain candidates remain
    # inert proposal material until separately admitted as domain CTL records.
    assert "proposed_domain_candidates" not in ref
    assert restored.event_type == CommitmentEventType.PROPOSAL_EMITTED
