from __future__ import annotations

import pytest

from mnemosyne.api.audit import (
    audit_active_commitments,
    audit_recovery_lineage,
    list_unresolved_commitments,
)
from mnemosyne.api.commitments import admit_active_commitment
from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError


class EmptyStore:
    pass


@pytest.mark.asyncio
async def test_audit_active_commitments_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        await audit_active_commitments(
            store=EmptyStore(),
            tenant_id="tenant",
            workflow_id="workflow",
        )

    assert "RecoveryStore capability boundary" in str(exc.value)


@pytest.mark.asyncio
async def test_list_unresolved_commitments_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        await list_unresolved_commitments(
            store=EmptyStore(),
            tenant_id="tenant",
            workflow_id="workflow",
        )

    assert "RecoveryStore capability boundary" in str(exc.value)


@pytest.mark.asyncio
async def test_audit_recovery_lineage_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        await audit_recovery_lineage(
            store=EmptyStore(),
            tenant_id="tenant",
            workflow_id="workflow",
        )

    assert "RecoveryStore capability boundary" in str(exc.value)


@pytest.mark.asyncio
async def test_admit_active_commitment_fails_closed_without_recovery_store():
    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        await admit_active_commitment(
            store=EmptyStore(),
            tenant_id="tenant",
            tx_group_id="tx",
            commitment_id="commitment",
            admitted_record_ids=[],
            workflow_id="workflow",
        )

    assert "RecoveryStore capability boundary" in str(exc.value)
    assert "commit_batch" in str(exc.value)
