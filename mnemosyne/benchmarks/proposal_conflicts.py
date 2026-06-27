# File: mnemosyne/benchmarks/proposal_conflicts.py
#
# Purpose:
#   Proposal conflict detection for solver/agent plan proposals.
#
# Stage:
#   R2.2 — proposal conflict semantics.
#
# Design rule:
#   A solver certificate proves what a solver claims.
#   It does not guarantee that the proposal can be admitted.
#
#   Before admission, proposals must be checked for conflicts over their
#   workflow/entity/dependency scopes.
#
#   Mnemosyne remains the commit authority.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from mnemosyne.benchmarks.solver import PlanProposal


@dataclass(frozen=True)
class ProposalConflict:
    """A conflict between two active plan proposals."""

    conflict_type: str
    left_proposal_id: str
    right_proposal_id: str
    scope: str
    message: str


@dataclass(frozen=True)
class ProposalConflictReport:
    """Result of proposal conflict analysis."""

    ok: bool
    conflicts: list[ProposalConflict] = field(default_factory=list)

    @property
    def error_codes(self) -> list[str]:
        return [
            conflict.conflict_type
            for conflict in self.conflicts
        ]


def _same_tenant(left: PlanProposal, right: PlanProposal) -> bool:
    return left.tenant_id == right.tenant_id


def _proposal_pair_id(left: PlanProposal, right: PlanProposal) -> tuple[str, str]:
    return tuple(sorted([left.proposal_id, right.proposal_id]))  # type: ignore[return-value]


def _conflict(
    *,
    conflict_type: str,
    left: PlanProposal,
    right: PlanProposal,
    scope: str,
    message: str,
) -> ProposalConflict:
    left_id, right_id = _proposal_pair_id(left, right)

    return ProposalConflict(
        conflict_type=conflict_type,
        left_proposal_id=left_id,
        right_proposal_id=right_id,
        scope=scope,
        message=message,
    )


def detect_proposal_conflicts(
    proposals: Iterable[PlanProposal],
) -> ProposalConflictReport:
    """Detect conflicts among active proposals.

    R2.2 intentionally uses conservative fail-closed semantics.

    Current conflict rules:

    1. Duplicate proposal IDs conflict.
       Proposal IDs must be unique in the active proposal set.

    2. Same tenant + same entity + different proposal IDs conflict.
       Two different active proposals may not both claim authority over the
       same entity.

    3. Same tenant + same workflow + same entity + different route conflict.
       This catches alternative plans for the same workflow/entity pair.

    Non-conflict rule:

    - Different tenants do not conflict.
    - Different entities in the same tenant do not conflict at this layer.
      Future dependency-scope rules can extend this.
    """
    proposal_list = list(proposals)
    conflicts: list[ProposalConflict] = []

    for index, left in enumerate(proposal_list):
        for right in proposal_list[index + 1:]:
            if not _same_tenant(left, right):
                continue

            if left.proposal_id == right.proposal_id:
                conflicts.append(
                    _conflict(
                        conflict_type="DUPLICATE_PROPOSAL_ID",
                        left=left,
                        right=right,
                        scope=f"proposal:{left.proposal_id}",
                        message=(
                            "two active proposals share the same proposal_id"
                        ),
                    )
                )
                continue

            if left.entity_id == right.entity_id:
                conflicts.append(
                    _conflict(
                        conflict_type="ENTITY_PROPOSAL_CONFLICT",
                        left=left,
                        right=right,
                        scope=f"tenant:{left.tenant_id}/entity:{left.entity_id}",
                        message=(
                            "two different active proposals target the same entity"
                        ),
                    )
                )
                continue

            if (
                left.workflow_id == right.workflow_id
                and left.entity_id == right.entity_id
                and left.route != right.route
            ):
                conflicts.append(
                    _conflict(
                        conflict_type="WORKFLOW_ROUTE_CONFLICT",
                        left=left,
                        right=right,
                        scope=(
                            f"tenant:{left.tenant_id}/"
                            f"workflow:{left.workflow_id}/"
                            f"entity:{left.entity_id}"
                        ),
                        message=(
                            "two active proposals for the same workflow/entity "
                            "carry different routes"
                        ),
                    )
                )

    return ProposalConflictReport(
        ok=not conflicts,
        conflicts=conflicts,
    )


def assert_no_proposal_conflicts(
    proposals: Iterable[PlanProposal],
) -> None:
    """Raise ValueError if proposal conflicts exist."""

    report = detect_proposal_conflicts(proposals)

    if report.ok:
        return

    details = "; ".join(
        f"{conflict.conflict_type}:{conflict.scope}"
        for conflict in report.conflicts
    )

    raise ValueError(f"proposal conflicts detected: {details}")
