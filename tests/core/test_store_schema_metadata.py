from __future__ import annotations

import pytest

from mnemosyne.core.store_capabilities import (
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
    StoreCapabilityReport,
    store_capability_report_to_dict,
)
from mnemosyne.store.sqlite.store import SQLiteStore


@pytest.mark.asyncio
async def test_sqlite_store_records_schema_metadata():
    store = SQLiteStore()

    assert await store.get_store_schema_version() == STORE_SCHEMA_VERSION

    row = store.conn.execute(
        """
        SELECT schema_id, schema_version, store_type
        FROM store_schema_metadata
        WHERE schema_id = ?
        """,
        (STORE_SCHEMA_ID,),
    ).fetchone()

    assert row["schema_id"] == STORE_SCHEMA_ID
    assert row["schema_version"] == STORE_SCHEMA_VERSION
    assert row["store_type"] == "SQLiteStore"


@pytest.mark.asyncio
async def test_sqlite_store_capability_report_is_explicit_for_r75():
    store = SQLiteStore()

    report = await store.get_store_capability_report()

    assert isinstance(report, StoreCapabilityReport)
    assert report.store_type == "SQLiteStore"
    assert report.schema_id == STORE_SCHEMA_ID
    assert report.schema_version == STORE_SCHEMA_VERSION
    assert report.durable_recovery_events is True
    assert report.idempotent_recovery_events is True
    assert report.deterministic_recovery_replay_order is True
    assert report.supports_restart_persistence is False
    assert report.supports_postgres_conformance_target is False

    as_dict = store_capability_report_to_dict(report)
    assert as_dict["schema_id"] == STORE_SCHEMA_ID
    assert as_dict["supports_postgres_conformance_target"] is False
    assert "PostgreSQL conformance remains future R7 work." in as_dict["notes"]


@pytest.mark.asyncio
async def test_sqlite_file_store_reports_restart_persistence(tmp_path):
    db_path = tmp_path / "durability.sqlite"

    store = SQLiteStore(db_path)
    report = await store.get_store_capability_report()

    assert report.supports_restart_persistence is True

    reopened = SQLiteStore(db_path)
    reopened_report = await reopened.get_store_capability_report()

    assert reopened_report.schema_version == STORE_SCHEMA_VERSION
    assert reopened_report.supports_restart_persistence is True
