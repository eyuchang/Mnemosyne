from __future__ import annotations

from pathlib import Path

import pytest

from mnemosyne.store.factory import (
    POSTGRES_BACKEND,
    SQLITE_BACKEND,
    STORE_BACKEND_ENV,
    SQLITE_PATH_ENV,
    StoreFactoryConfig,
    UnsupportedStoreBackendError,
    create_store,
    store_factory_config_from_env,
    store_factory_config_to_dict,
)
from mnemosyne.store.postgres import POSTGRES_DATABASE_URL_ENV, PostgresStore
from mnemosyne.store.postgres.store import PostgresStoreNotConfiguredError
from mnemosyne.store.sqlite.store import SQLiteStore


def test_store_factory_config_defaults_to_sqlite():
    config = store_factory_config_from_env({})

    assert config.backend == SQLITE_BACKEND
    assert config.normalized_backend == SQLITE_BACKEND
    assert config.sqlite_path is None
    assert config.postgres_database_url is None


def test_store_factory_creates_default_sqlite_store():
    store = create_store(StoreFactoryConfig())

    assert isinstance(store, SQLiteStore)


def test_store_factory_creates_file_backed_sqlite_store(tmp_path):
    db_path = tmp_path / "factory.sqlite"

    store = create_store(
        StoreFactoryConfig(
            backend=SQLITE_BACKEND,
            sqlite_path=db_path,
        )
    )

    assert isinstance(store, SQLiteStore)
    assert Path(store.path) == db_path


def test_store_factory_creates_optional_postgres_store_without_live_dependency():
    store = create_store(
        StoreFactoryConfig(
            backend=POSTGRES_BACKEND,
            postgres_database_url="postgresql://user:secret@localhost:5432/mnemosyne",
        )
    )

    assert isinstance(store, PostgresStore)
    assert store.config.configured is True
    assert store.config.redacted_database_url == "postgresql://***:***@localhost:5432/mnemosyne"


def test_store_factory_can_require_postgres_configuration():
    with pytest.raises(PostgresStoreNotConfiguredError):
        create_store(
            StoreFactoryConfig(
                backend=POSTGRES_BACKEND,
                require_configured_postgres=True,
            )
        )


def test_store_factory_rejects_unknown_backend():
    with pytest.raises(UnsupportedStoreBackendError) as exc:
        create_store(StoreFactoryConfig(backend="unknown"))

    assert "unsupported store backend" in str(exc.value)


def test_store_factory_config_from_env_reads_backend_values(tmp_path):
    db_path = tmp_path / "from-env.sqlite"

    config = store_factory_config_from_env(
        {
            STORE_BACKEND_ENV: SQLITE_BACKEND,
            SQLITE_PATH_ENV: str(db_path),
            POSTGRES_DATABASE_URL_ENV: "postgresql://user:secret@localhost:5432/mnemosyne",
        }
    )

    as_dict = store_factory_config_to_dict(config)

    assert config.normalized_backend == SQLITE_BACKEND
    assert config.sqlite_path == str(db_path)
    assert as_dict["postgres_database_url_present"] is True
    assert as_dict["sqlite_path"] == str(db_path)
