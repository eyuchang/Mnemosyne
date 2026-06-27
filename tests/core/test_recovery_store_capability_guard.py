from __future__ import annotations

import pytest

from mnemosyne.core.protocols.recovery_store import (
    RECOVERY_READ_METHODS,
    RECOVERY_STORE_REQUIRED_METHODS,
    RECOVERY_WRITE_METHODS,
    RecoveryStoreCapabilityError,
    missing_recovery_store_methods,
    require_recovery_store,
)
from mnemosyne.store.sqlite.store import SQLiteStore


class EmptyStore:
    pass


class ReadOnlyRecoveryStore:
    async def get_record(self, tenant_id: str, rid: str):
        return None

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: str):
        return []

    async def get_full_entity_history(self, tenant_id: str, eid: str, fsm: str):
        return []

    async def get_state_view(self, tenant_id: str, eid: str, fsm: str):
        return None

    async def get_by_op_id(self, tenant_id: str, op_id: str):
        return None


def test_sqlite_store_passes_recovery_store_capability_guard():
    store = SQLiteStore()

    assert missing_recovery_store_methods(store) == ()
    assert require_recovery_store(store) is store


def test_empty_store_fails_closed_with_all_required_methods_missing():
    store = EmptyStore()

    assert missing_recovery_store_methods(store) == RECOVERY_STORE_REQUIRED_METHODS

    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        require_recovery_store(store)

    message = str(exc.value)
    assert "RecoveryStore capability boundary" in message
    for method in RECOVERY_STORE_REQUIRED_METHODS:
        assert method in message


def test_read_only_store_can_satisfy_read_boundary_but_not_write_boundary():
    store = ReadOnlyRecoveryStore()

    assert missing_recovery_store_methods(store, RECOVERY_READ_METHODS) == ()
    assert missing_recovery_store_methods(store, RECOVERY_STORE_REQUIRED_METHODS) == RECOVERY_WRITE_METHODS

    assert require_recovery_store(store, required_methods=RECOVERY_READ_METHODS) is store

    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        require_recovery_store(store)

    assert "commit_batch" in str(exc.value)
