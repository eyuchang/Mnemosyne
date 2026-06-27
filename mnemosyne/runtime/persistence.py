from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


RUNTIME_TABLES = (
    "runtime_workflows",
    "runtime_workflow_bindings",
    "runtime_agents",
    "runtime_agent_bindings",
    "runtime_proposals",
    "runtime_admission_decisions",
    "runtime_trace_events",
)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runtime_workflows (
    workflow_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    fsm TEXT NOT NULL,
    app_id TEXT NOT NULL,
    schema_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runtime_workflow_bindings (
    binding_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    fsm TEXT NOT NULL,
    app_id TEXT NOT NULL,
    schema_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES runtime_workflows(workflow_id)
);

CREATE TABLE IF NOT EXISTS runtime_agents (
    agent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runtime_agent_bindings (
    agent_binding_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    fsm TEXT NOT NULL,
    app_id TEXT NOT NULL,
    schema_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES runtime_agents(agent_id),
    FOREIGN KEY (workflow_id) REFERENCES runtime_workflows(workflow_id),
    FOREIGN KEY (binding_id) REFERENCES runtime_workflow_bindings(binding_id)
);

CREATE TABLE IF NOT EXISTS runtime_proposals (
    proposal_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_binding_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    fsm TEXT NOT NULL,
    app_id TEXT NOT NULL,
    schema_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'submitted',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES runtime_workflows(workflow_id),
    FOREIGN KEY (binding_id) REFERENCES runtime_workflow_bindings(binding_id),
    FOREIGN KEY (agent_id) REFERENCES runtime_agents(agent_id),
    FOREIGN KEY (agent_binding_id) REFERENCES runtime_agent_bindings(agent_binding_id),
    CHECK (status IN ('submitted', 'accepted', 'rejected'))
);

CREATE TABLE IF NOT EXISTS runtime_admission_decisions (
    decision_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    committed_rids_json TEXT NOT NULL DEFAULT '[]',
    error_codes_json TEXT NOT NULL DEFAULT '[]',
    audit_ref TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES runtime_proposals(proposal_id),
    FOREIGN KEY (workflow_id) REFERENCES runtime_workflows(workflow_id),
    FOREIGN KEY (binding_id) REFERENCES runtime_workflow_bindings(binding_id),
    FOREIGN KEY (agent_id) REFERENCES runtime_agents(agent_id),
    CHECK (decision IN ('accepted', 'rejected')),
    CHECK (
        (decision = 'accepted' AND committed_rids_json != '[]' AND error_codes_json = '[]')
        OR
        (decision = 'rejected' AND committed_rids_json = '[]')
    )
);

CREATE TABLE IF NOT EXISTS runtime_trace_events (
    trace_event_id TEXT PRIMARY KEY,
    proposal_id TEXT,
    decision_id TEXT,
    tenant_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    binding_id TEXT,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    event_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES runtime_proposals(proposal_id),
    FOREIGN KEY (decision_id) REFERENCES runtime_admission_decisions(decision_id),
    FOREIGN KEY (workflow_id) REFERENCES runtime_workflows(workflow_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_workflows_tenant
    ON runtime_workflows(tenant_id);

CREATE INDEX IF NOT EXISTS idx_runtime_bindings_workflow
    ON runtime_workflow_bindings(workflow_id);

CREATE INDEX IF NOT EXISTS idx_runtime_agent_bindings_workflow
    ON runtime_agent_bindings(workflow_id);

CREATE INDEX IF NOT EXISTS idx_runtime_proposals_workflow
    ON runtime_proposals(workflow_id);

CREATE INDEX IF NOT EXISTS idx_runtime_proposals_agent
    ON runtime_proposals(agent_id);

CREATE INDEX IF NOT EXISTS idx_runtime_decisions_proposal
    ON runtime_admission_decisions(proposal_id);

CREATE INDEX IF NOT EXISTS idx_runtime_trace_proposal
    ON runtime_trace_events(proposal_id);

CREATE INDEX IF NOT EXISTS idx_runtime_trace_workflow
    ON runtime_trace_events(workflow_id);
"""


class RuntimePersistence:
    """SQLite persistence boundary for R4 runtime metadata.

    This layer creates durable tables only. It does not commit truth,
    validate proposals, call CTL, or bypass the kernel.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def table_names(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        return {str(row["name"]) for row in rows}

    def missing_tables(self, expected: Iterable[str] = RUNTIME_TABLES) -> set[str]:
        return set(expected) - self.table_names()
