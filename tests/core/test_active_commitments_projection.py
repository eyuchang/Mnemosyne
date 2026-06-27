from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEvent,
    CommitmentEventType,
    CommitmentStatus,
    replay_commitments,
)


def test_registered_commitment_replays_as_live():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Revalidate dependent step when upstream fact changes.",
        dependency_scope={"entity_id": "entity:1"},
        trigger={"kind": "world_change"},
    )

    projection = replay_commitments([
        CommitmentEvent(
            event_type=CommitmentEventType.REGISTERED,
            commitment_id="c1",
            payload={"commitment": commitment},
        )
    ])

    assert projection.status("c1") == CommitmentStatus.LIVE
    assert "c1" in projection.live_commitments()


def test_fired_commitment_is_still_live_but_not_mutating():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="delayed_guard",
        description="Wake when guard becomes true.",
    )

    projection = replay_commitments([
        CommitmentEvent(
            event_type=CommitmentEventType.REGISTERED,
            commitment_id="c1",
            payload={"commitment": commitment},
        ),
        CommitmentEvent(
            event_type=CommitmentEventType.FIRED,
            commitment_id="c1",
            payload={"reason": "trigger_true"},
        ),
    ])

    assert projection.status("c1") == CommitmentStatus.FIRED
    assert "c1" in projection.live_commitments()


def test_discharged_commitment_is_not_live_after_replay():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="evidence_preservation",
        description="Preserve evidence until admitted repair.",
    )

    projection = replay_commitments([
        CommitmentEvent(
            event_type=CommitmentEventType.REGISTERED,
            commitment_id="c1",
            payload={"commitment": commitment},
        ),
        CommitmentEvent(
            event_type=CommitmentEventType.DISCHARGED,
            commitment_id="c1",
            payload={"reason": "obligation_satisfied"},
        ),
    ])

    assert projection.status("c1") == CommitmentStatus.DISCHARGED
    assert "c1" not in projection.live_commitments()


def test_expired_commitment_is_not_live_after_replay():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="temporary_watch",
        description="Temporary watch with expiry.",
        expiry="2026-12-31T00:00:00Z",
    )

    projection = replay_commitments([
        CommitmentEvent(
            event_type=CommitmentEventType.REGISTERED,
            commitment_id="c1",
            payload={"commitment": commitment},
        ),
        CommitmentEvent(
            event_type=CommitmentEventType.EXPIRED,
            commitment_id="c1",
            payload={"reason": "expiry_reached"},
        ),
    ])

    assert projection.status("c1") == CommitmentStatus.EXPIRED
    assert "c1" not in projection.live_commitments()


def test_unknown_commitment_event_rejected_by_projection():
    projection = replay_commitments([])

    try:
        projection.apply(
            CommitmentEvent(
                event_type=CommitmentEventType.FIRED,
                commitment_id="missing",
            )
        )
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected KeyError for unknown commitment")
