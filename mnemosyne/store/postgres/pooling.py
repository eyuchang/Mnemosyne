from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from mnemosyne.store.postgres.store import POSTGRES_DATABASE_URL_ENV


POSTGRES_POOL_MIN_SIZE_ENV = "MNEMOSYNE_POSTGRES_POOL_MIN_SIZE"
POSTGRES_POOL_MAX_SIZE_ENV = "MNEMOSYNE_POSTGRES_POOL_MAX_SIZE"
POSTGRES_POOL_TIMEOUT_SECONDS_ENV = "MNEMOSYNE_POSTGRES_POOL_TIMEOUT_SECONDS"


class PostgresConnectionPoolNotConfiguredError(RuntimeError):
    """Raised when PostgreSQL pooling is requested without DATABASE_URL."""


class PostgresConnectionPoolConfigError(ValueError):
    """Raised when PostgreSQL pool configuration is invalid."""


class PostgresConnectionPoolDependencyError(RuntimeError):
    """Raised when psycopg_pool is required but unavailable."""


@dataclass(frozen=True)
class PostgresConnectionPoolConfig:
    database_url: str | None = None
    min_size: int = 1
    max_size: int = 10
    timeout_seconds: float = 5.0
    open_immediately: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.database_url)

    @property
    def redacted_database_url(self) -> str | None:
        if not self.database_url:
            return None

        if "@" not in self.database_url:
            return self.database_url

        prefix, suffix = self.database_url.rsplit("@", 1)
        scheme = prefix.split("://", 1)[0] if "://" in prefix else "postgresql"
        return f"{scheme}://***:***@{suffix}"

    def validate(self) -> None:
        if not self.configured:
            raise PostgresConnectionPoolNotConfiguredError(
                f"PostgreSQL connection pool requires {POSTGRES_DATABASE_URL_ENV}"
            )

        if self.min_size < 1:
            raise PostgresConnectionPoolConfigError("min_size must be >= 1")

        if self.max_size < self.min_size:
            raise PostgresConnectionPoolConfigError(
                "max_size must be greater than or equal to min_size"
            )

        if self.timeout_seconds <= 0:
            raise PostgresConnectionPoolConfigError("timeout_seconds must be > 0")


def _int_env(source: dict[str, str], name: str, default: int) -> int:
    value = source.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _float_env(source: dict[str, str], name: str, default: float) -> float:
    value = source.get(name)
    if value is None or value == "":
        return default
    return float(value)


def postgres_connection_pool_config_from_env(
    env: dict[str, str] | None = None,
) -> PostgresConnectionPoolConfig:
    source = env if env is not None else os.environ

    return PostgresConnectionPoolConfig(
        database_url=source.get(POSTGRES_DATABASE_URL_ENV),
        min_size=_int_env(source, POSTGRES_POOL_MIN_SIZE_ENV, 1),
        max_size=_int_env(source, POSTGRES_POOL_MAX_SIZE_ENV, 10),
        timeout_seconds=_float_env(source, POSTGRES_POOL_TIMEOUT_SECONDS_ENV, 5.0),
    )


def create_psycopg_connection_pool(config: PostgresConnectionPoolConfig) -> Any:
    """Create a psycopg_pool.ConnectionPool when the optional dependency exists.

    This function is intentionally lazy so default CI and SQLite-only users do not
    need psycopg_pool installed.
    """

    config.validate()

    try:
        from psycopg_pool import ConnectionPool  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PostgresConnectionPoolDependencyError(
            "PostgreSQL connection pooling requires optional dependency `psycopg_pool`"
        ) from exc

    return ConnectionPool(
        conninfo=config.database_url,
        min_size=config.min_size,
        max_size=config.max_size,
        timeout=config.timeout_seconds,
        open=config.open_immediately,
    )


def postgres_connection_pool_boundary_report(
    config: PostgresConnectionPoolConfig | None = None,
) -> dict[str, Any]:
    selected = config if config is not None else postgres_connection_pool_config_from_env()

    return {
        "postgres_database_url_env": POSTGRES_DATABASE_URL_ENV,
        "pool_min_size_env": POSTGRES_POOL_MIN_SIZE_ENV,
        "pool_max_size_env": POSTGRES_POOL_MAX_SIZE_ENV,
        "pool_timeout_seconds_env": POSTGRES_POOL_TIMEOUT_SECONDS_ENV,
        "configured": selected.configured,
        "database_url": selected.redacted_database_url,
        "min_size": selected.min_size,
        "max_size": selected.max_size,
        "timeout_seconds": selected.timeout_seconds,
        "open_immediately": selected.open_immediately,
        "optional_dependency": "psycopg_pool",
        "default_ci_requires_pool_dependency": False,
        "default_ci_requires_postgres_service": False,
        "pool_creation_is_lazy": True,
        "pooling_implementation_claimed": False,
        "pooling_boundary_claimed": True,
    }
