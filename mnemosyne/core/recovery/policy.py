from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mnemosyne.core.commitments.models import ActiveCommitment


class RecoveryDecision(str, Enum):
    ALLOW = "allow"
    DENY_DEPTH_EXCEEDED = "deny_depth_exceeded"
    DENY_ATTEMPTS_EXCEEDED = "deny_attempts_exceeded"
    DENY_SCOPE_VIOLATION = "deny_scope_violation"


@dataclass(frozen=True)
class RecoveryPolicy:
    max_depth: int = 2
    max_attempts: int = 3
    require_scope_subset: bool = True


@dataclass(frozen=True)
class RecoveryContext:
    commitment_id: str
    depth: int = 0
    attempt_index: int = 0
    triggering_record_id: str | None = None
    triggering_error: str | None = None
    history: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecoveryProposal:
    proposal_ref: str
    proposal_scope: dict[str, Any] = field(default_factory=dict)
    rationale: str | None = None


@dataclass(frozen=True)
class RecoveryCheck:
    decision: RecoveryDecision
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.decision == RecoveryDecision.ALLOW


def _scope_contains(allowed: dict[str, Any], proposed: dict[str, Any]) -> bool:
    """Return True when every proposed scope item is allowed by dependency_scope.

    This is intentionally conservative and shallow for R4.5:
    proposed keys must exist in the commitment dependency_scope with equal values.
    Later we can support lists, wildcards, graph scopes, and semantic scopes.
    """
    for key, value in proposed.items():
        if key not in allowed:
            return False
        if allowed[key] != value:
            return False
    return True


def check_recovery_allowed(
    *,
    commitment: ActiveCommitment,
    context: RecoveryContext,
    proposal: RecoveryProposal,
    policy: RecoveryPolicy | None = None,
) -> RecoveryCheck:
    policy = policy or RecoveryPolicy()

    if context.depth > policy.max_depth:
        return RecoveryCheck(
            RecoveryDecision.DENY_DEPTH_EXCEEDED,
            {
                "depth": context.depth,
                "max_depth": policy.max_depth,
            },
        )

    if context.attempt_index >= policy.max_attempts:
        return RecoveryCheck(
            RecoveryDecision.DENY_ATTEMPTS_EXCEEDED,
            {
                "attempt_index": context.attempt_index,
                "max_attempts": policy.max_attempts,
            },
        )

    if policy.require_scope_subset and not _scope_contains(
        commitment.dependency_scope,
        proposal.proposal_scope,
    ):
        return RecoveryCheck(
            RecoveryDecision.DENY_SCOPE_VIOLATION,
            {
                "dependency_scope": commitment.dependency_scope,
                "proposal_scope": proposal.proposal_scope,
            },
        )

    return RecoveryCheck(
        RecoveryDecision.ALLOW,
        {
            "depth": context.depth,
            "attempt_index": context.attempt_index,
            "proposal_ref": proposal.proposal_ref,
        },
    )
