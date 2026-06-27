from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from mnemosyne.runtime.persistence import RuntimePersistence


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _load_json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    return json.loads(value)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    data = dict(row)

    for key in list(data):
        if key.endswith("_json"):
            plain_key = key[:-5]
            default: Any = [] if key.endswith("_rids_json") or key.endswith("_codes_json") else {}
            data[plain_key] = _load_json(data[key], default)

    return data


class SQLiteRuntimeRepository:
    """Durable R4 repository for runtime metadata.

    This repository persists workflow, agent, proposal, admission-decision,
    and trace metadata. It does not validate domain truth, write CTL, or bypass
    the correctness kernel.
    """

    def __init__(self, db_path: str | Path):
        self.persistence = RuntimePersistence(db_path)
        self.persistence.initialize()

    def connect(self) -> sqlite3.Connection:
        return self.persistence.connect()

    def create_workflow(
        self,
        *,
        workflow_id: str,
        tenant_id: str,
        fsm: str,
        app_id: str,
        schema_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_workflows (
                    workflow_id, tenant_id, fsm, app_id, schema_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    tenant_id,
                    fsm,
                    app_id,
                    schema_id,
                    _json(metadata or {}),
                ),
            )

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        return _row_to_dict(row)

    def create_workflow_binding(
        self,
        *,
        binding_id: str,
        workflow_id: str,
        tenant_id: str,
        entity_id: str,
        fsm: str,
        app_id: str,
        schema_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_workflow_bindings (
                    binding_id, workflow_id, tenant_id, entity_id,
                    fsm, app_id, schema_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding_id,
                    workflow_id,
                    tenant_id,
                    entity_id,
                    fsm,
                    app_id,
                    schema_id,
                    _json(metadata or {}),
                ),
            )

    def get_workflow_binding(self, binding_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_workflow_bindings WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        return _row_to_dict(row)

    def create_agent(
        self,
        *,
        agent_id: str,
        tenant_id: str,
        agent_type: str,
        display_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_agents (
                    agent_id, tenant_id, agent_type, display_name, metadata_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    agent_id,
                    tenant_id,
                    agent_type,
                    display_name,
                    _json(metadata or {}),
                ),
            )

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return _row_to_dict(row)

    def create_agent_binding(
        self,
        *,
        agent_binding_id: str,
        agent_id: str,
        workflow_id: str,
        binding_id: str,
        tenant_id: str,
        entity_id: str,
        fsm: str,
        app_id: str,
        schema_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_agent_bindings (
                    agent_binding_id, agent_id, workflow_id, binding_id,
                    tenant_id, entity_id, fsm, app_id, schema_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_binding_id,
                    agent_id,
                    workflow_id,
                    binding_id,
                    tenant_id,
                    entity_id,
                    fsm,
                    app_id,
                    schema_id,
                    _json(metadata or {}),
                ),
            )

    def get_agent_binding(self, agent_binding_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_agent_bindings WHERE agent_binding_id = ?",
                (agent_binding_id,),
            ).fetchone()
        return _row_to_dict(row)

    def submit_proposal(
        self,
        *,
        proposal_id: str,
        workflow_id: str,
        binding_id: str,
        agent_id: str,
        agent_binding_id: str,
        tenant_id: str,
        entity_id: str,
        fsm: str,
        app_id: str,
        schema_id: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_proposals (
                    proposal_id, workflow_id, binding_id, agent_id, agent_binding_id,
                    tenant_id, entity_id, fsm, app_id, schema_id,
                    payload_json, metadata_json, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'submitted')
                """,
                (
                    proposal_id,
                    workflow_id,
                    binding_id,
                    agent_id,
                    agent_binding_id,
                    tenant_id,
                    entity_id,
                    fsm,
                    app_id,
                    schema_id,
                    _json(payload),
                    _json(metadata or {}),
                ),
            )
            self._append_trace_event_with_conn(
                conn,
                proposal_id=proposal_id,
                decision_id=None,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                binding_id=binding_id,
                agent_id=agent_id,
                event_type="proposal_submitted",
                event={"proposal_id": proposal_id},
            )

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        return _row_to_dict(row)

    def list_proposals_for_workflow(self, workflow_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_proposals
                WHERE workflow_id = ?
                ORDER BY created_at, proposal_id
                """,
                (workflow_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows if row is not None]

    def list_proposals_for_agent(self, agent_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_proposals
                WHERE agent_id = ?
                ORDER BY created_at, proposal_id
                """,
                (agent_id,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows if row is not None]

    def record_decision(
        self,
        *,
        decision_id: str,
        proposal_id: str,
        tenant_id: str,
        workflow_id: str,
        binding_id: str,
        agent_id: str,
        decision: str,
        reason: str,
        committed_rids: list[str] | None = None,
        error_codes: list[str] | None = None,
        audit_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if decision not in {"accepted", "rejected"}:
            raise ValueError(f"Unsupported decision: {decision}")

        committed_rids = committed_rids or []
        error_codes = error_codes or []

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_admission_decisions (
                    decision_id, proposal_id, tenant_id, workflow_id, binding_id,
                    agent_id, decision, reason, committed_rids_json,
                    error_codes_json, audit_ref, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    proposal_id,
                    tenant_id,
                    workflow_id,
                    binding_id,
                    agent_id,
                    decision,
                    reason,
                    _json(committed_rids),
                    _json(error_codes),
                    audit_ref,
                    _json(metadata or {}),
                ),
            )

            conn.execute(
                """
                UPDATE runtime_proposals
                SET status = ?
                WHERE proposal_id = ?
                """,
                (decision, proposal_id),
            )

            self._append_trace_event_with_conn(
                conn,
                proposal_id=proposal_id,
                decision_id=decision_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                binding_id=binding_id,
                agent_id=agent_id,
                event_type=f"admission_{decision}",
                event={
                    "proposal_id": proposal_id,
                    "decision_id": decision_id,
                    "decision": decision,
                    "reason": reason,
                    "committed_rids": committed_rids,
                    "error_codes": error_codes,
                },
            )

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM runtime_admission_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
        return _row_to_dict(row)

    def get_decision_for_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_admission_decisions
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()
        return _row_to_dict(row)

    def append_trace_event(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        event_type: str,
        event: dict[str, Any] | None = None,
        proposal_id: str | None = None,
        decision_id: str | None = None,
        binding_id: str | None = None,
        agent_id: str | None = None,
        trace_event_id: str | None = None,
    ) -> str:
        with self.connect() as conn:
            return self._append_trace_event_with_conn(
                conn,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                event_type=event_type,
                event=event or {},
                proposal_id=proposal_id,
                decision_id=decision_id,
                binding_id=binding_id,
                agent_id=agent_id,
                trace_event_id=trace_event_id,
            )

    def _append_trace_event_with_conn(
        self,
        conn: sqlite3.Connection,
        *,
        tenant_id: str,
        workflow_id: str,
        event_type: str,
        event: dict[str, Any],
        proposal_id: str | None = None,
        decision_id: str | None = None,
        binding_id: str | None = None,
        agent_id: str | None = None,
        trace_event_id: str | None = None,
    ) -> str:
        trace_event_id = trace_event_id or f"trace:{uuid.uuid4().hex}"

        conn.execute(
            """
            INSERT INTO runtime_trace_events (
                trace_event_id, proposal_id, decision_id, tenant_id,
                workflow_id, binding_id, agent_id, event_type, event_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_event_id,
                proposal_id,
                decision_id,
                tenant_id,
                workflow_id,
                binding_id,
                agent_id,
                event_type,
                _json(event),
            ),
        )

        return trace_event_id

    def list_trace_events(
        self,
        *,
        workflow_id: str | None = None,
        proposal_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT rowid AS _rowid, * FROM runtime_trace_events"
        params: list[Any] = []
        clauses: list[str] = []

        if workflow_id is not None:
            clauses.append("workflow_id = ?")
            params.append(workflow_id)

        if proposal_id is not None:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY _rowid"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_dict(row) for row in rows if row is not None]

    def runtime_status(self) -> dict[str, int]:
        with self.connect() as conn:
            proposal_count = conn.execute(
                "SELECT COUNT(*) AS n FROM runtime_proposals"
            ).fetchone()["n"]
            decision_count = conn.execute(
                "SELECT COUNT(*) AS n FROM runtime_admission_decisions"
            ).fetchone()["n"]
            accepted_count = conn.execute(
                "SELECT COUNT(*) AS n FROM runtime_admission_decisions WHERE decision = 'accepted'"
            ).fetchone()["n"]
            rejected_count = conn.execute(
                "SELECT COUNT(*) AS n FROM runtime_admission_decisions WHERE decision = 'rejected'"
            ).fetchone()["n"]
            trace_event_count = conn.execute(
                "SELECT COUNT(*) AS n FROM runtime_trace_events"
            ).fetchone()["n"]

        return {
            "proposal_count": int(proposal_count),
            "decision_count": int(decision_count),
            "accepted_count": int(accepted_count),
            "rejected_count": int(rejected_count),
            "trace_event_count": int(trace_event_count),
        }
