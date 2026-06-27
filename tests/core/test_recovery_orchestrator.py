from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEventType,
    CommitmentStatus,
    event_from_extension,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
    replay_commitments,
)
from mnemosyne.core.recovery import (
    RecoveryContext,
    RecoveryDecision,
    RecoveryPolicy,
    RecoveryProposal,
    orchestrate_recovery,
)


def test_allowed_recovery_emits_commitment_proposal_candidate_only():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = orchestrate_recovery(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": "entity:1"},
        ),
        workflow_id="workflow:1",
        rid="rid:proposal",
    )

    assert result.allowed
    assert result.check.decision == RecoveryDecision.ALLOW

    candidate = result.candidate

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_proposal_emitted"
    assert candidate.state_after == CommitmentStatus.PROPOSED.value

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.PROPOSAL_EMITTED
    assert event.payload["proposal_ref"] == "proposal:repair:1"
    assert event.payload["proposal_scope"] == {"entity_id": "entity:1"}


def test_scope_denied_recovery_emits_rejected_commitment_candidate():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = orchestrate_recovery(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:bad",
            proposal_scope={"entity_id": "entity:2"},
        ),
        workflow_id="workflow:1",
        rid="rid:rejected",
    )

    assert not result.allowed
    assert result.check.decision == RecoveryDecision.DENY_SCOPE_VIOLATION

    candidate = result.candidate

    assert candidate.eid == "commitment:c1"
    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_rejected"
    assert candidate.state_after == CommitmentStatus.REJECTED.value

    event = event_from_extension(candidate.extension)

    assert event.event_type == CommitmentEventType.REJECTED
    assert event.payload["rejection_code"] == "deny_scope_violation"
    assert event.payload["rejection_evidence"]["proposal_scope"] == {"entity_id": "entity:2"}


def test_attempt_limit_denied_recovery_emits_rejected_candidate():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    result = orchestrate_recovery(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=3),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": "entity:1"},
        ),
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
        rid="rid:rejected",
    )

    assert not result.allowed
    assert result.check.decision == RecoveryDecision.DENY_ATTEMPTS_EXCEEDED
    assert result.candidate.action_type == "commitment_rejected"

    event = event_from_extension(result.candidate.extension)

    assert event.payload["rejection_code"] == "deny_attempts_exceeded"


def test_rejected_orchestrated_recovery_keeps_commitment_live_after_replay():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "entity:1"},
    )

    rejected = orchestrate_recovery(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:bad",
            proposal_scope={"entity_id": "entity:2"},
        ),
        rid="rid:rejected",
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
        event_from_extension(rejected.candidate.extension),
    ]

    projection = replay_commitments(events)

    assert projection.status("c1") == CommitmentStatus.REJECTED
    assert "c1" in projection.live_commitments()


def test_orchestrator_never_targets_domain_entity_directly():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )

    result = orchestrate_recovery(
        tenant_id="tenant:1",
        tx_group_id="tx:1",
        commitment=commitment,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": "domain:entity:1"},
        ),
        rid="rid:proposal",
    )

    assert result.candidate.eid == "commitment:c1"
    assert result.candidate.eid != "domain:entity:1"
    assert result.candidate.fsm == "mnemosyne.commitment"
