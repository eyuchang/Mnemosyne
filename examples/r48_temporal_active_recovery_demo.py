from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from pprint import pprint

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mnemosyne.core.commitments import (
    ActiveCommitment,
    active_commitment_index_from_store,
    build_commitment_fsm_registry,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import ctl_record_from_transition_candidate
from mnemosyne.runtime.temporal import (
    FakeTemporalClient,
    TemporalRuntimeDriver,
    plan_validate_and_commit_active_recovery_activity,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r48-demo"
W = "workflow:r48-demo"
G = "tx:r48-demo"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def domain_record(*, rid: str, version: int, state_before: str, state_after: str) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        op_id=rid,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        binding_id=None,
        eid=DOMAIN_EID,
        fsm=DOMAIN_FSM,
        version=version,
        state_before=state_before,
        state_after=state_after,
        action_type="domain_transition",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_transition"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="demo.validator",
        validator_version="1.0",
        timestamp=FT,
    )


def proposal_provider(_commitment, _context):
    return [
        RecoveryProposal(
            proposal_ref="proposal:r48-temporal-repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
            rationale="Repair stale dependent entity through Temporal activity boundary.",
        )
    ]


async def seed_domain_and_fired_commitment(store: SQLiteStore) -> None:
    await store.commit_batch(
        batch("batch:domain-initial", []),
        [
            domain_record(
                rid="rid:domain-initial",
                version=1,
                state_before="none",
                state_after="stale",
            )
        ],
    )

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Temporal active recovery demo commitment.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        workflow_id=W,
        rid="rid:commitment-register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:commitment-fire",
    )

    await store.commit_batch(
        batch("batch:commitment-fire", [register, fire]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )


async def run_demo() -> dict:
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    client = FakeTemporalClient()
    runtime = TemporalRuntimeDriver(
        namespace="default",
        task_queue="mnemosyne-r48",
        client=client,
    )

    handle = await runtime.submit_workflow(
        {
            "workflow_id": W,
            "tenant_id": T,
            "app_id": "mnemosyne",
            "entity_id": "commitment:c1",
        }
    )

    runtime_status_before = await runtime.query_status(W)
    domain_before_activity = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    validator = Validator(build_commitment_fsm_registry())

    first_activity = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:r48-temporal-active-recovery:first",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    index_after_first = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    domain_after_first = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    second_activity = await plan_validate_and_commit_active_recovery_activity(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:r48-temporal-active-recovery:retry",
        workflow_id=W,
        store=store,
        validator=validator,
        proposal_provider=proposal_provider,
    )

    runtime_status_after = await runtime.query_status(W)
    domain_after_second = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    return {
        "workflow_id": handle.workflow_id,
        "runtime_status_before": runtime_status_before.status,
        "runtime_status_after": runtime_status_after.status,
        "first_activity_committed_rids": first_activity.committed_rids,
        "first_activity_committed_fsms": first_activity.committed_fsms,
        "first_activity_actions": first_activity.committed_action_types,
        "first_activity_validation_ok": first_activity.validation_ok,
        "first_activity_commitment_statuses": first_activity.commitment_statuses,
        "second_activity_committed_rids": second_activity.committed_rids,
        "second_activity_skipped": second_activity.skipped,
        "second_activity_commitment_statuses": second_activity.commitment_statuses,
        "commitment_status_after_first": index_after_first.status("c1").value,
        "domain_state_before_activity": domain_before_activity.state,
        "domain_state_after_first": domain_after_first.state,
        "domain_state_after_second": domain_after_second.state,
        "domain_version_after_second": domain_after_second.version,
        "domain_effective_records_after_second": domain_after_second.effective_records,
        "runtime_exposes_commit_batch": hasattr(runtime, "commit_batch"),
        "runtime_exposes_get_state_view": hasattr(runtime, "get_state_view"),
    }


def main() -> None:
    pprint(asyncio.run(run_demo()))


if __name__ == "__main__":
    main()
