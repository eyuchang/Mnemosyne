from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.store_conformance import (
    RecoveryStoreConformanceCase,
    observe_recovery_store_conformance,
)
from mnemosyne.store.postgres import POSTGRES_SCHEMA_STATEMENTS, PostgresStore, PostgresStoreConfig


class FakePostgresCursor:
    def __init__(self, connection: "FakePostgresConnection") -> None:
        self.connection = connection
        self._one: dict[str, Any] | None = None
        self._many: list[dict[str, Any]] = []

    def __enter__(self) -> "FakePostgresCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        normalized = " ".join(sql.split()).lower()
        params = params or ()

        self._one = None
        self._many = []

        if normalized.startswith("create table") or normalized.startswith("create index"):
            return

        if normalized.startswith("insert into store_schema_metadata"):
            self.connection.schema_metadata = {
                "schema_id": params[0],
                "schema_version": params[1],
                "store_type": params[2],
            }
            return

        if normalized.startswith("select schema_version from store_schema_metadata"):
            self._one = {
                "schema_version": self.connection.schema_metadata["schema_version"]
            }
            return

        if normalized.startswith("select event_id") and "event_id = %s or idempotency_key = %s" in normalized:
            tenant_id, event_id, idempotency_key, _preferred_event_id = params
            matches = [
                row
                for row in self.connection.recovery_events
                if row["tenant_id"] == tenant_id
                and (
                    row["event_id"] == event_id
                    or row["idempotency_key"] == idempotency_key
                )
            ]
            matches.sort(
                key=lambda row: (
                    0 if row["event_id"] == event_id else 1,
                    row["sequence_no"],
                    row["event_id"],
                )
            )
            self._one = matches[0] if matches else None
            return

        if normalized.startswith("insert into recovery_events"):
            self.connection.recovery_events.append(
                {
                    "event_id": params[0],
                    "tenant_id": params[1],
                    "workflow_id": params[2],
                    "recovery_id": params[3],
                    "sequence_no": params[4],
                    "event_type": params[5],
                    "idempotency_key": params[6],
                    "causality_key": params[7],
                    "payload": params[8],
                    "schema_id": params[9],
                    "schema_version": params[10],
                    "created_at": params[11],
                }
            )
            return

        if normalized.startswith("select event_id") and "from recovery_events" in normalized:
            tenant_id = params[0]
            workflow_id = params[1] if "workflow_id = %s" in normalized else None
            recovery_id = params[2] if "recovery_id = %s" in normalized and workflow_id is not None else None
            if "recovery_id = %s" in normalized and workflow_id is None:
                recovery_id = params[1]
            event_type = params[-1] if "event_type = %s" in normalized else None

            rows = [
                row
                for row in self.connection.recovery_events
                if row["tenant_id"] == tenant_id
                and (workflow_id is None or row["workflow_id"] == workflow_id)
                and (recovery_id is None or row["recovery_id"] == recovery_id)
                and (event_type is None or row["event_type"] == event_type)
            ]
            rows.sort(key=lambda row: (row["recovery_id"], row["sequence_no"], row["event_id"]))
            self._many = rows
            return

        raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self) -> dict[str, Any] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._many)


class FakePostgresConnection:
    def __init__(self) -> None:
        self.schema_metadata = {
            "schema_id": "mnemosyne.store.sqlite",
            "schema_version": "1.0",
            "store_type": "PostgresStore",
        }
        self.recovery_events: list[dict[str, Any]] = []
        self.commit_count = 0

    def cursor(self) -> FakePostgresCursor:
        return FakePostgresCursor(self)

    def commit(self) -> None:
        self.commit_count += 1


def _event(event_id: str, sequence_no: int, idempotency_key: str) -> RecoveryEvent:
    return RecoveryEvent(
        event_id=event_id,
        tenant_id="tenant-pg",
        workflow_id="workflow-pg",
        recovery_id="recovery-pg",
        sequence_no=sequence_no,
        event_type="commitment_fired",
        idempotency_key=idempotency_key,
        payload={"event_id": event_id},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_postgres_schema_statements_define_recovery_event_constraints():
    schema = "\\n".join(POSTGRES_SCHEMA_STATEMENTS)

    assert "CREATE TABLE IF NOT EXISTS recovery_events" in schema
    assert "PRIMARY KEY (tenant_id, event_id)" in schema
    assert "UNIQUE (tenant_id, idempotency_key)" in schema
    assert "UNIQUE (tenant_id, recovery_id, sequence_no)" in schema
    assert "payload JSONB NOT NULL" in schema


@pytest.mark.asyncio
async def test_postgres_store_appends_lists_and_idempotently_returns_existing_event():
    connection = FakePostgresConnection()
    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_factory=lambda: connection,
    )

    first = await store.append_recovery_event(_event("pg-event-2", 2, "pg-idem-2"))
    second = await store.append_recovery_event(_event("pg-event-1", 1, "pg-idem-1"))
    duplicate = await store.append_recovery_event(_event("pg-event-dup", 3, "pg-idem-1"))

    assert first.event_id == "pg-event-2"
    assert second.event_id == "pg-event-1"
    assert duplicate.event_id == "pg-event-1"

    events = await store.list_recovery_events(
        "tenant-pg",
        workflow_id="workflow-pg",
        recovery_id="recovery-pg",
    )

    assert [event.event_id for event in events] == ["pg-event-1", "pg-event-2"]


@pytest.mark.asyncio
async def test_postgres_store_passes_recovery_store_conformance_with_fake_connection():
    connection = FakePostgresConnection()
    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_factory=lambda: connection,
    )

    observation = await observe_recovery_store_conformance(
        store,
        RecoveryStoreConformanceCase(
            store_name="PostgresStore",
            expects_restart_persistence=True,
        ),
    )

    assert observation.passed is True
    assert observation.details["store_type"] == "PostgresStore"
    assert observation.details["event_ids"] == [
        "conformance-event-1",
        "conformance-event-2",
    ]
    assert observation.details["duplicate_result_event_id"] == "conformance-event-1"

@pytest.mark.asyncio
async def test_postgres_store_non_event_runtime_methods_remain_out_of_scope():
    store = PostgresStore(
        PostgresStoreConfig(database_url="postgresql://fake"),
        connection_factory=FakePostgresConnection,
    )

    with pytest.raises(NotImplementedError):
        await store.get_record("tenant", "rid")

    with pytest.raises(NotImplementedError):
        await store.get_entity_history("tenant", "eid", "fsm")

    with pytest.raises(NotImplementedError):
        await store.get_full_entity_history("tenant", "eid", "fsm")

    with pytest.raises(NotImplementedError):
        await store.get_state_view("tenant", "eid", "fsm")

    with pytest.raises(NotImplementedError):
        await store.get_by_op_id("tenant", "op")

    with pytest.raises(NotImplementedError):
        await store.commit_batch([])

