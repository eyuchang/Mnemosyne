from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    event_from_extension,
)
from mnemosyne.core.recovery import (
    RecoveryContext,
    RecoveryDecision,
    RecoveryPolicy,
    RecoveryProposal,
    run_bounded_recovery_loop,
)


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )


def test_recovery_loop_stops_on_first_allowed_proposal():
    result = run_bounded_recovery_loop(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment(),
        start_context=RecoveryContext(commitment_id="c1"),
        proposals=[
            RecoveryProposal(
                proposal_ref="proposal:repair:1",
                proposal_scope={"entity_id": "domain:entity:1"},
            )
        ],
    )

    assert result.allowed
    assert not result.exhausted
    assert result.terminal_status == CommitmentStatus.PROPOSED
    assert len(result.results) == 1
    assert result.candidates[0].action_type == "commitment_proposal_emitted"
    assert result.candidates[0].state_before == CommitmentStatus.FIRED.value


def test_recovery_loop_retries_after_scope_rejection_and_then_proposes():
    result = run_bounded_recovery_loop(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment(),
        start_context=RecoveryContext(commitment_id="c1"),
        proposals=[
            RecoveryProposal(
                proposal_ref="proposal:bad",
                proposal_scope={"entity_id": "domain:outside"},
            ),
            RecoveryProposal(
                proposal_ref="proposal:repair:1",
                proposal_scope={"entity_id": "domain:entity:1"},
            ),
        ],
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert result.allowed
    assert not result.exhausted
    assert result.terminal_status == CommitmentStatus.PROPOSED
    assert [r.candidate.action_type for r in result.results] == [
        "commitment_rejected",
        "commitment_proposal_emitted",
    ]
    assert result.results[0].candidate.state_before == CommitmentStatus.FIRED.value
    assert result.results[1].candidate.state_before == CommitmentStatus.REJECTED.value


def test_recovery_loop_stops_when_attempt_limit_is_reached():
    result = run_bounded_recovery_loop(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment(),
        start_context=RecoveryContext(commitment_id="c1"),
        proposals=[
            RecoveryProposal(
                proposal_ref="proposal:bad:1",
                proposal_scope={"entity_id": "domain:outside:1"},
            ),
            RecoveryProposal(
                proposal_ref="proposal:bad:2",
                proposal_scope={"entity_id": "domain:outside:2"},
            ),
        ],
        policy=RecoveryPolicy(max_depth=2, max_attempts=1),
    )

    assert not result.allowed
    assert result.exhausted
    assert result.terminal_status == CommitmentStatus.REJECTED
    assert len(result.results) == 2
    assert result.results[-1].check.decision == RecoveryDecision.DENY_ATTEMPTS_EXCEEDED
    assert result.results[-1].candidate.state_before == CommitmentStatus.REJECTED.value


def test_recovery_loop_stops_when_depth_is_exceeded():
    result = run_bounded_recovery_loop(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment(),
        start_context=RecoveryContext(commitment_id="c1", depth=3),
        proposals=[
            RecoveryProposal(
                proposal_ref="proposal:repair:1",
                proposal_scope={"entity_id": "domain:entity:1"},
            )
        ],
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert not result.allowed
    assert result.exhausted
    assert result.terminal_status == CommitmentStatus.REJECTED
    assert result.results[0].check.decision == RecoveryDecision.DENY_DEPTH_EXCEEDED


def test_recovery_loop_never_emits_domain_transition_candidates():
    result = run_bounded_recovery_loop(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment(),
        start_context=RecoveryContext(commitment_id="c1"),
        proposals=[
            RecoveryProposal(
                proposal_ref="proposal:bad",
                proposal_scope={"entity_id": "domain:outside"},
            ),
            RecoveryProposal(
                proposal_ref="proposal:repair:1",
                proposal_scope={"entity_id": "domain:entity:1"},
            ),
        ],
    )

    for candidate in result.candidates:
        assert candidate.eid == "commitment:c1"
        assert candidate.fsm == "mnemosyne.commitment"
        assert candidate.eid != "domain:entity:1"

    events = [event_from_extension(candidate.extension) for candidate in result.candidates]
    assert [event.commitment_id for event in events] == ["c1", "c1"]
