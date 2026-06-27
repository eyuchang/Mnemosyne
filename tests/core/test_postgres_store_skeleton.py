from __future__ import annotations

import pytest

from mnemosyne.core.store_capabilities import STORE_SCHEMA_ID, STORE_SCHEMA_VERSION
from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresStore,
    PostgresStoreConfig,
    PostgresStoreNotConfiguredError,
    postgres_store_config_from_env,
)


def test_postgres_store_config_from_env_is_opt_in():
    config = postgres_store_config_from_env({})

    assert config.database_url is None
    assert config.configured is False
    assert config.schema_id == STORE_SCHEMA_ID
    assert config.schema_version == STORE_SCHEMA_VERSION


def test_postgres_store_config_redacts_password():
    config = PostgresStoreConfig(
        database_url="postgresql://user:secret@localhost:5432/mnemosyne"
    )

    assert config.redacted_database_url == "postgresql://***:***@localhost:5432/mnemosyne"


def test_postgres_store_config_from_env_reads_expected_variable():
    config = postgres_store_config_from_env(
        {
            POSTGRES_DATABASE_URL_ENV: "postgresql://user:secret@localhost:5432/mnemosyne"
        }
    )

    assert config.configured is True
    assert config.redacted_database_url == "postgresql://***:***@localhost:5432/mnemosyne"


def test_postgres_store_fails_closed_when_not_configured():
    store = PostgresStore(PostgresStoreConfig(database_url=None))

    with pytest.raises(PostgresStoreNotConfiguredError) as exc:
        store.require_configured()

    assert POSTGRES_DATABASE_URL_ENV in str(exc.value)


@pytest.mark.asyncio
async def test_postgres_store_reports_future_conformance_capability_without_live_dependency():
    store = PostgresStore(PostgresStoreConfig(database_url=None))

    report = await store.get_store_capability_report()

    assert report.store_type == "PostgresStore"
    assert report.schema_id == STORE_SCHEMA_ID
    assert report.schema_version == STORE_SCHEMA_VERSION
    assert report.supports_restart_persistence is True
    assert report.supports_postgres_conformance_target is True
    assert "R7.8 implements the live PostgreSQL adapter surface." in report.notes
    assert "Live PostgreSQL execution remains opt-in." in report.notes


@pytest.mark.asyncio
async def test_postgres_store_recovery_event_methods_fail_closed_when_not_configured():
    store = PostgresStore(PostgresStoreConfig(database_url=None))

    with pytest.raises(PostgresStoreNotConfiguredError):
        await store.append_recovery_event(object())

    with pytest.raises(PostgresStoreNotConfiguredError):
        await store.list_recovery_events("tenant")
