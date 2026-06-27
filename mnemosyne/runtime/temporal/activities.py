# File: mnemosyne/runtime/temporal/activities.py
#
# Purpose:
#   Define Temporal-style activity boundaries for durable Mnemosyne operations.
#
# Stage:
#   Stage 1.4 introduces activity-like functions without importing temporalio.
#
# Contract:
#   Temporal workflow/runtime code orchestrates only.
#   Durable Store/CTL writes happen through activity-like boundaries.
#
# Source-of-truth rule:
#   CTL/store remains domain truth. Temporal remains orchestration.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mnemosyne.core.models import CTLRecord, CommitBatch, StateView


@dataclass(frozen=True)
class CommitBatchActivityResult:
    batch_id: str
    tenant_id: str
    workflow_id: str | None
    committed_rids: list[str]
    state_views: list[StateView]


def _unique_entity_keys(records: list[CTLRecord]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    keys: list[tuple[str, str, str]] = []

    for record in records:
        key = (record.tenant_id, record.eid, record.fsm)

        if key not in seen:
            seen.add(key)
            keys.append(key)

    return keys


async def validate_and_commit_batch_activity(
    *,
    batch: CommitBatch,
    store: Any,
    validator: Any,
) -> CommitBatchActivityResult:
    """Validate and commit a CommitBatch through the durable Store path.

    This function is intentionally Temporal-SDK-free.

    A future temporalio activity can call this boundary from inside an actual
    Temporal activity implementation.

    Behavior:
        1. Validate the batch.
        2. Convert candidates to CTL records.
        3. Commit through Store.commit_batch(...).
        4. Return committed record ids and resulting StateViews.

    Important:
        This is the correct place for durable CTL/store writes.
        Workflow orchestration code must not bypass this boundary.
    """
    validation_result = await validator.validate_batch(batch, store)

    if not validation_result.ok:
        codes = [error.code for error in validation_result.errors]
        raise ValueError(f"batch validation failed: {codes}")

    records = await validator.records_from_batch(batch, store)
    committed_records = await store.commit_batch(batch, records)

    state_views: list[StateView] = []

    for tenant_id, eid, fsm in _unique_entity_keys(committed_records):
        state_views.append(await store.get_state_view(tenant_id, eid, fsm))

    return CommitBatchActivityResult(
        batch_id=batch.batch_id,
        tenant_id=batch.tenant_id,
        workflow_id=batch.workflow_id,
        committed_rids=[record.rid for record in committed_records],
        state_views=state_views,
    )