from __future__ import annotations

import pytest

from mnemosyne.core.store_capabilities import STORE_SCHEMA_VERSION
from mnemosyne.core.store_conformance import (
    RecoveryStoreConformanceCase,
    observe_recovery_store_conformance,
    recovery_store_conformance_observation_to_dict,
)
from mnemosyne.store.sqlite.store import SQLiteStore


@pytest.mark.asyncio
async def test_sqlite_store_passes_recovery_store_conformance_contract():
    observation = await observe_recovery_store_conformance(
        SQLiteStore(),
        RecoveryStoreConformanceCase(store_name="SQLiteStore"),
    )

    assert observation.passed is True
    assert observation.details["event_ids"] == [
        "conformance-event-1",
        "conformance-event-2",
    ]
    assert observation.details["replay_event_ids"] == [
        "conformance-event-1",
        "conformance-event-2",
    ]
    assert observation.details["duplicate_result_event_id"] == "conformance-event-1"


@pytest.mark.asyncio
async def test_file_backed_sqlite_store_passes_restart_persistence_expectation(tmp_path):
    observation = await observe_recovery_store_conformance(
        SQLiteStore(tmp_path / "conformance.sqlite"),
        RecoveryStoreConformanceCase(
            store_name="SQLiteStore",
            expects_restart_persistence=True,
        ),
    )

    assert observation.passed is True
    assert observation.details["supports_restart_persistence"] is True


@pytest.mark.asyncio
async def test_recovery_store_conformance_observation_serializes_to_dict():
    observation = await observe_recovery_store_conformance(
        SQLiteStore(),
        RecoveryStoreConformanceCase(store_name="SQLiteStore"),
    )

    as_dict = recovery_store_conformance_observation_to_dict(observation)

    assert as_dict["passed"] is True
    assert as_dict["case"]["store_name"] == "SQLiteStore"
    assert as_dict["details"]["schema_version"] == STORE_SCHEMA_VERSION
    assert as_dict["checks"]["idempotent_duplicate_retry"] is True


@pytest.mark.asyncio
async def test_recovery_store_conformance_detects_schema_version_mismatch():
    observation = await observe_recovery_store_conformance(
        SQLiteStore(),
        RecoveryStoreConformanceCase(
            store_name="SQLiteStore",
            expected_schema_version="wrong-version",
        ),
    )

    assert observation.passed is False
    assert observation.checks["schema_version_matches"] is False
    assert observation.checks["idempotent_duplicate_retry"] is True
