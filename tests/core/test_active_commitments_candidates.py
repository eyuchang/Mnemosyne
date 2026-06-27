from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEventType,
    CommitmentStatus,
    event_from_extension,
    make_discharge_commitment_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)


def test_register_commitment_candidate_contains_commitment_event_extension():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Revalidate when upstream evidence changes.",
    )

    candidate = make_register_commitment_candidate(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        workflow_id="workflow:1",
        rid="rid:register",
    )

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_registered"
    assert candidate.state_before == "none"
    assert candidate.state_after == CommitmentStatus.LIVE.value
    assert candidate.schema_id == "mnemosyne.active_commitment_event"

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.REGISTERED
    assert event.commitment_id == "c1"
    assert event.payload["commitment"] == commitment


def test_fire_commitment_candidate_is_non_domain_state_transition():
    candidate = make_fire_commitment_candidate(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment_id="c1",
        workflow_id="workflow:1",
        rid="rid:fire",
        dependency_rid="rid:upstream",
    )

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_fired"
    assert candidate.state_before == CommitmentStatus.LIVE.value
    assert candidate.state_after == CommitmentStatus.FIRED.value
    assert candidate.dependencies == ["rid:upstream"]

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.FIRED
    assert event.commitment_id == "c1"
    assert event.payload["reason"] == "trigger_true"


def test_discharge_commitment_candidate_marks_obligation_not_live():
    candidate = make_discharge_commitment_candidate(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment_id="c1",
        workflow_id="workflow:1",
        rid="rid:discharge",
        reason="obligation_satisfied",
    )

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_discharged"
    assert candidate.state_after == CommitmentStatus.DISCHARGED.value

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.DISCHARGED
    assert event.payload["reason"] == "obligation_satisfied"
