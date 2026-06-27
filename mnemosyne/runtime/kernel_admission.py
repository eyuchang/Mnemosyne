from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository


@dataclass(frozen=True)
class KernelCommitRequest:
    proposal_id: str
    tenant_id: str
    workflow_id: str
    binding_id: str
    agent_id: str
    entity_id: str
    fsm: str
    app_id: str
    schema_id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KernelCommitResult:
    ok: bool
    status: str
    committed_rids: tuple[str, ...] = ()
    audit_ref: str | None = None
    error_codes: tuple[str, ...] = ()
    message: str = ""


class KernelCommitter(Protocol):
    def commit(self, request: KernelCommitRequest) -> KernelCommitResult:
        ...


@dataclass(frozen=True)
class RuntimeKernelAdmissionResult:
    proposal_id: str
    decision_id: str
    status: str
    runtime_decision: str
    committed_rids: tuple[str, ...]
    error_codes: tuple[str, ...]
    audit_ref: str | None
    kernel_commit_performed: bool
    message: str


class KernelAdmissionAdapter:
    """Runtime admission adapter bound to a kernel commit boundary."""

    def __init__(self, repo: SQLiteRuntimeRepository, committer: KernelCommitter):
        self.repo = repo
        self.committer = committer

    def reject_before_commit(
        self,
        *,
        proposal_id: str,
        decision_id: str,
        tenant_id: str,
        workflow_id: str,
        binding_id: str,
        agent_id: str,
        reason: str,
        error_codes: tuple[str, ...] | list[str],
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeKernelAdmissionResult:
        if not error_codes:
            raise ValueError("Rejected runtime admission requires at least one error code.")

        self.repo.record_decision(
            decision_id=decision_id,
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            binding_id=binding_id,
            agent_id=agent_id,
            decision="rejected",
            reason=reason,
            committed_rids=[],
            error_codes=list(error_codes),
            metadata={
                **(metadata or {}),
                "kernel_commit_performed": False,
                "kernel_admission_status": "rejected_before_commit",
            },
        )

        return RuntimeKernelAdmissionResult(
            proposal_id=proposal_id,
            decision_id=decision_id,
            status="rejected_before_commit",
            runtime_decision="rejected",
            committed_rids=(),
            error_codes=tuple(error_codes),
            audit_ref=None,
            kernel_commit_performed=False,
            message=reason,
        )

    def accept_via_kernel(
        self,
        *,
        proposal_id: str,
        decision_id: str,
        tenant_id: str,
        workflow_id: str,
        binding_id: str,
        agent_id: str,
        entity_id: str,
        fsm: str,
        app_id: str,
        schema_id: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeKernelAdmissionResult:
        request = KernelCommitRequest(
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            binding_id=binding_id,
            agent_id=agent_id,
            entity_id=entity_id,
            fsm=fsm,
            app_id=app_id,
            schema_id=schema_id,
            payload=payload,
            metadata=metadata or {},
        )

        kernel_result = self.committer.commit(request)

        if kernel_result.ok and kernel_result.committed_rids:
            self.repo.record_decision(
                decision_id=decision_id,
                proposal_id=proposal_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                binding_id=binding_id,
                agent_id=agent_id,
                decision="accepted",
                reason=kernel_result.message or "accepted by kernel commit",
                committed_rids=list(kernel_result.committed_rids),
                error_codes=[],
                metadata={
                    **(metadata or {}),
                    "kernel_commit_performed": True,
                    "kernel_admission_status": "accepted_and_committed",
                    "kernel_audit_ref": kernel_result.audit_ref,
                },
            )

            return RuntimeKernelAdmissionResult(
                proposal_id=proposal_id,
                decision_id=decision_id,
                status="accepted_and_committed",
                runtime_decision="accepted",
                committed_rids=kernel_result.committed_rids,
                error_codes=(),
                audit_ref=kernel_result.audit_ref,
                kernel_commit_performed=True,
                message=kernel_result.message or "accepted by kernel commit",
            )

        if kernel_result.ok and not kernel_result.committed_rids:
            status = "commit_failed"
            error_codes = ("KERNEL_COMMIT_RETURNED_NO_RIDS",)
            message = "Kernel returned success without committed record IDs."
        else:
            status = kernel_result.status if kernel_result.status in {"validator_rejected", "commit_failed"} else "commit_failed"
            error_codes = kernel_result.error_codes or (status.upper(),)
            message = kernel_result.message or status

        self.repo.record_decision(
            decision_id=decision_id,
            proposal_id=proposal_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            binding_id=binding_id,
            agent_id=agent_id,
            decision="rejected",
            reason=message,
            committed_rids=[],
            error_codes=list(error_codes),
            metadata={
                **(metadata or {}),
                "kernel_commit_performed": True,
                "kernel_admission_status": status,
                "kernel_audit_ref": kernel_result.audit_ref,
            },
        )

        return RuntimeKernelAdmissionResult(
            proposal_id=proposal_id,
            decision_id=decision_id,
            status=status,
            runtime_decision="rejected",
            committed_rids=(),
            error_codes=tuple(error_codes),
            audit_ref=kernel_result.audit_ref,
            kernel_commit_performed=True,
            message=message,
        )
