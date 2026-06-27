# File: mnemosyne/runtime/temporal/driver.py
#
# Purpose:
#   Define the Temporal runtime adapter boundary.
#
# Stage:
#   Stage 1.3 supports a fake Temporal client for deterministic local tests
#   while preserving the optional temporalio dependency guard for real usage.
#
# Contract:
#   - TemporalRuntimeDriver exposes the RuntimeDriver API shape.
#   - Without an injected client, real Temporal operations remain guarded.
#   - With an injected fake client, the driver can be tested locally.
#   - Temporal orchestrates workflows but does not become domain truth.

from __future__ import annotations

from typing import Any

from mnemosyne.core.models import ExternalEvent, RuntimeStatus, WorkflowHandle
from mnemosyne.runtime.temporal.client import TemporalClientLike
from mnemosyne.runtime.temporal.dependency import require_temporal_sdk


class TemporalRuntimeDriver:
    """Temporal runtime adapter.

    The driver delegates orchestration to a Temporal client boundary.

    In Stage 1.3, the supported local client is FakeTemporalClient.
    A future stage will provide a temporalio-backed implementation.

    Domain truth remains in:
        - CTL
        - event log
        - event inbox
        - StateView
        - outbox
    """

    def __init__(
        self,
        *,
        namespace: str | None = None,
        task_queue: str | None = None,
        client: TemporalClientLike | None = None,
    ) -> None:
        self.namespace = namespace
        self.task_queue = task_queue
        self.client = client

    def _require_ready_temporal_driver(self, method_name: str) -> None:
        """Check Temporal dependency, then report that real integration is pending.

        Behavior:
            If temporalio is not installed:
                require_temporal_sdk() raises RuntimeError with install guidance.

            If temporalio is installed:
                this method raises NotImplementedError because real Temporal
                client/workflow integration has not been added yet.

            If a fake/injected client is present:
                this method is not used.
        """
        require_temporal_sdk()

        raise NotImplementedError(
            f"TemporalRuntimeDriver.{method_name}(...) requires the Stage 1.4 "
            "Temporal SDK integration. The optional Temporal dependency is present, "
            "but the real temporalio-backed runtime adapter is not implemented yet."
        )

    async def submit_workflow(self, spec: dict[str, Any]) -> WorkflowHandle:
        """Submit a workflow for Temporal orchestration.

        With an injected client:
            delegate to client.start_workflow(...).

        Without an injected client:
            preserve guarded-stub behavior.

        Source-of-truth rule:
            Starting a Temporal workflow does not create committed domain truth.
            Domain truth must still be committed through the Store/CTL path.
        """
        if self.client is None:
            self._require_ready_temporal_driver("submit_workflow")

        return await self.client.start_workflow(spec)

    async def signal_disruption(self, workflow_id: str, event: ExternalEvent) -> None:
        """Signal an external event into a Temporal workflow.

        With an injected client:
            delegate to client.signal_workflow(...).

        Without an injected client:
            preserve guarded-stub behavior.

        Source-of-truth rule:
            Signaling Temporal is orchestration. External events still need
            durable inbox/event-log/CTL handling as appropriate.
        """
        if self.client is None:
            self._require_ready_temporal_driver("signal_disruption")

        await self.client.signal_workflow(workflow_id, event)

    async def query_status(self, workflow_id: str) -> RuntimeStatus:
        """Query Temporal workflow orchestration status.

        With an injected client:
            delegate to client.query_workflow(...).

        Without an injected client:
            preserve guarded-stub behavior.

        Source-of-truth rule:
            Runtime status is not domain state. Current domain state is read
            from Store.get_state_view(...).
        """
        if self.client is None:
            self._require_ready_temporal_driver("query_status")

        return await self.client.query_workflow(workflow_id)