from __future__ import annotations

from dataclasses import dataclass, field

from mnemosyne.core.commitments.models import (
    ActiveCommitment,
    CommitmentEvent,
    CommitmentEventType,
    CommitmentStatus,
)


@dataclass
class CommitmentProjection:
    commitments: dict[str, ActiveCommitment] = field(default_factory=dict)
    statuses: dict[str, CommitmentStatus] = field(default_factory=dict)

    def apply(self, event: CommitmentEvent) -> None:
        cid = event.commitment_id

        if event.event_type == CommitmentEventType.REGISTERED:
            commitment = event.payload.get("commitment")
            if not isinstance(commitment, ActiveCommitment):
                raise TypeError("REGISTERED event payload must contain ActiveCommitment under key 'commitment'")
            self.commitments[cid] = commitment
            self.statuses[cid] = CommitmentStatus.LIVE
            return

        if cid not in self.commitments:
            raise KeyError(f"Unknown commitment_id: {cid}")

        if event.event_type == CommitmentEventType.FIRED:
            self.statuses[cid] = CommitmentStatus.FIRED
        elif event.event_type == CommitmentEventType.PROPOSAL_EMITTED:
            self.statuses[cid] = CommitmentStatus.PROPOSED
        elif event.event_type == CommitmentEventType.ADMITTED:
            self.statuses[cid] = CommitmentStatus.ADMITTED
        elif event.event_type == CommitmentEventType.REJECTED:
            self.statuses[cid] = CommitmentStatus.REJECTED
        elif event.event_type == CommitmentEventType.DISCHARGED:
            self.statuses[cid] = CommitmentStatus.DISCHARGED
        elif event.event_type == CommitmentEventType.EXPIRED:
            self.statuses[cid] = CommitmentStatus.EXPIRED
        else:
            raise ValueError(f"Unhandled commitment event type: {event.event_type}")

    def live_commitments(self) -> dict[str, ActiveCommitment]:
        return {
            cid: commitment
            for cid, commitment in self.commitments.items()
            if self.statuses.get(cid) in {
                CommitmentStatus.LIVE,
                CommitmentStatus.FIRED,
                CommitmentStatus.PROPOSED,
                CommitmentStatus.REJECTED,
            }
        }

    def status(self, commitment_id: str) -> CommitmentStatus:
        return self.statuses[commitment_id]


def replay_commitments(events: list[CommitmentEvent]) -> CommitmentProjection:
    projection = CommitmentProjection()
    for event in events:
        projection.apply(event)
    return projection
