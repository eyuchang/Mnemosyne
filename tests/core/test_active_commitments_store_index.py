from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    active_commitment_index_from_store,
    make_discharge_commitment_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:commitment-store-index"
W = "workflow:commitment-store-index"
G = "tx:commitment-store-index"
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


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


@pytest.mark.asyncio
async def test_store_backed_index_reconstructs_live_commitments():
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )

    await store.commit_batch(
        batch("batch:index-live", [register, fire]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
        ],
    )

    index = await active_commitment_index_from_store(store, tenant_id=T)

    assert index.status("c1") == CommitmentStatus.FIRED
    assert index.is_live("c1")
    assert index.live_commitment_ids() == ["c1"]
    assert index.get("c1") == commitment


@pytest.mark.asyncio
async def test_store_backed_index_excludes_discharged_commitments():
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    discharge = make_discharge_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:discharge",
    )

    await store.commit_batch(
        batch("batch:index-discharged", [register, fire, discharge]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(discharge, version=3),
        ],
    )

    index = await active_commitment_index_from_store(store, tenant_id=T)

    assert index.status("c1") == CommitmentStatus.DISCHARGED
    assert not index.is_live("c1")
    assert index.live_commitment_ids() == []


@pytest.mark.asyncio
async def test_store_backed_index_can_filter_by_workflow():
    store = SQLiteStore()

    c1 = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Workflow one.",
    )
    c2 = ActiveCommitment(
        commitment_id="c2",
        commitment_type="dependency_guard",
        description="Workflow two.",
    )

    r1 = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c1,
        workflow_id="workflow:one",
        rid="rid:register:c1",
    )
    r2 = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c2,
        workflow_id="workflow:two",
        rid="rid:register:c2",
    )

    await store.commit_batch(
        CommitBatch(
            batch_id="batch:index-workflow",
            tenant_id=T,
            workflow_id=None,
            tx_group_id=G,
            candidates=[r1, r2],
        ),
        [
            record_from_candidate(r1, version=1),
            record_from_candidate(r2, version=1),
        ],
    )

    index_one = await active_commitment_index_from_store(
        store,
        tenant_id=T,
        workflow_id="workflow:one",
    )
    index_two = await active_commitment_index_from_store(
        store,
        tenant_id=T,
        workflow_id="workflow:two",
    )

    assert index_one.live_commitment_ids() == ["c1"]
    assert index_two.live_commitment_ids() == ["c2"]
