from __future__ import annotations

from mnemosyne.service.app import R8DeploymentService
from mnemosyne.service.schemas import ProposalRequest


def test_r8_service_rejects_direct_commit_bypass_attempts() -> None:
    service = R8DeploymentService()

    decision = service.submit_proposal(
        ProposalRequest(
            tenant="tenant",
            workflow="wf",
            entity="entity",
            operation="raw_append",
            payload={"direct_commit": True},
        )
    )

    assert decision.accepted is False
    assert decision.reason in {"direct_commit_forbidden", "operation_not_admissible"}
    assert service.committed == {}


def test_r8_service_commits_only_admitted_proposals_to_effective_state() -> None:
    service = R8DeploymentService()

    ok = service.submit_proposal(
        ProposalRequest(
            tenant="tenant",
            workflow="wf",
            entity="entity",
            operation="valid_transition",
            payload={"valid_under_c": True, "value": 7},
        )
    )
    bad = service.submit_proposal(
        ProposalRequest(
            tenant="tenant",
            workflow="wf",
            entity="entity",
            operation="valid_transition",
            payload={"valid_under_c": False, "value": 999},
        )
    )

    state = service.state("tenant", "entity")

    assert ok.accepted is True
    assert bad.accepted is False
    assert state["effective_record_count"] == 1
    assert state["records"][0]["payload"]["value"] == 7


def test_r8_service_rejects_explicit_admission_bypass_flag() -> None:
    service = R8DeploymentService()

    decision = service.submit_proposal(
        ProposalRequest(
            tenant="tenant",
            workflow="wf",
            entity="entity",
            operation="valid_transition",
            payload={"valid_under_c": True, "bypass_admission": True},
        )
    )

    assert decision.accepted is False
    assert decision.reason == "bypass_admission_requested"
    assert service.state("tenant", "entity")["effective_record_count"] == 0
