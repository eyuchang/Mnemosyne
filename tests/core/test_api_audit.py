from __future__ import annotations

import pytest

from mnemosyne.api.audit import (
    audit_active_commitments,
    audit_commitment_lineage,
    audit_recovery_lineage,
    list_unresolved_commitments,
)
from mnemosyne.api.commitments import (
    admit_active_commitment,
    fire_active_commitment,
    register_active_commitment,
)
from mnemosyne.api.proposal_packages import (
    create_recovery_proposal_package,
    emit_package_backed_proposal,
)
from mnemosyne.core.commitments import ActiveCommitment, CommitmentStatus
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r50-api-audit"
W = "workflow:r50-api-audit"
G = "tx:r50-api-audit"
DOMAIN_EID = "domain:entity:1"


def commitment(commitment_id: str = "c1") -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id=commitment_id,
        commitment_type="dependency_guard",
        description=f"Audit API commitment {commitment_id}.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


async def seed_package_proposed_commitment(store: SQLiteStore) -> None:
    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment("c1"),
        rid="rid:audit-register",
        batch_id="batch:audit-register",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        reason="dependency_changed",
        rid="rid:audit-fire",
        batch_id="batch:audit-fire",
    )

    package = create_recovery_proposal_package(
        package_id="pkg:c1:audit-repair:1",
        commitment_id="c1",
        proposal_ref="proposal:audit-repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        rationale="Audit recovery package.",
        created_from_record_id="rid:audit-fire",
    )

    await emit_package_backed_proposal(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        package=package,
        commitment=commitment("c1"),
        rid="rid:audit-proposal",
        batch_id="batch:audit-proposal",
    )


@pytest.mark.asyncio
async def test_audit_api_reports_active_commitment_status_and_record_counts():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert len(rows) == 1

    row = rows[0]
    assert row.commitment_id == "c1"
    assert row.commitment_type == "dependency_guard"
    assert row.status == CommitmentStatus.PROPOSED.value
    assert row.is_unresolved
    assert row.record_count == 3
    assert row.first_record_id == "rid:audit-register"
    assert row.last_record_id == "rid:audit-proposal"
    assert row.last_action_type == "commitment_proposal_emitted"


@pytest.mark.asyncio
async def test_audit_api_lists_unresolved_commitments():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    report = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert report.tenant_id == T
    assert report.workflow_id == W
    assert report.count == 1
    assert report.commitment_ids == ["c1"]


@pytest.mark.asyncio
async def test_audit_api_commitment_lineage_returns_ordered_ctl_events():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    rows = await audit_commitment_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )

    assert [row.record_id for row in rows] == [
        "rid:audit-register",
        "rid:audit-fire",
        "rid:audit-proposal",
    ]
    assert [row.action_type for row in rows] == [
        "commitment_registered",
        "commitment_fired",
        "commitment_proposal_emitted",
    ]
    assert rows[2].payload["proposal_ref"] == "proposal:audit-repair:1"


@pytest.mark.asyncio
async def test_audit_api_recovery_lineage_extracts_package_reference():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    rows = await audit_recovery_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )

    assert len(rows) == 1

    row = rows[0]
    assert row.commitment_id == "c1"
    assert row.record_id == "rid:audit-proposal"
    assert row.action_type == "commitment_proposal_emitted"
    assert row.proposal_ref == "proposal:audit-repair:1"
    assert row.package_id == "pkg:c1:audit-repair:1"


@pytest.mark.asyncio
async def test_audit_api_excludes_resolved_commitments_from_unresolved_report():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    await admit_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        admitted_record_ids=["rid:domain-admitted"],
        rid="rid:audit-admitted",
        batch_id="batch:audit-admitted",
    )

    report = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    assert report.count == 0
    assert report.commitment_ids == []

    rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    assert rows[0].status == CommitmentStatus.ADMITTED.value
    assert not rows[0].is_unresolved


@pytest.mark.asyncio
async def test_audit_api_is_read_only():
    store = SQLiteStore()
    await seed_package_proposed_commitment(store)

    before = store.conn.execute(
        "SELECT COUNT(*) FROM ctl_records WHERE tenant_id = ?",
        (T,),
    ).fetchone()[0]

    await audit_active_commitments(store=store, tenant_id=T, workflow_id=W)
    await list_unresolved_commitments(store=store, tenant_id=T, workflow_id=W)
    await audit_commitment_lineage(store=store, tenant_id=T, workflow_id=W, commitment_id="c1")
    await audit_recovery_lineage(store=store, tenant_id=T, workflow_id=W, commitment_id="c1")

    after = store.conn.execute(
        "SELECT COUNT(*) FROM ctl_records WHERE tenant_id = ?",
        (T,),
    ).fetchone()[0]

    assert after == before
