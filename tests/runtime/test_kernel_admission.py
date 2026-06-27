from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from mnemosyne.runtime.kernel_admission import (
    KernelAdmissionAdapter,
    KernelCommitRequest,
    KernelCommitResult,
)
from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository


def seed_runtime(repo: SQLiteRuntimeRepository) -> dict[str, str]:
    ids = {
        "tenant_id": "tenant:r4-kernel",
        "workflow_id": "workflow:r4-kernel",
        "binding_id": "binding:r4-kernel",
        "agent_id": "agent:r4-kernel",
        "agent_binding_id": "agent-binding:r4-kernel",
        "entity_id": "entity:r4-kernel",
        "proposal_id": "proposal:r4-kernel",
        "fsm": "CampusTourFSM",
        "app_id": "campus_tour",
        "schema_id": "campus_tour.transition",
    }

    repo.create_workflow(
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    repo.create_workflow_binding(
        binding_id=ids["binding_id"],
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    repo.create_agent(
        agent_id=ids["agent_id"],
        tenant_id=ids["tenant_id"],
        agent_type="planner",
        display_name="R4 Kernel Planner",
    )

    repo.create_agent_binding(
        agent_binding_id=ids["agent_binding_id"],
        agent_id=ids["agent_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    repo.submit_proposal(
        proposal_id=ids["proposal_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        agent_binding_id=ids["agent_binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["S", "D", "A", "B", "L", "S"]},
    )

    return ids


@dataclass
class RecordingCommitter:
    result: KernelCommitResult
    calls: list[KernelCommitRequest] = field(default_factory=list)

    def commit(self, request: KernelCommitRequest) -> KernelCommitResult:
        self.calls.append(request)
        return self.result


def make_adapter(tmp_path, result: KernelCommitResult):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_runtime(repo)
    committer = RecordingCommitter(result)
    adapter = KernelAdmissionAdapter(repo, committer)
    return repo, adapter, committer, ids


def test_accept_via_kernel_records_accepted_and_committed(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(
            ok=True,
            status="committed",
            committed_rids=("rid:kernel:001",),
            audit_ref="audit:kernel:001",
            message="kernel commit succeeded",
        ),
    )

    result = adapter.accept_via_kernel(
        proposal_id=ids["proposal_id"],
        decision_id="decision:r4-kernel:accepted",
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["S", "D", "A", "B", "L", "S"]},
    )

    assert result.status == "accepted_and_committed"
    assert result.runtime_decision == "accepted"
    assert result.committed_rids == ("rid:kernel:001",)
    assert result.kernel_commit_performed is True
    assert len(committer.calls) == 1

    proposal = repo.get_proposal(ids["proposal_id"])
    decision = repo.get_decision_for_proposal(ids["proposal_id"])
    traces = repo.list_trace_events(proposal_id=ids["proposal_id"])

    assert proposal["status"] == "accepted"
    assert decision["decision"] == "accepted"
    assert decision["committed_rids"] == ["rid:kernel:001"]
    assert decision["error_codes"] == []
    assert decision["metadata"]["kernel_commit_performed"] is True
    assert decision["metadata"]["kernel_admission_status"] == "accepted_and_committed"
    assert decision["metadata"]["kernel_audit_ref"] == "audit:kernel:001"
    assert [trace["event_type"] for trace in traces] == [
        "proposal_submitted",
        "admission_accepted",
    ]


def test_reject_before_commit_never_calls_kernel(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(
            ok=True,
            status="committed",
            committed_rids=("rid:should-not-appear",),
        ),
    )

    result = adapter.reject_before_commit(
        proposal_id=ids["proposal_id"],
        decision_id="decision:r4-kernel:preflight",
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        reason="preflight rejected",
        error_codes=("DOMAIN_FEASIBILITY_REJECTED",),
    )

    assert result.status == "rejected_before_commit"
    assert result.runtime_decision == "rejected"
    assert result.kernel_commit_performed is False
    assert len(committer.calls) == 0

    proposal = repo.get_proposal(ids["proposal_id"])
    decision = repo.get_decision_for_proposal(ids["proposal_id"])

    assert proposal["status"] == "rejected"
    assert decision["committed_rids"] == []
    assert decision["error_codes"] == ["DOMAIN_FEASIBILITY_REJECTED"]
    assert decision["metadata"]["kernel_commit_performed"] is False
    assert decision["metadata"]["kernel_admission_status"] == "rejected_before_commit"


def test_validator_rejection_records_rejected_without_committed_rids(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(
            ok=False,
            status="validator_rejected",
            audit_ref="audit:validator:001",
            error_codes=("VALIDATOR_REJECTED",),
            message="validator rejected proposal",
        ),
    )

    result = adapter.accept_via_kernel(
        proposal_id=ids["proposal_id"],
        decision_id="decision:r4-kernel:validator",
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["bad"]},
    )

    assert result.status == "validator_rejected"
    assert result.runtime_decision == "rejected"
    assert result.committed_rids == ()
    assert result.error_codes == ("VALIDATOR_REJECTED",)
    assert len(committer.calls) == 1

    proposal = repo.get_proposal(ids["proposal_id"])
    decision = repo.get_decision_for_proposal(ids["proposal_id"])

    assert proposal["status"] == "rejected"
    assert decision["committed_rids"] == []
    assert decision["error_codes"] == ["VALIDATOR_REJECTED"]
    assert decision["metadata"]["kernel_admission_status"] == "validator_rejected"
    assert decision["metadata"]["kernel_audit_ref"] == "audit:validator:001"


def test_commit_failure_records_rejected_without_committed_truth(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(
            ok=False,
            status="commit_failed",
            audit_ref="audit:commit:001",
            error_codes=("STORE_COMMIT_FAILED",),
            message="store commit failed",
        ),
    )

    result = adapter.accept_via_kernel(
        proposal_id=ids["proposal_id"],
        decision_id="decision:r4-kernel:commit-failed",
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["S", "D"]},
    )

    assert result.status == "commit_failed"
    assert result.runtime_decision == "rejected"
    assert result.error_codes == ("STORE_COMMIT_FAILED",)

    proposal = repo.get_proposal(ids["proposal_id"])
    decision = repo.get_decision_for_proposal(ids["proposal_id"])

    assert proposal["status"] == "rejected"
    assert decision["committed_rids"] == []
    assert decision["error_codes"] == ["STORE_COMMIT_FAILED"]
    assert decision["metadata"]["kernel_admission_status"] == "commit_failed"


