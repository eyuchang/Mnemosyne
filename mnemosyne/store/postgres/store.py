from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.store_capabilities import (
    STORE_SCHEMA_ID,
    STORE_SCHEMA_VERSION,
    StoreCapabilityReport,
)


POSTGRES_DATABASE_URL_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"

POSTGRES_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS store_schema_metadata (
        schema_id TEXT PRIMARY KEY,
        schema_version TEXT NOT NULL,
        store_type TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    INSERT INTO store_schema_metadata
    (
        schema_id,
        schema_version,
        store_type,
        created_at,
        updated_at
    )
    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT (schema_id) DO UPDATE SET
        schema_version = EXCLUDED.schema_version,
        updated_at = CURRENT_TIMESTAMP
    """,
    """
    CREATE TABLE IF NOT EXISTS recovery_events (
        event_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        workflow_id TEXT,
        recovery_id TEXT NOT NULL,
        sequence_no INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        causality_key TEXT,
        payload JSONB NOT NULL,
        schema_id TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (tenant_id, event_id),
        UNIQUE (tenant_id, idempotency_key),
        UNIQUE (tenant_id, recovery_id, sequence_no)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_recovery_events_recovery
    ON recovery_events (tenant_id, recovery_id, sequence_no)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_recovery_events_workflow
    ON recovery_events (tenant_id, workflow_id, created_at)
    """,
)


class PostgresStoreNotConfiguredError(RuntimeError):
    """Raised when PostgreSQL store usage is attempted without configuration."""


class PostgresStoreDependencyError(RuntimeError):
    """Raised when live PostgreSQL usage is requested but psycopg is unavailable."""


@dataclass(frozen=True)
class PostgresStoreConfig:
    database_url: str | None = None
    schema_id: str = STORE_SCHEMA_ID
    schema_version: str = STORE_SCHEMA_VERSION
    connect_timeout_seconds: int = 5
    initialize_schema: bool = True

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
    """Optional PostgreSQL recovery-store adapter.

    R7.8 implements the live adapter surface behind explicit configuration.
    Default CI remains PostgreSQL-free because no connection is opened unless
    PostgreSQL is selected and a database URL is supplied.
    """

    def __init__(
        self,
        config: PostgresStoreConfig | None = None,
        *,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.config = config if config is not None else postgres_store_config_from_env()
        self._connection_factory = connection_factory

    @property
    def configured(self) -> bool:
        return self.config.configured

    def require_configured(self) -> None:
        if not self.config.configured:
            raise PostgresStoreNotConfiguredError(
                f"PostgreSQL store requires {POSTGRES_DATABASE_URL_ENV}"
            )

    def _connect(self) -> Any:
        self.require_configured()

        if self._connection_factory is not None:
            return self._connection_factory()

        try:
            import psycopg  # type: ignore[import-not-found]
        except ImportError as exc:
            raise PostgresStoreDependencyError(
                "Live PostgreSQL store requires optional dependency `psycopg`"
            ) from exc

        return psycopg.connect(
            self.config.database_url,
            connect_timeout=self.config.connect_timeout_seconds,
        )

    @staticmethod
    def _cursor(connection: Any) -> Any:
        return connection.cursor()

    @staticmethod
    def _row_value(row: Any, key: str, index: int) -> Any:
        if isinstance(row, dict):
            return row[key]
        return row[index]

    @staticmethod
    def _decode_payload(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    @classmethod
    def _row_to_recovery_event(cls, row: Any) -> RecoveryEvent:
        return RecoveryEvent(
            event_id=str(cls._row_value(row, "event_id", 0)),
            tenant_id=str(cls._row_value(row, "tenant_id", 1)),
            workflow_id=cls._row_value(row, "workflow_id", 2),
            recovery_id=str(cls._row_value(row, "recovery_id", 3)),
            sequence_no=int(cls._row_value(row, "sequence_no", 4)),
            event_type=str(cls._row_value(row, "event_type", 5)),
            idempotency_key=str(cls._row_value(row, "idempotency_key", 6)),
            causality_key=cls._row_value(row, "causality_key", 7),
            payload=cls._decode_payload(cls._row_value(row, "payload", 8)),
            schema_id=str(cls._row_value(row, "schema_id", 9)),
            schema_version=str(cls._row_value(row, "schema_version", 10)),
            created_at=cls._row_value(row, "created_at", 11),
        )

    def _initialize_schema(self, connection: Any) -> None:
        if not self.config.initialize_schema:
            return

        with self._cursor(connection) as cursor:
            for statement in POSTGRES_SCHEMA_STATEMENTS:
                if "INSERT INTO store_schema_metadata" in statement:
                    cursor.execute(
                        statement,
                        (
                            self.config.schema_id,
                            self.config.schema_version,
                            "PostgresStore",
                        ),
                    )
                else:
                    cursor.execute(statement)

        if hasattr(connection, "commit"):
            connection.commit()

    async def initialize_schema(self) -> None:
        connection = self._connect()
        self._initialize_schema(connection)

    async def get_store_schema_version(self) -> str:
        if not self.config.configured:
            return self.config.schema_version

        connection = self._connect()
        self._initialize_schema(connection)

        with self._cursor(connection) as cursor:
            cursor.execute(
                """
                SELECT schema_version
                FROM store_schema_metadata
                WHERE schema_id = %s
                """,
                (self.config.schema_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return self.config.schema_version

        return str(self._row_value(row, "schema_version", 0))

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
                "R7.8 implements the live PostgreSQL adapter surface.",
                "Live PostgreSQL execution remains opt-in.",
                f"Live use requires {POSTGRES_DATABASE_URL_ENV}.",
            ),
        )

    async def get_record(self, tenant_id: str, rid: str) -> Any:
        raise NotImplementedError(
            "PostgreSQL get_record is outside the R7.8 recovery-event adapter scope"
        )

    async def get_entity_history(self, tenant_id: str, rid: str) -> list[Any]:
        raise NotImplementedError(
            "PostgreSQL get_entity_history is outside the R7.8 recovery-event adapter scope"
        )

    async def get_full_entity_history(self, tenant_id: str, rid: str) -> list[Any]:
        raise NotImplementedError(
            "PostgreSQL get_full_entity_history is outside the R7.8 recovery-event adapter scope"
        )

    async def get_state_view(self, tenant_id: str) -> Any:
        raise NotImplementedError(
            "PostgreSQL get_state_view is outside the R7.8 recovery-event adapter scope"
        )

    async def get_by_op_id(self, tenant_id: str, op_id: str) -> Any:
        raise NotImplementedError(
            "PostgreSQL get_by_op_id is outside the R7.8 recovery-event adapter scope"
        )

    async def commit_batch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "PostgreSQL commit_batch is outside the R7.8 recovery-event adapter scope"
        )

    async def append_recovery_event(self, event: RecoveryEvent) -> RecoveryEvent:
        connection = self._connect()
        self._initialize_schema(connection)

        with self._cursor(connection) as cursor:
            cursor.execute(
                """
                SELECT event_id, tenant_id, workflow_id, recovery_id, sequence_no,
                       event_type, idempotency_key, causality_key, payload,
                       schema_id, schema_version, created_at
                FROM recovery_events
                WHERE tenant_id = %s
                  AND (event_id = %s OR idempotency_key = %s)
                ORDER BY
                    CASE WHEN event_id = %s THEN 0 ELSE 1 END,
                    sequence_no,
                    event_id
                LIMIT 1
                """,
                (
                    event.tenant_id,
                    event.event_id,
                    event.idempotency_key,
                    event.event_id,
                ),
            )
            existing = cursor.fetchone()
            if existing is not None:
                return self._row_to_recovery_event(existing)

            cursor.execute(
                """
                INSERT INTO recovery_events
                (
                    event_id,
                    tenant_id,
                    workflow_id,
                    recovery_id,
                    sequence_no,
                    event_type,
                    idempotency_key,
                    causality_key,
                    payload,
                    schema_id,
                    schema_version,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.workflow_id,
                    event.recovery_id,
                    event.sequence_no,
                    event.event_type,
                    event.idempotency_key,
                    event.causality_key,
                    json.dumps(event.payload, sort_keys=True),
                    event.schema_id,
                    event.schema_version,
                    event.created_at,
                ),
            )

        if hasattr(connection, "commit"):
            connection.commit()

        return event

    async def list_recovery_events(
        self,
        tenant_id: str,
        *,
        workflow_id: str | None = None,
        recovery_id: str | None = None,
        event_type: str | None = None,
    ) -> list[RecoveryEvent]:
        connection = self._connect()
        self._initialize_schema(connection)

        clauses = ["tenant_id = %s"]
        params: list[Any] = [tenant_id]

        if workflow_id is not None:
            clauses.append("workflow_id = %s")
            params.append(workflow_id)

        if recovery_id is not None:
            clauses.append("recovery_id = %s")
            params.append(recovery_id)

        if event_type is not None:
            clauses.append("event_type = %s")
            params.append(event_type)

        query = f"""
            SELECT event_id, tenant_id, workflow_id, recovery_id, sequence_no,
                   event_type, idempotency_key, causality_key, payload,
                   schema_id, schema_version, created_at
            FROM recovery_events
            WHERE {' AND '.join(clauses)}
            ORDER BY recovery_id, sequence_no, event_id
        """

        with self._cursor(connection) as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [self._row_to_recovery_event(row) for row in rows]
