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
    CommitmentStatus,
    active_commitment_index_from_store,
    make_commitment_admitted_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import (
    RecoveryContext,
    RecoveryPolicy,
    RecoveryProposal,
    plan_recovery_from_store,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r45-demo"
W = "workflow:r45-demo"
G = "tx:r45-demo"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def record_from_candidate(candidate: TransitionCandidate, *, version: int) -> CTLRecord:
    return CTLRecord(
        rid=candidate.rid,
        op_id=candidate.op_id or candidate.rid,
        tenant_id=candidate.tenant_id,
        tx_group_id=candidate.tx_group_id,
        workflow_id=candidate.workflow_id,
        binding_id=candidate.binding_id,
        eid=candidate.eid,
        fsm=candidate.fsm,
        version=version,
        state_before=candidate.state_before,
        state_after=candidate.state_after,
        action_type=candidate.action_type,
        triggers=list(candidate.triggers),
        dependencies=list(candidate.dependencies),
        metadata=dict(candidate.metadata),
        extension=dict(candidate.extension),
        app_id=candidate.app_id,
        app_version=candidate.app_version,
        schema_id=candidate.schema_id,
        schema_version=candidate.schema_version,
        fsm_version=candidate.fsm_version,
        policy_id=candidate.policy_id,
        policy_version=candidate.policy_version,
        validator_id=candidate.validator_id,
        validator_version=candidate.validator_version,
        timestamp=FT,
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
        action_type="domain_repair",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_repair"},
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


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def proposal_provider(_commitment: ActiveCommitment, _context: RecoveryContext):
    return [
        RecoveryProposal(
            proposal_ref="proposal:bad-out-of-scope",
            proposal_scope={"entity_id": "domain:outside"},
        ),
        RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        ),
    ]


async def run_demo() -> dict:
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity when upstream evidence changes.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )

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
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
        ],
    )

    plan = await plan_recovery_from_store(
        store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        proposal_provider=proposal_provider,
        policy=RecoveryPolicy(max_depth=2, max_attempts=3),
        contexts={"c1": RecoveryContext(commitment_id="c1")},
    )

    plan_records = [
        record_from_candidate(candidate, version=version)
        for version, candidate in enumerate(plan.candidates, start=3)
    ]

    await store.commit_batch(
        batch("batch:recovery-plan", plan.candidates),
        plan_records,
    )

    mid_domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    mid_index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)

    admitted_domain = domain_record(
        rid="rid:domain-repair",
        version=2,
        state_before="stale",
        state_after="repaired",
    )
    admitted = make_commitment_admitted_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        admitted_record_ids=["rid:domain-repair"],
        workflow_id=W,
        rid="rid:commitment-admitted",
    )

    await store.commit_batch(
        batch("batch:admit-repair", [admitted]),
        [
            admitted_domain,
            record_from_candidate(admitted, version=3 + len(plan.candidates)),
        ],
    )

    final_domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    final_index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)

    return {
        "plan_candidate_actions": [candidate.action_type for candidate in plan.candidates],
        "mid_domain_state": mid_domain_view.state,
        "mid_commitment_status": mid_index.status("c1").value,
        "final_domain_state": final_domain_view.state,
        "final_domain_effective_records": final_domain_view.effective_records,
        "final_commitment_status": final_index.status("c1").value,
        "final_live_commitments": final_index.live_commitment_ids(),
    }


def main() -> None:
    result = asyncio.run(run_demo())
    pprint(result)


if __name__ == "__main__":
    main()
