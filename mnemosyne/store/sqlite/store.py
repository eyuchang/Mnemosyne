from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from mnemosyne.core.models import (
    CTLRecord,
    Command,
    CommitBatch,
    ExternalEvent,
    OutboxIntent,
    StateView,
)
from mnemosyne.core.recovery.events import RecoveryEvent
from mnemosyne.core.replay import replay_state_view


def _dt(value: datetime) -> str:
    return value.isoformat()


def _loads(value: str | None) -> Any:
    return json.loads(value) if value else None


class SQLiteStore:
    """Test/local store implementing the Phase 0 Store protocol.

    This store intentionally mirrors the production table shapes but uses stdlib sqlite3.
    CTL append, effective-index updates, projection updates, and outbox insertions happen
    synchronously inside the same transaction.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        # isolation_level=None: explicit BEGIN/COMMIT control, no implicit transactions.
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                workflow_id TEXT,
                submitted_at TEXT NOT NULL,
                UNIQUE(tenant_id, idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS event_log (
                log_position INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_refs TEXT NOT NULL,
                payload TEXT NOT NULL,
                workflow_id TEXT,
                binding_id TEXT,
                schema_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(tenant_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS recovery_events (
                log_position INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                workflow_id TEXT,
                recovery_id TEXT NOT NULL,
                sequence_no INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                causality_key TEXT,
                payload TEXT NOT NULL,
                schema_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(tenant_id, event_id),
                UNIQUE(tenant_id, idempotency_key),
                UNIQUE(tenant_id, recovery_id, sequence_no)
            );

            CREATE INDEX IF NOT EXISTS idx_recovery_events_recovery
                ON recovery_events(tenant_id, recovery_id, sequence_no);

            CREATE INDEX IF NOT EXISTS idx_recovery_events_workflow
                ON recovery_events(tenant_id, workflow_id, log_position);

            CREATE TABLE IF NOT EXISTS event_inbox (
                inbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                source TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                workflow_id TEXT,
                binding_id TEXT,
                payload TEXT NOT NULL,
                schema_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                received_at TEXT NOT NULL,
                processed_at TEXT,
                status TEXT NOT NULL,
                UNIQUE(tenant_id, source, dedupe_key)
            );

            CREATE TABLE IF NOT EXISTS ctl_records (
                log_position INTEGER PRIMARY KEY AUTOINCREMENT,
                rid TEXT NOT NULL,
                op_id TEXT,
                tenant_id TEXT NOT NULL,
                tx_group_id TEXT NOT NULL,
                workflow_id TEXT,
                binding_id TEXT,
                eid TEXT NOT NULL,
                fsm TEXT NOT NULL,
                version INTEGER NOT NULL,
                state_before TEXT NOT NULL,
                state_after TEXT NOT NULL,
                action_type TEXT NOT NULL,
                triggers TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                metadata TEXT NOT NULL,
                extension TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_version TEXT NOT NULL,
                schema_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                fsm_version TEXT NOT NULL,
                policy_id TEXT,
                policy_version TEXT,
                validator_id TEXT,
                validator_version TEXT,
                timestamp TEXT NOT NULL,
                local_log_position INTEGER NOT NULL,
                UNIQUE(tenant_id, rid),
                UNIQUE(tenant_id, op_id),
                UNIQUE(tenant_id, eid, fsm, version),
                UNIQUE(tenant_id, workflow_id, local_log_position)
            );

            CREATE INDEX IF NOT EXISTS idx_ctl_group
                ON ctl_records(tenant_id, tx_group_id);

            CREATE INDEX IF NOT EXISTS idx_ctl_entity
                ON ctl_records(tenant_id, eid, fsm, version);

            CREATE TABLE IF NOT EXISTS effective_record_index (
                tenant_id TEXT NOT NULL,
                rid TEXT NOT NULL,
                effective INTEGER NOT NULL,
                changed_by_rid TEXT,
                PRIMARY KEY (tenant_id, rid)
            );

            CREATE TABLE IF NOT EXISTS entity_projection (
                tenant_id TEXT NOT NULL,
                eid TEXT NOT NULL,
                fsm TEXT NOT NULL,
                state TEXT,
                version INTEGER NOT NULL,
                attrs TEXT NOT NULL,
                effective_records TEXT NOT NULL,
                as_of_log_position INTEGER,
                workflow_id TEXT,
                binding_id TEXT,
                PRIMARY KEY (tenant_id, eid, fsm)
            );

            CREATE TABLE IF NOT EXISTS outbox (
                outbox_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                effect_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                provider_idempotency_key TEXT NOT NULL,
                workflow_id TEXT,
                binding_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(tenant_id, outbox_id),
                UNIQUE(tenant_id, provider, provider_idempotency_key)
            );
            """
        )
        self.conn.commit()

    async def append_command(self, command: Command) -> Command:
        async with self._lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO commands
                (
                    command_id,
                    tenant_id,
                    actor_id,
                    command_type,
                    payload,
                    idempotency_key,
                    workflow_id,
                    submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    command.command_id,
                    command.tenant_id,
                    command.actor_id,
                    command.command_type,
                    json.dumps(command.payload),
                    command.idempotency_key,
                    command.workflow_id,
                    _dt(command.submitted_at),
                ),
            )
            self.conn.commit()
        return command

    async def append_event(self, event: ExternalEvent) -> ExternalEvent:
        async with self._lock:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO event_log
                (
                    event_id,
                    tenant_id,
                    source,
                    event_type,
                    entity_refs,
                    payload,
                    workflow_id,
                    binding_id,
                    schema_id,
                    schema_version,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.source,
                    event.event_type,
                    json.dumps(event.entity_refs),
                    json.dumps(event.payload),
                    event.workflow_id,
                    event.binding_id,
                    event.schema_id,
                    event.schema_version,
                    _dt(event.timestamp),
                ),
            )
            self.conn.commit()
        return event

    async def append_recovery_event(self, event: RecoveryEvent) -> RecoveryEvent:
        """Append or dedupe a durable recovery lifecycle event."""

        async with self._lock:
            existing = self.conn.execute(
                """
                SELECT *
                FROM recovery_events
                WHERE tenant_id = ?
                  AND idempotency_key = ?
                """,
                (event.tenant_id, event.idempotency_key),
            ).fetchone()

            if existing:
                return self._row_to_recovery_event(existing)

            self.conn.execute(
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(event.payload),
                    event.schema_id,
                    event.schema_version,
                    _dt(event.created_at),
                ),
            )
            self.conn.commit()

        return event

    async def list_recovery_events(
        self,
        tenant_id: str,
        *,
        workflow_id: str | None = None,
        recovery_id: str | None = None,
        event_type: str | None = None,
    ) -> list[RecoveryEvent]:
        """List durable recovery events in deterministic replay order."""

        clauses = ["tenant_id = ?"]
        params: list[Any] = [tenant_id]

        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)

        if recovery_id is not None:
            clauses.append("recovery_id = ?")
            params.append(recovery_id)

        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)

        rows = self.conn.execute(
            f"""
            SELECT *
            FROM recovery_events
            WHERE {' AND '.join(clauses)}
            ORDER BY recovery_id ASC, sequence_no ASC, log_position ASC
            """,
            tuple(params),
        ).fetchall()

        return [self._row_to_recovery_event(row) for row in rows]

    async def record_inbox_event(self, event: ExternalEvent) -> ExternalEvent:
        """Record an inbound event once, deduped by tenant/source/dedupe_key."""
        async with self._lock:
            existing = self.conn.execute(
                """
                SELECT event_id
                FROM event_inbox
                WHERE tenant_id = ? AND source = ? AND dedupe_key = ?
                """,
                (event.tenant_id, event.source, event.dedupe_key),
            ).fetchone()

            if existing:
                return event

            self.conn.execute(
                """
                INSERT INTO event_inbox (
                    event_id,
                    tenant_id,
                    source,
                    dedupe_key,
                    workflow_id,
                    binding_id,
                    payload,
                    schema_id,
                    schema_version,
                    received_at,
                    processed_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.source,
                    event.dedupe_key,
                    event.workflow_id,
                    event.binding_id,
                    json.dumps(event.payload),
                    event.schema_id,
                    event.schema_version,
                    _dt(event.timestamp),
                    None,
                    "received",
                ),
            )
            self.conn.commit()
            return event

    async def has_event(self, tenant_id: str, event_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM event_log WHERE tenant_id=? AND event_id=?",
            (tenant_id, event_id),
        ).fetchone()
        return bool(row)

    async def is_effective(self, tenant_id: str, rid: str) -> bool:
        row = self.conn.execute(
            "SELECT effective FROM effective_record_index WHERE tenant_id=? AND rid=?",
            (tenant_id, rid),
        ).fetchone()
        return bool(row and row["effective"])

    async def get_latest_version(self, tenant_id: str, eid: str, fsm: str) -> int:
        # Authoritative: the append-only ledger, not the cacheable projection.
        row = self.conn.execute(
            "SELECT MAX(version) AS v FROM ctl_records WHERE tenant_id=? AND eid=? AND fsm=?",
            (tenant_id, eid, fsm),
        ).fetchone()
        return int(row["v"]) if row and row["v"] is not None else 0

    async def get_by_op_id(self, tenant_id: str, op_id: str) -> CTLRecord | None:
        if not op_id:
            return None

        row = self.conn.execute(
            "SELECT * FROM ctl_records WHERE tenant_id=? AND op_id=?",
            (tenant_id, op_id),
        ).fetchone()
        return self._row_to_record(row) if row else None

    async def get_effective_dependents(self, tenant_id: str, rid: str) -> list[CTLRecord]:
        """Effective records whose dependencies include rid, across the tenant."""
        rows = self.conn.execute(
            """
            SELECT r.*
            FROM ctl_records r
            JOIN effective_record_index e
              ON e.tenant_id = r.tenant_id
             AND e.rid = r.rid
            WHERE r.tenant_id = ?
              AND e.effective = 1
            """,
            (tenant_id,),
        ).fetchall()

        out: list[CTLRecord] = []

        for row in rows:
            record = self._row_to_record(row)
            if rid in record.dependencies:
                out.append(record)

        return out

    async def get_state_view(self, tenant_id: str, eid: str, fsm: str) -> StateView:
        row = self.conn.execute(
            "SELECT * FROM entity_projection WHERE tenant_id=? AND eid=? AND fsm=?",
            (tenant_id, eid, fsm),
        ).fetchone()

        if not row:
            return StateView(
                tenant_id=tenant_id,
                eid=eid,
                fsm=fsm,
                state=None,
                version=0,
                attrs={},
                effective_records=[],
            )

        return StateView(
            tenant_id=tenant_id,
            eid=eid,
            fsm=fsm,
            state=row["state"],
            version=row["version"],
            attrs=_loads(row["attrs"]) or {},
            effective_records=_loads(row["effective_records"]) or [],
            as_of_log_position=row["as_of_log_position"],
            workflow_id=row["workflow_id"],
            binding_id=row["binding_id"],
        )

    async def get_record(self, tenant_id: str, rid: str) -> CTLRecord | None:
        row = self.conn.execute(
            "SELECT * FROM ctl_records WHERE tenant_id=? AND rid=?",
            (tenant_id, rid),
        ).fetchone()
        return self._row_to_record(row) if row else None

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[CTLRecord]:
        """Effective CTL history for an entity/FSM, in version order."""
        rows = self.conn.execute(
            """
            SELECT r.*
            FROM ctl_records r
            JOIN effective_record_index e
              ON e.tenant_id = r.tenant_id
             AND e.rid = r.rid
            WHERE r.tenant_id = ?
              AND r.eid = ?
              AND r.fsm = ?
              AND e.effective = 1
            ORDER BY r.version ASC
            """,
            (tenant_id, eid, fsm),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_full_entity_history(
        self,
        tenant_id: str,
        eid: str,
        fsm: str,
    ) -> list[CTLRecord]:
        """All committed CTL records for an entity/FSM, including ineffective records."""
        rows = self.conn.execute(
            """
            SELECT *
            FROM ctl_records
            WHERE tenant_id = ?
              AND eid = ?
              AND fsm = ?
            ORDER BY version ASC
            """,
            (tenant_id, eid, fsm),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    async def enqueue_outbox(self, intents: list[OutboxIntent]) -> None:
        async with self._lock:
            self._insert_outbox(intents)
            self.conn.commit()

    async def commit_batch(
        self,
        batch: CommitBatch,
        records: list[CTLRecord],
    ) -> list[CTLRecord]:
        if not records and not batch.outbox_intents:
            return []

        async with self._lock:
            affected: set[tuple[str, str, str]] = set()
            applied_records: list[CTLRecord] = []

            try:
                self.conn.execute("BEGIN")

                for record in records:
                    op_id = record.op_id or record.rid

                    existing = await self.get_by_op_id(record.tenant_id, op_id)
                    if existing:
                        applied_records.append(existing)
                        continue

                    latest = await self.get_latest_version(record.tenant_id, record.eid, record.fsm)
                    if record.version != latest + 1:
                        raise ValueError(
                            f"bad version for {record.eid}/{record.fsm}: "
                            f"got {record.version}, expected {latest + 1}"
                        )

                    for dep in record.dependencies:
                        if not await self.is_effective(record.tenant_id, dep):
                            raise ValueError(f"dependency not effective: {dep}")

                    local_pos = self._next_local_position(record.tenant_id, record.workflow_id)

                    self.conn.execute(
                        """
                        INSERT INTO ctl_records
                        (
                            rid,
                            op_id,
                            tenant_id,
                            tx_group_id,
                            workflow_id,
                            binding_id,
                            eid,
                            fsm,
                            version,
                            state_before,
                            state_after,
                            action_type,
                            triggers,
                            dependencies,
                            metadata,
                            extension,
                            app_id,
                            app_version,
                            schema_id,
                            schema_version,
                            fsm_version,
                            policy_id,
                            policy_version,
                            validator_id,
                            validator_version,
                            timestamp,
                            local_log_position
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.rid,
                            op_id,
                            record.tenant_id,
                            record.tx_group_id,
                            record.workflow_id,
                            record.binding_id,
                            record.eid,
                            record.fsm,
                            record.version,
                            record.state_before,
                            record.state_after,
                            record.action_type,
                            json.dumps(record.triggers),
                            json.dumps(record.dependencies),
                            json.dumps(record.metadata),
                            json.dumps(record.extension),
                            record.app_id,
                            record.app_version,
                            record.schema_id,
                            record.schema_version,
                            record.fsm_version,
                            record.policy_id,
                            record.policy_version,
                            record.validator_id,
                            record.validator_version,
                            _dt(record.timestamp),
                            local_pos,
                        ),
                    )

                    self.conn.execute(
                        """
                        INSERT OR REPLACE INTO effective_record_index
                        (tenant_id, rid, effective, changed_by_rid)
                        VALUES (?, ?, 1, NULL)
                        """,
                        (record.tenant_id, record.rid),
                    )
                    affected.add((record.tenant_id, record.eid, record.fsm))

                    for old in record.metadata.get("compensates", []) + record.metadata.get(
                        "supersedes", []
                    ):
                        old_rec = await self.get_record(record.tenant_id, old)
                        if old_rec is None:
                            raise ValueError(f"compensation target does not exist: {old}")

                        self.conn.execute(
                            """
                            INSERT OR REPLACE INTO effective_record_index
                            (tenant_id, rid, effective, changed_by_rid)
                            VALUES (?, ?, 0, ?)
                            """,
                            (record.tenant_id, old, record.rid),
                        )
                        affected.add((record.tenant_id, old_rec.eid, old_rec.fsm))

                    inserted = await self.get_record(record.tenant_id, record.rid)
                    applied_records.append(inserted or record)

                for tenant_id, eid, fsm in affected:
                    self._reproject(tenant_id, eid, fsm)

                self._assert_no_orphaned_dependents(batch.tenant_id)
                self._insert_outbox(batch.outbox_intents)
                self.conn.commit()

            except Exception:
                self.conn.rollback()
                raise

        return applied_records

    def _next_local_position(self, tenant_id: str, workflow_id: str | None) -> int:
        row = self.conn.execute(
            """
            SELECT COALESCE(MAX(local_log_position), 0) AS m
            FROM ctl_records
            WHERE tenant_id = ?
              AND workflow_id IS ?
            """,
            (tenant_id, workflow_id),
        ).fetchone()
        return int(row["m"]) + 1

    def _insert_outbox(self, intents: list[OutboxIntent]) -> None:
        for intent in intents:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO outbox
                (
                    outbox_id,
                    tenant_id,
                    provider,
                    effect_type,
                    payload,
                    provider_idempotency_key,
                    workflow_id,
                    binding_id,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    intent.outbox_id,
                    intent.tenant_id,
                    intent.provider,
                    intent.effect_type,
                    json.dumps(intent.payload),
                    intent.provider_idempotency_key,
                    intent.workflow_id,
                    intent.binding_id,
                    _dt(intent.created_at),
                ),
            )

    def _reproject(self, tenant_id: str, eid: str, fsm: str) -> None:
        """Rebuild one entity projection from currently effective records."""
        rows = self.conn.execute(
            """
            SELECT r.*
            FROM ctl_records r
            JOIN effective_record_index e
              ON e.tenant_id = r.tenant_id
             AND e.rid = r.rid
            WHERE r.tenant_id = ?
              AND r.eid = ?
              AND r.fsm = ?
              AND e.effective = 1
            ORDER BY r.version ASC
            """,
            (tenant_id, eid, fsm),
        ).fetchall()

        history = [self._row_to_record(row) for row in rows]
        view = replay_state_view(tenant_id, eid, fsm, history)

        self.conn.execute(
            """
            INSERT OR REPLACE INTO entity_projection
            (
                tenant_id,
                eid,
                fsm,
                state,
                version,
                attrs,
                effective_records,
                as_of_log_position,
                workflow_id,
                binding_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                view.tenant_id,
                view.eid,
                view.fsm,
                view.state,
                view.version,
                json.dumps(view.attrs),
                json.dumps(view.effective_records),
                view.as_of_log_position,
                view.workflow_id,
                view.binding_id,
            ),
        )

    def _assert_no_orphaned_dependents(self, tenant_id: str) -> None:
        """Invariant: no effective record may depend on an ineffective record."""
        rows = self.conn.execute(
            """
            SELECT r.*
            FROM ctl_records r
            JOIN effective_record_index e
              ON e.tenant_id = r.tenant_id
             AND e.rid = r.rid
            WHERE r.tenant_id = ?
              AND e.effective = 1
            """,
            (tenant_id,),
        ).fetchall()

        records = [self._row_to_record(row) for row in rows]
        effective_ids = {record.rid for record in records}

        for record in records:
            own_undone = set(record.metadata.get("compensates", [])) | set(
                record.metadata.get("supersedes", [])
            )

            for dep in record.dependencies:
                if dep in own_undone or dep in effective_ids:
                    continue

                exists = self.conn.execute(
                    """
                    SELECT 1
                    FROM ctl_records
                    WHERE tenant_id = ?
                      AND rid = ?
                    """,
                    (tenant_id, dep),
                ).fetchone()

                if exists:
                    raise ValueError(
                        f"effective record {record.rid} depends on ineffective record {dep}"
                    )

    def _row_to_recovery_event(self, row: sqlite3.Row) -> RecoveryEvent:
        return RecoveryEvent(
            event_id=row["event_id"],
            tenant_id=row["tenant_id"],
            workflow_id=row["workflow_id"],
            recovery_id=row["recovery_id"],
            sequence_no=int(row["sequence_no"]),
            event_type=row["event_type"],
            idempotency_key=row["idempotency_key"],
            causality_key=row["causality_key"],
            payload=_loads(row["payload"]) or {},
            schema_id=row["schema_id"],
            schema_version=row["schema_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_record(self, row: sqlite3.Row) -> CTLRecord:
        return CTLRecord(
            log_position=row["log_position"],
            rid=row["rid"],
            op_id=row["op_id"],
            tenant_id=row["tenant_id"],
            tx_group_id=row["tx_group_id"],
            workflow_id=row["workflow_id"],
            binding_id=row["binding_id"],
            eid=row["eid"],
            fsm=row["fsm"],
            version=row["version"],
            state_before=row["state_before"],
            state_after=row["state_after"],
            action_type=row["action_type"],
            triggers=_loads(row["triggers"]) or [],
            dependencies=_loads(row["dependencies"]) or [],
            metadata=_loads(row["metadata"]) or {},
            extension=_loads(row["extension"]) or {},
            app_id=row["app_id"],
            app_version=row["app_version"],
            schema_id=row["schema_id"],
            schema_version=row["schema_version"],
            fsm_version=row["fsm_version"],
            policy_id=row["policy_id"],
            policy_version=row["policy_version"],
            validator_id=row["validator_id"],
            validator_version=row["validator_version"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            local_log_position=row["local_log_position"],
        )