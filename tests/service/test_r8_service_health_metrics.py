from __future__ import annotations

from mnemosyne.service.app import R8DeploymentService
from mnemosyne.service.schemas import ProposalRequest


def test_r8_service_health_exposes_authority_boundary() -> None:
    service = R8DeploymentService()
    health = service.health()

    assert health["ok"] is True
    assert health["service"] == "mnemosyne-r8-deployment-service"
    assert health["authority_boundary"] == "proposal_admission_only"


def test_r8_service_metrics_records_admission_decisions() -> None:
    service = R8DeploymentService()

    accepted = service.submit_proposal(
        ProposalRequest(
            tenant="t1",
            workflow="w1",
            entity="e1",
            operation="schedule",
            payload={"valid_under_c": True},
        )
    )
    rejected = service.submit_proposal(
        ProposalRequest(
            tenant="t1",
            workflow="w1",
            entity="e1",
            operation="schedule",
            payload={"valid_under_c": False},
        )
    )

    assert accepted.accepted is True
    assert rejected.accepted is False

    metrics = service.metrics.render_prometheus()
    assert "mnemosyne_service_proposals_total 2" in metrics
    assert "mnemosyne_service_admitted_total 1" in metrics
    assert "mnemosyne_service_rejected_total 1" in metrics
    assert "mnemosyne_service_admission_latency_ms_count 2" in metrics
