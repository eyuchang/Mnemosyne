from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

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
        store_type = EXCLUDED.store_type,
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


class PostgresRecoveryEventConflictError(RuntimeError):
    """Raised when a recovery event conflicts with an existing sequence slot."""


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
    """Optional PostgreSQL recovery-event adapter.

    R7.8.1 keeps PostgreSQL opt-in, closes owned connections, avoids hot-path
    repeated schema DDL, casts payloads to JSONB, and makes idempotent retry
    resilient to unique-conflict races.
    """

    def __init__(
        self,
        config: PostgresStoreConfig | None = None,
        *,
        connection_factory: Callable[[], Any] | None = None,
        connection_provider: Callable[[], Any] | None = None,
    ) -> None:
        self.config = config if config is not None else postgres_store_config_from_env()
        self._connection_factory = connection_factory
        self._connection_provider = connection_provider
        self._schema_initialized = False

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
    def _commit(connection: Any) -> None:
        if hasattr(connection, "commit"):
            connection.commit()

    @staticmethod
    def _rollback(connection: Any) -> None:
        if hasattr(connection, "rollback"):
            connection.rollback()

    @staticmethod
    def _close(connection: Any) -> None:
        if hasattr(connection, "close"):
            connection.close()

    @contextmanager
    def _managed_connection(self) -> Iterator[Any]:
        self.require_configured()

        if self._connection_provider is not None:
            provided = self._connection_provider()

            if hasattr(provided, "__enter__") and hasattr(provided, "__exit__"):
                with provided as connection:
                    try:
                        self._initialize_schema_once(connection)
                        yield connection
                    except Exception:
                        self._rollback(connection)
                        raise
                return

            try:
                self._initialize_schema_once(provided)
                yield provided
            except Exception:
                self._rollback(provided)
                raise
            return

        connection = self._connect()
        try:
            self._initialize_schema_once(connection)
            yield connection
        except Exception:
            self._rollback(connection)
            raise
        finally:
            self._close(connection)

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
            decoded = json.loads(value)
            if isinstance(decoded, dict):
                return decoded
            raise TypeError("Recovery event payload must decode to a JSON object")
        decoded = dict(value)
        if not isinstance(decoded, dict):
            raise TypeError("Recovery event payload must be a JSON object")
        return decoded

    @staticmethod
    def _normalize_created_at(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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

    def _initialize_schema_once(self, connection: Any) -> None:
        if not self.config.initialize_schema or self._schema_initialized:
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

        self._commit(connection)
        self._schema_initialized = True

    @staticmethod
    def _select_columns_sql() -> str:
        return """
            SELECT event_id, tenant_id, workflow_id, recovery_id, sequence_no,
                   event_type, idempotency_key, causality_key, payload,
                   schema_id, schema_version, created_at
            FROM recovery_events
        """

    def _select_by_event_or_idempotency(
        self,
        cursor: Any,
        event: RecoveryEvent,
    ) -> RecoveryEvent | None:
        cursor.execute(
            self._select_columns_sql()
            + """
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
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_recovery_event(row)

    def _select_by_recovery_sequence(
        self,
        cursor: Any,
        event: RecoveryEvent,
    ) -> RecoveryEvent | None:
        cursor.execute(
            self._select_columns_sql()
            + """
            WHERE tenant_id = %s
              AND recovery_id = %s
              AND sequence_no = %s
            LIMIT 1
            """,
            (
                event.tenant_id,
                event.recovery_id,
                event.sequence_no,
            ),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_recovery_event(row)

    async def initialize_schema(self) -> None:
        connection = self._connect()
        try:
            self._initialize_schema_once(connection)
        except Exception:
            self._rollback(connection)
            raise
        finally:
            self._close(connection)

    async def get_store_schema_version(self) -> str:
        if not self.config.configured:
            return self.config.schema_version

        with self._managed_connection() as connection:
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
        live_configured = self.config.configured

        return StoreCapabilityReport(
            store_type="PostgresStore",
            schema_id=self.config.schema_id,
            schema_version=self.config.schema_version,
            durable_recovery_events=live_configured,
            idempotent_recovery_events=live_configured,
            deterministic_recovery_replay_order=live_configured,
            supports_restart_persistence=live_configured,
            supports_postgres_conformance_target=True,
            notes=(
                "R7.8.1 implements the opt-in PostgreSQL recovery-event adapter surface.",
                "Live PostgreSQL execution remains gated by configuration.",
                f"Live use requires {POSTGRES_DATABASE_URL_ENV}.",
                "Default CI remains PostgreSQL-free.",
            ),
        )

    async def get_record(self, tenant_id: str, rid: str) -> Any:
        raise NotImplementedError(
            "PostgreSQL get_record is outside the R7.8 recovery-event adapter scope"
        )

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: Any) -> list[Any]:
        raise NotImplementedError(
            "PostgreSQL get_entity_history is outside the R7.8 recovery-event adapter scope"
        )

    async def get_full_entity_history(self, tenant_id: str, eid: str, fsm: Any) -> list[Any]:
        raise NotImplementedError(
            "PostgreSQL get_full_entity_history is outside the R7.8 recovery-event adapter scope"
        )

    async def get_state_view(self, tenant_id: str, eid: str, fsm: Any) -> Any:
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
        self.require_configured()
        created_at = self._normalize_created_at(event.created_at)

        with self._managed_connection() as connection:
            with self._cursor(connection) as cursor:
                existing = self._select_by_event_or_idempotency(cursor, event)
                if existing is not None:
                    return existing

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
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING event_id
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
                        created_at,
                    ),
                )
                inserted = cursor.fetchone()

                if inserted is None:
                    existing = self._select_by_event_or_idempotency(cursor, event)
                    if existing is not None:
                        return existing

                    sequence_conflict = self._select_by_recovery_sequence(cursor, event)
                    if sequence_conflict is not None:
                        raise PostgresRecoveryEventConflictError(
                            "Recovery event conflicts with an existing "
                            "(tenant_id, recovery_id, sequence_no) slot"
                        )

                    raise PostgresRecoveryEventConflictError(
                        "Recovery event insert conflicted but no canonical row was found"
                    )

            self._commit(connection)

        return RecoveryEvent(
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            workflow_id=event.workflow_id,
            recovery_id=event.recovery_id,
            sequence_no=event.sequence_no,
            event_type=event.event_type,
            idempotency_key=event.idempotency_key,
            causality_key=event.causality_key,
            payload=event.payload,
            schema_id=event.schema_id,
            schema_version=event.schema_version,
            created_at=created_at,
        )

    async def list_recovery_events(
        self,
        tenant_id: str,
        *,
        workflow_id: str | None = None,
        recovery_id: str | None = None,
        event_type: str | None = None,
    ) -> list[RecoveryEvent]:
        with self._managed_connection() as connection:
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
                {self._select_columns_sql()}
                WHERE {' AND '.join(clauses)}
                ORDER BY recovery_id, sequence_no, event_id
            """

            with self._cursor(connection) as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

        return [self._row_to_recovery_event(row) for row in rows]
