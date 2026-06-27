from __future__ import annotations

import json
import sqlite3

import pytest

from mnemosyne.runtime.persistence import RuntimePersistence, RUNTIME_TABLES


def test_runtime_persistence_creates_expected_tables(tmp_path):
    db_path = tmp_path / "runtime.sqlite3"
    persistence = RuntimePersistence(db_path)

    persistence.initialize()

    assert persistence.missing_tables() == set()
    assert set(RUNTIME_TABLES).issubset(persistence.table_names())


def test_runtime_persistence_enforces_foreign_keys(tmp_path):
    db_path = tmp_path / "runtime.sqlite3"
    persistence = RuntimePersistence(db_path)
    persistence.initialize()

    with persistence.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO runtime_workflow_bindings (
                    binding_id,
                    workflow_id,
                    tenant_id,
                    entity_id,
                    fsm,
                    app_id,
                    schema_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "binding:missing-workflow",
                    "workflow:missing",
                    "tenant:t1",
                    "entity:e1",
                    "CampusTourFSM",
                    "campus_tour",
                    "campus_tour.transition",
                ),
            )


def test_runtime_persistence_enforces_one_decision_per_proposal(tmp_path):
    db_path = tmp_path / "runtime.sqlite3"
    persistence = RuntimePersistence(db_path)
    persistence.initialize()

    with persistence.connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_workflows (
                workflow_id, tenant_id, fsm, app_id, schema_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "workflow:1",
                "tenant:t1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_workflow_bindings (
                binding_id, workflow_id, tenant_id, entity_id, fsm, app_id, schema_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "binding:1",
                "workflow:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_agents (
                agent_id, tenant_id, agent_type, display_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "agent:1",
                "tenant:t1",
                "planner",
                "Planner",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_agent_bindings (
                agent_binding_id,
                agent_id,
                workflow_id,
                binding_id,
                tenant_id,
                entity_id,
                fsm,
                app_id,
                schema_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent-binding:1",
                "agent:1",
                "workflow:1",
                "binding:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_proposals (
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
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "proposal:1",
                "workflow:1",
                "binding:1",
                "agent:1",
                "agent-binding:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
                json.dumps({"proposal": "demo"}),
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_admission_decisions (
                decision_id,
                proposal_id,
                tenant_id,
                workflow_id,
                binding_id,
                agent_id,
                decision,
                reason,
                committed_rids_json,
                error_codes_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "decision:1",
                "proposal:1",
                "tenant:t1",
                "workflow:1",
                "binding:1",
                "agent:1",
                "accepted",
                "accepted for test",
                json.dumps(["rid:1"]),
                json.dumps([]),
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO runtime_admission_decisions (
                    decision_id,
                    proposal_id,
                    tenant_id,
                    workflow_id,
                    binding_id,
                    agent_id,
                    decision,
                    reason,
                    committed_rids_json,
                    error_codes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision:2",
                    "proposal:1",
                    "tenant:t1",
                    "workflow:1",
                    "binding:1",
                    "agent:1",
                    "rejected",
                    "second decision should fail",
                    json.dumps([]),
                    json.dumps(["SECOND_DECISION_FORBIDDEN"]),
                ),
            )


def test_runtime_persistence_rejects_accepted_decision_without_committed_rids(tmp_path):
    db_path = tmp_path / "runtime.sqlite3"
    persistence = RuntimePersistence(db_path)
    persistence.initialize()

    with persistence.connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_workflows (
                workflow_id, tenant_id, fsm, app_id, schema_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "workflow:1",
                "tenant:t1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_workflow_bindings (
                binding_id, workflow_id, tenant_id, entity_id, fsm, app_id, schema_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "binding:1",
                "workflow:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_agents (
                agent_id, tenant_id, agent_type, display_name
            )
            VALUES (?, ?, ?, ?)
            """,
            ("agent:1", "tenant:t1", "planner", "Planner"),
        )

        conn.execute(
            """
            INSERT INTO runtime_agent_bindings (
                agent_binding_id, agent_id, workflow_id, binding_id,
                tenant_id, entity_id, fsm, app_id, schema_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent-binding:1",
                "agent:1",
                "workflow:1",
                "binding:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
            ),
        )

        conn.execute(
            """
            INSERT INTO runtime_proposals (
                proposal_id, workflow_id, binding_id, agent_id, agent_binding_id,
                tenant_id, entity_id, fsm, app_id, schema_id, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "proposal:1",
                "workflow:1",
                "binding:1",
                "agent:1",
                "agent-binding:1",
                "tenant:t1",
                "entity:e1",
                "CampusTourFSM",
                "campus_tour",
                "campus_tour.transition",
                json.dumps({"proposal": "demo"}),
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO runtime_admission_decisions (
                    decision_id,
                    proposal_id,
                    tenant_id,
                    workflow_id,
                    binding_id,
                    agent_id,
                    decision,
                    reason,
                    committed_rids_json,
                    error_codes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision:bad",
                    "proposal:1",
                    "tenant:t1",
                    "workflow:1",
                    "binding:1",
                    "agent:1",
                    "accepted",
                    "accepted without committed rids should fail",
                    json.dumps([]),
                    json.dumps([]),
                ),
            )
