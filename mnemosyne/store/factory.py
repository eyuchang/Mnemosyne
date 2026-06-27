from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mnemosyne.store.postgres import (
    POSTGRES_DATABASE_URL_ENV,
    PostgresStore,
    PostgresStoreConfig,
)
from mnemosyne.store.sqlite.store import SQLiteStore


STORE_BACKEND_ENV = "MNEMOSYNE_STORE_BACKEND"
SQLITE_PATH_ENV = "MNEMOSYNE_SQLITE_PATH"

SQLITE_BACKEND = "sqlite"
POSTGRES_BACKEND = "postgres"


class UnsupportedStoreBackendError(ValueError):
    """Raised when a store backend name is not supported."""


@dataclass(frozen=True)
class StoreFactoryConfig:
    backend: str = SQLITE_BACKEND
    sqlite_path: str | Path | None = None
    postgres_database_url: str | None = None
    require_configured_postgres: bool = False

    @property
    def normalized_backend(self) -> str:
        return self.backend.strip().lower()


def store_factory_config_from_env(
    env: dict[str, str] | None = None,
) -> StoreFactoryConfig:
    source = env if env is not None else os.environ

    return StoreFactoryConfig(
        backend=source.get(STORE_BACKEND_ENV, SQLITE_BACKEND),
        sqlite_path=source.get(SQLITE_PATH_ENV),
        postgres_database_url=source.get(POSTGRES_DATABASE_URL_ENV),
    )


def create_store(config: StoreFactoryConfig | None = None) -> Any:
    resolved = config if config is not None else store_factory_config_from_env()
    backend = resolved.normalized_backend

    if backend == SQLITE_BACKEND:
        if resolved.sqlite_path:
            return SQLiteStore(Path(resolved.sqlite_path))
        return SQLiteStore()

    if backend == POSTGRES_BACKEND:
        store = PostgresStore(
            PostgresStoreConfig(database_url=resolved.postgres_database_url)
        )
        if resolved.require_configured_postgres:
            store.require_configured()
        return store

    raise UnsupportedStoreBackendError(f"unsupported store backend: {resolved.backend}")


def store_factory_config_to_dict(config: StoreFactoryConfig) -> dict[str, Any]:
    return {
        "backend": config.backend,
        "normalized_backend": config.normalized_backend,
        "sqlite_path": str(config.sqlite_path) if config.sqlite_path is not None else None,
        "postgres_database_url_present": bool(config.postgres_database_url),
        "require_configured_postgres": config.require_configured_postgres,
    }
