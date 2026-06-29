from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from mnemosyne.service.app import R8DeploymentService
from mnemosyne.service.schemas import ProposalDecision, ProposalRequest


@dataclass(frozen=True)
class WorkerBatchResult:
    submitted: int
    admitted: int
    rejected: int
    invalid_commits: int
    committed_record_ids: tuple[str, ...] = field(default_factory=tuple)


class R8DeploymentWorker:
    """Non-authoritative deployment worker.

    R8 worker rule:
      The worker may orchestrate proposal submission, but it has no committed
      truth write API. It can only hand ProposalRequest objects to the service
      admission boundary.
    """

    def __init__(self, service: R8DeploymentService) -> None:
        self._service = service

    def submit(self, proposal: ProposalRequest) -> ProposalDecision:
        return self._service.submit_proposal(proposal)

    def submit_many(self, proposals: Iterable[ProposalRequest]) -> WorkerBatchResult:
        submitted = 0
        admitted = 0
        rejected = 0
        invalid_commits = 0
        record_ids: list[str] = []

        for proposal in proposals:
            submitted += 1
            decision = self.submit(proposal)

            if decision.accepted:
                admitted += 1
                if decision.committed_record_id is not None:
                    record_ids.append(decision.committed_record_id)

                # Deployment-level safety check: proposals explicitly marked
                # invalid by the workload must never be admitted.
                if proposal.payload.get("valid_under_c") is False:
                    invalid_commits += 1
                if proposal.payload.get("direct_commit") is True:
                    invalid_commits += 1
                if proposal.payload.get("bypass_admission") is True:
                    invalid_commits += 1
            else:
                rejected += 1

        return WorkerBatchResult(
            submitted=submitted,
            admitted=admitted,
            rejected=rejected,
            invalid_commits=invalid_commits,
            committed_record_ids=tuple(record_ids),
        )
