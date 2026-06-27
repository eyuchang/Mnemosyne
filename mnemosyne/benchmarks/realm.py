# File: mnemosyne/benchmarks/realm.py
#
# Purpose:
#   Translate a small REALM-style benchmark case into Mnemosyne CommitBatch
#   objects, then collect simple CTL/StateView metrics.
#
# Stage:
#   Stage 1.2 keeps this local and deterministic:
#
#   REALM-style case
#   -> CommitBatch
#   -> Validator
#   -> Store
#   -> StateView
#   -> metrics
#
# Rule:
#   REALM provides scenarios. Mnemosyne owns transactional memory.

from __future__ import annotations

from mnemosyne.benchmarks.models import BenchmarkCase, BenchmarkMetrics
from mnemosyne.core.models import CommitBatch, OutboxIntent, TransitionCandidate


def _rid_for_step(case: BenchmarkCase, step_id: str) -> str:
    return f"realm-{case.case_id}-{step_id}"


def _outbox_id_for_step(case: BenchmarkCase, step_id: str) -> str:
    return f"outbox-realm-{case.case_id}-{step_id}"


def realm_case_to_commit_batches(case: BenchmarkCase) -> list[CommitBatch]:
    step_id_to_rid = {
        step.step_id: _rid_for_step(case, step.step_id)
        for step in case.steps
    }

    batches: list[CommitBatch] = []

    for index, step in enumerate(case.steps, start=1):
        rid = step_id_to_rid[step.step_id]
        dependencies = [
            step_id_to_rid[dependency_step_id]
            for dependency_step_id in step.depends_on
        ]
        compensates = [
            step_id_to_rid[compensated_step_id]
            for compensated_step_id in step.compensates
        ]

        metadata = {
            "benchmark": "realm",
            "case_id": case.case_id,
            "step_id": step.step_id,
            "step_index": index,
        }

        if compensates:
            metadata["compensates"] = compensates

        candidate = TransitionCandidate(
            rid=rid,
            tenant_id=case.tenant_id,
            tx_group_id=f"realm-{case.case_id}-group-{index:03d}",
            workflow_id=case.workflow_id,
            binding_id=case.binding_id,
            eid=case.entity_id,
            fsm=case.fsm,
            state_before=step.state_before,
            state_after=step.state_after,
            action_type=step.action_type,
            dependencies=dependencies,
            metadata=metadata,
            extension={
                "attrs_after": {
                    **step.attrs_after,
                    "benchmark": "realm",
                    "case_id": case.case_id,
                    "step_id": step.step_id,
                }
            },
            app_id=case.app_id,
            schema_id=case.schema_id,
        )

        outbox_intents = []

        if step.emit_outbox:
            outbox_intents.append(
                OutboxIntent(
                    outbox_id=_outbox_id_for_step(case, step.step_id),
                    tenant_id=case.tenant_id,
                    provider=step.outbox_provider,
                    effect_type=step.outbox_effect_type,
                    payload={
                        "benchmark": "realm",
                        "case_id": case.case_id,
                        "step_id": step.step_id,
                        "entity_id": case.entity_id,
                    },
                    provider_idempotency_key=(
                        f"realm:{case.case_id}:{step.step_id}:{step.outbox_effect_type}"
                    ),
                    workflow_id=case.workflow_id,
                    binding_id=case.binding_id,
                )
            )

        batches.append(
            CommitBatch(
                batch_id=f"realm-{case.case_id}-batch-{index:03d}",
                tenant_id=case.tenant_id,
                workflow_id=case.workflow_id,
                tx_group_id=f"realm-{case.case_id}-group-{index:03d}",
                candidates=[candidate],
                outbox_intents=outbox_intents,
            )
        )

    return batches


async def collect_realm_case_metrics(store, case: BenchmarkCase) -> BenchmarkMetrics:
    view = await store.get_state_view(case.tenant_id, case.entity_id, case.fsm)

    total_records = store.conn.execute(
        """
        SELECT COUNT(*)
        FROM ctl_records
        WHERE tenant_id=? AND workflow_id=? AND eid=?
        """,
        (case.tenant_id, case.workflow_id, case.entity_id),
    ).fetchone()[0]

    outbox_rows = store.conn.execute(
        """
        SELECT COUNT(*)
        FROM outbox
        WHERE tenant_id=? AND workflow_id=?
        """,
        (case.tenant_id, case.workflow_id),
    ).fetchone()[0]

    effective_records = len(view.effective_records)

    return BenchmarkMetrics(
        case_id=case.case_id,
        tenant_id=case.tenant_id,
        workflow_id=case.workflow_id,
        entity_id=case.entity_id,
        total_records=total_records,
        effective_records=effective_records,
        ineffective_records=total_records - effective_records,
        outbox_rows=outbox_rows,
        final_state=view.state,
        state_version=view.version,
    )