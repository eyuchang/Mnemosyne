from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEventType,
    CommitmentStatus,
    event_from_extension,
    make_commitment_admitted_candidate,
    make_commitment_proposal_candidate,
    make_commitment_rejected_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
    replay_commitments,
)


def test_commitment_proposal_candidate_does_not_mutate_domain_entity():
    candidate = make_commitment_proposal_candidate(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment_id="c1",
        proposal_ref="proposal:repair:1",
        proposal_scope={"entity_id": "domain:entity:1"},
        workflow_id="workflow:1",
        rid="rid:proposal",
    )

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_proposal_emitted"
    assert candidate.state_before == CommitmentStatus.FIRED.value
    assert candidate.state_after == CommitmentStatus.PROPOSED.value

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.PROPOSAL_EMITTED
    assert event.payload["proposal_ref"] == "proposal:repair:1"
    assert event.payload["proposal_scope"] == {"entity_id": "domain:entity:1"}


def test_rejected_commitment_proposal_remains_live_for_further_recovery():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair dependent state after upstream change.",
    )

    events = [
        event_from_extension(
            make_register_commitment_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment=commitment,
                rid="rid:register",
            ).extension
        ),
        event_from_extension(
            make_fire_commitment_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                rid="rid:fire",
            ).extension
        ),
        event_from_extension(
            make_commitment_proposal_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                proposal_ref="proposal:repair:1",
                rid="rid:proposal",
            ).extension
        ),
        event_from_extension(
            make_commitment_rejected_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                rejection_code="CONSTRAINT_FAILED",
                rejection_evidence={"reason": "out_of_scope"},
                rid="rid:rejected",
            ).extension
        ),
    ]

    projection = replay_commitments(events)

    assert projection.status("c1") == CommitmentStatus.REJECTED
    assert "c1" in projection.live_commitments()


def test_admitted_commitment_proposal_is_not_live_after_replay():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair dependent state after upstream change.",
    )

    events = [
        event_from_extension(
            make_register_commitment_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment=commitment,
                rid="rid:register",
            ).extension
        ),
        event_from_extension(
            make_fire_commitment_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                rid="rid:fire",
            ).extension
        ),
        event_from_extension(
            make_commitment_proposal_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                proposal_ref="proposal:repair:1",
                rid="rid:proposal",
            ).extension
        ),
        event_from_extension(
            make_commitment_admitted_candidate(
                tenant_id="tenant:1",
                tx_group_id="tx:1",
                commitment_id="c1",
                admitted_record_ids=["rid:domain-repair"],
                rid="rid:admitted",
            ).extension
        ),
    ]

    projection = replay_commitments(events)

    assert projection.status("c1") == CommitmentStatus.ADMITTED
    assert "c1" not in projection.live_commitments()
