from __future__ import annotations

from dataclasses import dataclass

from mnemosyne.core.commitments.ctl import extract_commitment_events_from_ctl_records
from mnemosyne.core.commitments.models import ActiveCommitment, CommitmentStatus
from mnemosyne.core.commitments.projection import CommitmentProjection, replay_commitments


@dataclass(frozen=True)
class ActiveCommitmentIndex:
    """Replay-derived read model for active commitments.

    This index is not authoritative. It is a projection reconstructed from CTL
    commitment events. The CTL remains the source of truth.
    """

    projection: CommitmentProjection

    @classmethod
    def from_events(cls, events) -> "ActiveCommitmentIndex":
        return cls(projection=replay_commitments(list(events)))

    @classmethod
    def from_ctl_records(cls, records) -> "ActiveCommitmentIndex":
        events = extract_commitment_events_from_ctl_records(list(records))
        return cls.from_events(events)

    def get(self, commitment_id: str) -> ActiveCommitment | None:
        return self.projection.commitments.get(commitment_id)

    def status(self, commitment_id: str) -> CommitmentStatus | None:
        return self.projection.statuses.get(commitment_id)

    def is_live(self, commitment_id: str) -> bool:
        return commitment_id in self.projection.live_commitments()

    def live_commitments(self) -> dict[str, ActiveCommitment]:
        return self.projection.live_commitments()

    def live_commitment_ids(self) -> list[str]:
        return sorted(self.live_commitments().keys())

    def commitments_by_type(self, commitment_type: str) -> dict[str, ActiveCommitment]:
        return {
            cid: commitment
            for cid, commitment in self.projection.commitments.items()
            if commitment.commitment_type == commitment_type
        }

    def live_commitments_by_type(self, commitment_type: str) -> dict[str, ActiveCommitment]:
        return {
            cid: commitment
            for cid, commitment in self.live_commitments().items()
            if commitment.commitment_type == commitment_type
        }
