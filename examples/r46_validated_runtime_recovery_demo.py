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
    build_commitment_fsm_registry,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryProposal
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import (
    LocalActiveRecoveryExecutor,
    ctl_record_from_transition_candidate,
)
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r46-demo"
W = "workflow:r46-demo"
G = "tx:r46-demo"
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
            proposal_ref="proposal:runtime-repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        )
    ]


async def run_demo() -> dict:
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Validated runtime recovery for scoped dependent entity.",
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
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )

    executor = LocalActiveRecoveryExecutor(store)
    validator = Validator(build_commitment_fsm_registry())

    execution = await executor.plan_validate_and_commit(
        tenant_id=T,
        tx_group_id=G,
        batch_id="batch:validated-runtime-recovery",
        workflow_id=W,
        proposal_provider=proposal_provider,
        validator=validator,
    )

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    return {
        "validation_ok": [result.ok for result in execution.validation_results],
        "committed_actions": [record.action_type for record in execution.committed],
        "committed_fsms": [record.fsm for record in execution.committed],
        "commitment_status": index.status("c1").value,
        "domain_state": domain_view.state,
        "domain_version": domain_view.version,
        "domain_effective_records": domain_view.effective_records,
    }


def main() -> None:
    pprint(asyncio.run(run_demo()))


if __name__ == "__main__":
    main()
