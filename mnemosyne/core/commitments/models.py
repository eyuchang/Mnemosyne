from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommitmentEventType(str, Enum):
    REGISTERED = "commitment_registered"
    FIRED = "commitment_fired"
    PROPOSAL_EMITTED = "commitment_proposal_emitted"
    ADMITTED = "commitment_admitted"
    REJECTED = "commitment_rejected"
    DISCHARGED = "commitment_discharged"
    EXPIRED = "commitment_expired"


class CommitmentStatus(str, Enum):
    LIVE = "live"
    FIRED = "fired"
    PROPOSED = "proposed"
    ADMITTED = "admitted"
    REJECTED = "rejected"
    DISCHARGED = "discharged"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ActiveCommitment:
    commitment_id: str
    commitment_type: str
    description: str

    creating_record_id: str | None = None
    creating_workflow_id: str | None = None

    dependency_scope: dict[str, Any] = field(default_factory=dict)
    trigger: dict[str, Any] = field(default_factory=dict)

    continuation_ref: str | None = None
    guard_ref: str | None = None
    validator_ref: str | None = None
    compensation_ref: str | None = None

    priority: int = 0
    expiry: str | None = None

    failure_signature: dict[str, Any] | None = None
    cross_episode_key: str | None = None


@dataclass(frozen=True)
class CommitmentEvent:
    event_type: CommitmentEventType
    commitment_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    record_id: str | None = None
    workflow_id: str | None = None
