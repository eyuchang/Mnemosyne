# File: mnemosyne/runtime/temporal/client.py
#
# Purpose:
#   Define a small Temporal-client boundary that can be implemented by:
#
#   - a fake local client for deterministic tests;
#   - a future real temporalio-backed client.
#
# Rule:
#   Temporal clients orchestrate workflows only. They do not own domain truth.
#   CTL/store remains the source of committed domain state.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from mnemosyne.core.models import ExternalEvent, RuntimeStatus, WorkflowHandle


class TemporalClientLike(Protocol):
    async def start_workflow(self, spec: dict[str, Any]) -> WorkflowHandle:
        ...

    async def signal_workflow(self, workflow_id: str, event: ExternalEvent) -> None:
        ...

    async def query_workflow(self, workflow_id: str) -> RuntimeStatus:
        ...


@dataclass
class FakeTemporalWorkflow:
    workflow_id: str
    run_id: str
    spec: dict[str, Any]
    status: str = "submitted"
    signal_event_ids: list[str] = field(default_factory=list)


class FakeTemporalClient:
    """Deterministic local fake for the Temporal client boundary.

    This fake proves that TemporalRuntimeDriver can delegate orchestration
    operations through a client interface without requiring temporalio or a
    Temporal server.

    It does not write CTL records, mutate domain state, or own StateView truth.
    """

    def __init__(self) -> None:
        self.workflows: dict[str, FakeTemporalWorkflow] = {}

    async def start_workflow(self, spec: dict[str, Any]) -> WorkflowHandle:
        workflow_id = str(spec["workflow_id"])
        run_id = str(spec.get("run_id") or f"fake-run:{workflow_id}")

        self.workflows[workflow_id] = FakeTemporalWorkflow(
            workflow_id=workflow_id,
            run_id=run_id,
            spec=dict(spec),
            status="submitted",
        )

        return WorkflowHandle(
            workflow_id=workflow_id,
            run_id=run_id,
            status="submitted",
        )

    async def signal_workflow(self, workflow_id: str, event: ExternalEvent) -> None:
        workflow = self._get_workflow(workflow_id)

        workflow.status = "signaled"
        workflow.signal_event_ids.append(event.event_id)

    async def query_workflow(self, workflow_id: str) -> RuntimeStatus:
        workflow = self._get_workflow(workflow_id)

        return RuntimeStatus(
            workflow_id=workflow.workflow_id,
            status=workflow.status,
            detail={
                "spec": dict(workflow.spec),
                "run_id": workflow.run_id,
                "events": list(workflow.signal_event_ids),
                "runtime": "fake_temporal",
            },
        )

    def _get_workflow(self, workflow_id: str) -> FakeTemporalWorkflow:
        if workflow_id not in self.workflows:
            raise KeyError(f"unknown workflow_id: {workflow_id}")

        return self.workflows[workflow_id]