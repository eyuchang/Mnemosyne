from __future__ import annotations

import inspect

from mnemosyne.core.protocols.recovery_store import (
    RECOVERY_READ_METHODS,
    RECOVERY_STORE_REQUIRED_METHODS,
    RECOVERY_WRITE_METHODS,
    RecoveryReadStore,
    RecoveryStore,
    RecoveryWriteStore,
)
from mnemosyne.store.sqlite.store import SQLiteStore


def test_sqlite_store_satisfies_recovery_store_protocols():
    store = SQLiteStore()

    assert isinstance(store, RecoveryReadStore)
    assert isinstance(store, RecoveryWriteStore)
    assert isinstance(store, RecoveryStore)


def test_recovery_store_protocol_surface_is_explicit_and_minimal():
    assert RECOVERY_READ_METHODS == (
        "get_record",
        "get_entity_history",
        "get_full_entity_history",
        "get_state_view",
        "get_by_op_id",
    )
    assert RECOVERY_WRITE_METHODS == ("commit_batch",)
    assert RECOVERY_STORE_REQUIRED_METHODS == RECOVERY_READ_METHODS + RECOVERY_WRITE_METHODS


def test_sqlite_store_exposes_required_recovery_methods():
    missing = [
        method
        for method in RECOVERY_STORE_REQUIRED_METHODS
        if not hasattr(SQLiteStore, method)
    ]

    assert missing == []

    for method in RECOVERY_STORE_REQUIRED_METHODS:
        attr = getattr(SQLiteStore, method)
        assert inspect.isfunction(attr)
