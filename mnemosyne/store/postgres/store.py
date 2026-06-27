from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from mnemosyne.core.store_capabilities import (
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
    StoreCapabilityReport,
)


POSTGRES_DATABASE_URL_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"


class PostgresStoreNotConfiguredError(RuntimeError):
    """Raised when PostgreSQL store usage is attempted without configuration."""


@dataclass(frozen=True)
class PostgresStoreConfig:
    database_url: str | None = None
    schema_id: str = STORE_SCHEMA_ID
    schema_version: str = STORE_SCHEMA_VERSION
    connect_timeout_seconds: int = 5

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


def postgres_store_config_from_env(
    env: dict[str, str] | None = None,
) -> PostgresStoreConfig:
    source = env if env is not None else os.environ
    return PostgresStoreConfig(database_url=source.get(POSTGRES_DATABASE_URL_ENV))


class PostgresStore:
    """Optional PostgreSQL recovery-store adapter skeleton.

    R7.7 introduces the adapter surface and configuration boundary without
    requiring a PostgreSQL dependency in default CI. Live behavior is added in a
    later milestone behind MNEMOSYNE_POSTGRES_DATABASE_URL.
    """

    def __init__(self, config: PostgresStoreConfig | None = None) -> None:
        self.config = config if config is not None else postgres_store_config_from_env()

    @property
    def configured(self) -> bool:
        return self.config.configured

    def require_configured(self) -> None:
        if not self.config.configured:
            raise PostgresStoreNotConfiguredError(
                f"PostgreSQL store requires {POSTGRES_DATABASE_URL_ENV}"
            )

    async def get_store_schema_version(self) -> str:
        return self.config.schema_version

    async def get_store_capability_report(self) -> StoreCapabilityReport:
        return StoreCapabilityReport(
            store_type="PostgresStore",
            schema_id=self.config.schema_id,
            schema_version=self.config.schema_version,
            durable_recovery_events=True,
            idempotent_recovery_events=True,
            deterministic_recovery_replay_order=True,
            supports_restart_persistence=True,
            supports_postgres_conformance_target=True,
            notes=(
                "R7.7 defines the optional PostgreSQL adapter skeleton.",
                "Live PostgreSQL persistence is not implemented yet.",
                f"Live use requires {POSTGRES_DATABASE_URL_ENV}.",
            ),
        )

    async def append_recovery_event(self, event: Any) -> Any:
        self.require_configured()
        raise NotImplementedError(
            "PostgreSQL append_recovery_event is not implemented until the live adapter milestone"
        )

    async def list_recovery_events(
        self,
        tenant_id: str,
        *,
        workflow_id: str | None = None,
        recovery_id: str | None = None,
        event_type: str | None = None,
    ) -> list[Any]:
        self.require_configured()
        raise NotImplementedError(
            "PostgreSQL list_recovery_events is not implemented until the live adapter milestone"
        )
