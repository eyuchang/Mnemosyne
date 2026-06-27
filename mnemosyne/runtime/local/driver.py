from __future__ import annotations

import uuid

from mnemosyne.core.models import ExternalEvent, RuntimeStatus, WorkflowHandle


class LocalRuntimeDriver:
    """Deterministic dev/test RuntimeDriver.

    It does not orchestrate agents yet; Phase 0 uses it to prove the RuntimeDriver boundary.
    """

    def __init__(self) -> None:
        self._statuses: dict[str, RuntimeStatus] = {}

    async def submit_workflow(self, spec: dict) -> WorkflowHandle:
        workflow_id = spec.get("workflow_id") or f"wf:{uuid.uuid4()}"
        handle = WorkflowHandle(workflow_id=workflow_id, run_id="local-run-1", status="submitted")
        self._statuses[workflow_id] = RuntimeStatus(workflow_id=workflow_id, status="submitted", detail={"spec": spec})
        return handle

    async def signal_disruption(self, workflow_id: str, event: ExternalEvent) -> None:
        current = self._statuses.get(workflow_id, RuntimeStatus(workflow_id=workflow_id, status="unknown"))
        detail = dict(current.detail)
        detail.setdefault("events", []).append(event.event_id)
        self._statuses[workflow_id] = RuntimeStatus(workflow_id=workflow_id, status="signaled", detail=detail)

    async def query_status(self, workflow_id: str) -> RuntimeStatus:
        return self._statuses.get(workflow_id, RuntimeStatus(workflow_id=workflow_id, status="unknown"))
