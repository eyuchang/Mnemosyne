from mnemosyne.core.commitments import ActiveCommitment
from mnemosyne.core.recovery import (
    RecoveryContext,
    RecoveryDecision,
    RecoveryPolicy,
    RecoveryProposal,
    check_recovery_allowed,
)


def test_recovery_allowed_when_depth_attempt_and_scope_are_valid():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1", "field": "status"},
    )

    result = check_recovery_allowed(
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=1, attempt_index=1),
        proposal=RecoveryProposal(
            proposal_ref="proposal:1",
            proposal_scope={"entity_id": "entity:1"},
        ),
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert result.ok
    assert result.decision == RecoveryDecision.ALLOW


def test_recovery_denied_when_depth_exceeds_policy():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = check_recovery_allowed(
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=3, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:1",
            proposal_scope={"entity_id": "entity:1"},
        ),
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert not result.ok
    assert result.decision == RecoveryDecision.DENY_DEPTH_EXCEEDED


def test_recovery_denied_when_attempts_exceed_policy():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = check_recovery_allowed(
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=1, attempt_index=3),
        proposal=RecoveryProposal(
            proposal_ref="proposal:1",
            proposal_scope={"entity_id": "entity:1"},
        ),
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert not result.ok
    assert result.decision == RecoveryDecision.DENY_ATTEMPTS_EXCEEDED


def test_recovery_denied_when_proposal_scope_escapes_commitment_scope():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = check_recovery_allowed(
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:1",
            proposal_scope={"entity_id": "entity:2"},
        ),
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
    )

    assert not result.ok
    assert result.decision == RecoveryDecision.DENY_SCOPE_VIOLATION


def test_empty_proposal_scope_is_allowed_as_non_mutating_wakeup():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="wake_only",
        description="Wake runtime without proposing domain mutation.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = check_recovery_allowed(
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:wakeup-only",
            proposal_scope={},
        ),
    )

    assert result.ok
