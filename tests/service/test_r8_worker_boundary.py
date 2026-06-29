from __future__ import annotations

from mnemosyne.service.app import R8DeploymentService
from mnemosyne.service.schemas import ProposalRequest
from mnemosyne.service.worker import R8DeploymentWorker


def test_r8_worker_has_no_direct_commit_api() -> None:
    service = R8DeploymentService()
    worker = R8DeploymentWorker(service)

    forbidden = {"commit", "raw_append", "direct_write", "append_truth"}
    exposed = {name for name in dir(worker) if not name.startswith("_")}

    assert forbidden.isdisjoint(exposed)


def test_r8_worker_routes_all_mutation_through_admission() -> None:
    service = R8DeploymentService()
    worker = R8DeploymentWorker(service)

    result = worker.submit_many(
        [
            ProposalRequest(
                tenant="t",
                workflow="w",
                entity="e",
                operation="valid_transition",
                payload={"valid_under_c": True, "value": 1},
            ),
            ProposalRequest(
                tenant="t",
                workflow="w",
                entity="e",
                operation="valid_transition",
                payload={"valid_under_c": False, "value": 999},
            ),
            ProposalRequest(
                tenant="t",
                workflow="w",
                entity="e",
                operation="raw_append",
                payload={"direct_commit": True},
            ),
        ]
    )

    state = service.state("t", "e")

    assert result.submitted == 3
    assert result.admitted == 1
    assert result.rejected == 2
    assert result.invalid_commits == 0
    assert state["effective_record_count"] == 1
    assert state["records"][0]["payload"]["value"] == 1


def test_r8_worker_preserves_metrics_boundary() -> None:
    service = R8DeploymentService()
    worker = R8DeploymentWorker(service)

    worker.submit_many(
        ProposalRequest(
            tenant="tenant",
            workflow="wf",
            entity=f"entity-{i}",
            operation="valid_transition",
            payload={"valid_under_c": i % 2 == 0},
        )
        for i in range(10)
    )

    metrics = service.metrics.render_prometheus()

    assert "mnemosyne_service_proposals_total 10" in metrics
    assert "mnemosyne_service_admitted_total 5" in metrics
    assert "mnemosyne_service_rejected_total 5" in metrics
