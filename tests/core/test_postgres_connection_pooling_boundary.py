from __future__ import annotations

import builtins

import pytest

from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    POSTGRES_POOL_MAX_SIZE_ENV,
    POSTGRES_POOL_MIN_SIZE_ENV,
    POSTGRES_POOL_TIMEOUT_SECONDS_ENV,
    PostgresConnectionPoolConfig,
    PostgresConnectionPoolConfigError,
    PostgresConnectionPoolDependencyError,
    PostgresConnectionPoolNotConfiguredError,
    create_psycopg_connection_pool,
    postgres_connection_pool_boundary_report,
    postgres_connection_pool_config_from_env,
)


def test_postgres_connection_pool_config_from_env_uses_explicit_pool_settings():
    config = postgres_connection_pool_config_from_env(
        {
            POSTGRES_DATABASE_URL_ENV: "postgresql://user:secret@localhost:5432/db",
            POSTGRES_POOL_MIN_SIZE_ENV: "2",
            POSTGRES_POOL_MAX_SIZE_ENV: "8",
            POSTGRES_POOL_TIMEOUT_SECONDS_ENV: "3.5",
        }
    )

    assert config.configured is True
    assert config.redacted_database_url == "postgresql://***:***@localhost:5432/db"
    assert config.min_size == 2
    assert config.max_size == 8
    assert config.timeout_seconds == 3.5


def test_postgres_connection_pool_config_fails_closed_without_database_url():
    config = PostgresConnectionPoolConfig(database_url=None)

    with pytest.raises(PostgresConnectionPoolNotConfiguredError):
        config.validate()


def test_postgres_connection_pool_config_rejects_invalid_sizes():
    with pytest.raises(PostgresConnectionPoolConfigError):
        PostgresConnectionPoolConfig(
            database_url="postgresql://localhost/db",
            min_size=0,
            max_size=10,
        ).validate()

    with pytest.raises(PostgresConnectionPoolConfigError):
        PostgresConnectionPoolConfig(
            database_url="postgresql://localhost/db",
            min_size=5,
            max_size=4,
        ).validate()

    with pytest.raises(PostgresConnectionPoolConfigError):
        PostgresConnectionPoolConfig(
            database_url="postgresql://localhost/db",
            timeout_seconds=0,
        ).validate()


def test_create_psycopg_connection_pool_imports_optional_dependency_lazily(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psycopg_pool":
            raise ImportError("blocked optional dependency")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(PostgresConnectionPoolDependencyError):
        create_psycopg_connection_pool(
            PostgresConnectionPoolConfig(database_url="postgresql://localhost/db")
        )


def test_postgres_connection_pool_boundary_report_is_honest_and_ci_safe():
    report = postgres_connection_pool_boundary_report(
        PostgresConnectionPoolConfig(
            database_url="postgresql://user:secret@localhost:5432/db",
            min_size=2,
            max_size=6,
            timeout_seconds=4.0,
        )
    )

    assert report["configured"] is True
    assert report["database_url"] == "postgresql://***:***@localhost:5432/db"
    assert report["min_size"] == 2
    assert report["max_size"] == 6
    assert report["timeout_seconds"] == 4.0
    assert report["optional_dependency"] == "psycopg_pool"
    assert report["default_ci_requires_pool_dependency"] is False
    assert report["default_ci_requires_postgres_service"] is False
    assert report["pool_creation_is_lazy"] is True
    assert report["pooling_boundary_claimed"] is True
    assert report["pooling_implementation_claimed"] is False