def test_success_without_committed_rids_becomes_commit_failed(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(
            ok=True,
            status="committed",
            committed_rids=(),
            audit_ref="audit:no-rids",
            message="bad success",
        ),
    )

    result = adapter.accept_via_kernel(
        proposal_id=ids["proposal_id"],
        decision_id="decision:r4-kernel:no-rids",
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["S", "D"]},
    )

    assert result.status == "commit_failed"
    assert result.runtime_decision == "rejected"
    assert result.error_codes == ("KERNEL_COMMIT_RETURNED_NO_RIDS",)

    proposal = repo.get_proposal(ids["proposal_id"])
    decision = repo.get_decision_for_proposal(ids["proposal_id"])

    assert proposal["status"] == "rejected"
    assert decision["committed_rids"] == []
    assert decision["error_codes"] == ["KERNEL_COMMIT_RETURNED_NO_RIDS"]


def test_reject_before_commit_requires_error_code(tmp_path):
    repo, adapter, committer, ids = make_adapter(
        tmp_path,
        KernelCommitResult(ok=True, status="committed", committed_rids=("rid:unused",)),
    )

    with pytest.raises(ValueError):
        adapter.reject_before_commit(
            proposal_id=ids["proposal_id"],
            decision_id="decision:r4-kernel:bad-reject",
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            reason="missing error code",
            error_codes=(),
        )
