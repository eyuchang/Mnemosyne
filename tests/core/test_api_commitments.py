from __future__ import annotations

import pytest

from mnemosyne.api.commitments import (
    fire_active_commitment,
    get_active_commitment_status,
    list_live_active_commitment_ids,
    list_live_active_commitments,
    register_active_commitment,
)
from mnemosyne.core.commitments import ActiveCommitment, CommitmentStatus
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r50-api-commitments"
W = "workflow:r50-api-commitments"
G = "tx:r50-api-commitments"


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Product-facing API commitment.",
        dependency_scope={"entity_id": "domain:entity:1"},
    )


@pytest.mark.asyncio
async def test_commitment_api_registers_active_commitment():
    store = SQLiteStore()

    result = await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    assert result.ok
    assert result.committed_rids == ["rid:api-register"]
    assert result.committed_action_types == ["commitment_registered"]
    assert result.committed_only_commitment_fsm

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )

    assert status == CommitmentStatus.LIVE


@pytest.mark.asyncio
async def test_commitment_api_registers_and_fires_active_commitment():
    store = SQLiteStore()

    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    fire = await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        reason="external_dependency_changed",
        rid="rid:api-fire",
        batch_id="batch:api-fire",
    )

    assert fire.ok
    assert fire.committed_rids == ["rid:api-fire"]
    assert fire.committed_action_types == ["commitment_fired"]
    assert fire.committed_only_commitment_fsm

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )

    assert status == CommitmentStatus.FIRED


@pytest.mark.asyncio
async def test_commitment_api_fails_closed_on_invalid_fire():
    store = SQLiteStore()

    fire = await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        rid="rid:api-invalid-fire",
        batch_id="batch:api-invalid-fire",
    )

    assert not fire.ok
    assert fire.committed == []
    assert fire.records == []
    assert not fire.validation.ok

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )

    assert status is None


@pytest.mark.asyncio
async def test_commitment_api_lists_live_commitments():
    store = SQLiteStore()

    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    ids = await list_live_active_commitment_ids(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    commitments = await list_live_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert ids == ["c1"]
    assert [c.commitment_id for c in commitments] == ["c1"]
    assert commitments[0].description == "Product-facing API commitment."
