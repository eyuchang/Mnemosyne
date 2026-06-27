from __future__ import annotations

import sqlite3

import pytest

from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository


def seed_registry(repo: SQLiteRuntimeRepository) -> dict[str, str]:
    ids = {
        "tenant_id": "tenant:r4",
        "workflow_id": "workflow:r4",
        "binding_id": "binding:r4",
        "agent_id": "agent:r4",
        "agent_binding_id": "agent-binding:r4",
        "entity_id": "entity:r4",
        "fsm": "CampusTourFSM",
        "app_id": "campus_tour",
        "schema_id": "campus_tour.transition",
    }

    repo.create_workflow(
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        metadata={"purpose": "r4-test"},
    )

    repo.create_workflow_binding(
        binding_id=ids["binding_id"],
        workflow_id=ids["workflow_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    repo.create_agent(
        agent_id=ids["agent_id"],
        tenant_id=ids["tenant_id"],
        agent_type="planner",
        display_name="Planner",
    )

    repo.create_agent_binding(
        agent_binding_id=ids["agent_binding_id"],
        agent_id=ids["agent_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
    )

    return ids


def submit_demo_proposal(repo: SQLiteRuntimeRepository, ids: dict[str, str]) -> str:
    proposal_id = "proposal:r4"

    repo.submit_proposal(
        proposal_id=proposal_id,
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        agent_binding_id=ids["agent_binding_id"],
        tenant_id=ids["tenant_id"],
        entity_id=ids["entity_id"],
        fsm=ids["fsm"],
        app_id=ids["app_id"],
        schema_id=ids["schema_id"],
        payload={"route": ["S", "D", "A", "B", "L", "S"]},
        metadata={"source": "test"},
    )

    return proposal_id


def test_repository_create_and_get_registry_records(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)

    workflow = repo.get_workflow(ids["workflow_id"])
    binding = repo.get_workflow_binding(ids["binding_id"])
    agent = repo.get_agent(ids["agent_id"])
    agent_binding = repo.get_agent_binding(ids["agent_binding_id"])

    assert workflow is not None
    assert workflow["metadata"] == {"purpose": "r4-test"}
    assert binding is not None
    assert binding["entity_id"] == ids["entity_id"]
    assert agent is not None
    assert agent["display_name"] == "Planner"
    assert agent_binding is not None
    assert agent_binding["workflow_id"] == ids["workflow_id"]


def test_repository_submit_proposal_records_trace(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)
    proposal_id = submit_demo_proposal(repo, ids)

    proposal = repo.get_proposal(proposal_id)
    assert proposal is not None
    assert proposal["status"] == "submitted"
    assert proposal["payload"] == {"route": ["S", "D", "A", "B", "L", "S"]}

    by_workflow = repo.list_proposals_for_workflow(ids["workflow_id"])
    by_agent = repo.list_proposals_for_agent(ids["agent_id"])
    assert [row["proposal_id"] for row in by_workflow] == [proposal_id]
    assert [row["proposal_id"] for row in by_agent] == [proposal_id]

    traces = repo.list_trace_events(proposal_id=proposal_id)
    assert len(traces) == 1
    assert traces[0]["event_type"] == "proposal_submitted"

    status = repo.runtime_status()
    assert status == {
        "proposal_count": 1,
        "decision_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "trace_event_count": 1,
    }


def test_repository_record_accepted_decision_updates_status_and_trace(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)
    proposal_id = submit_demo_proposal(repo, ids)

    repo.record_decision(
        decision_id="decision:r4:accepted",
        proposal_id=proposal_id,
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        decision="accepted",
        reason="validated commit",
        committed_rids=["rid:1"],
        error_codes=[],
        metadata={"kernel_commit_performed": True},
    )

    proposal = repo.get_proposal(proposal_id)
    decision = repo.get_decision_for_proposal(proposal_id)
    traces = repo.list_trace_events(proposal_id=proposal_id)

    assert proposal is not None
    assert proposal["status"] == "accepted"
    assert decision is not None
    assert decision["decision"] == "accepted"
    assert decision["committed_rids"] == ["rid:1"]
    assert decision["error_codes"] == []
    assert decision["metadata"] == {"kernel_commit_performed": True}
    assert [trace["event_type"] for trace in traces] == [
        "proposal_submitted",
        "admission_accepted",
    ]

    assert repo.runtime_status() == {
        "proposal_count": 1,
        "decision_count": 1,
        "accepted_count": 1,
        "rejected_count": 0,
        "trace_event_count": 2,
    }


def test_repository_record_rejected_decision_updates_status_and_trace(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)
    proposal_id = submit_demo_proposal(repo, ids)

    repo.record_decision(
        decision_id="decision:r4:rejected",
        proposal_id=proposal_id,
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        decision="rejected",
        reason="domain infeasible",
        committed_rids=[],
        error_codes=["DOMAIN_FEASIBILITY_REJECTED"],
    )

    proposal = repo.get_proposal(proposal_id)
    decision = repo.get_decision("decision:r4:rejected")
    traces = repo.list_trace_events(proposal_id=proposal_id)

    assert proposal is not None
    assert proposal["status"] == "rejected"
    assert decision is not None
    assert decision["committed_rids"] == []
    assert decision["error_codes"] == ["DOMAIN_FEASIBILITY_REJECTED"]
    assert [trace["event_type"] for trace in traces] == [
        "proposal_submitted",
        "admission_rejected",
    ]


def test_repository_persists_across_reopen(tmp_path):
    db_path = tmp_path / "runtime.sqlite3"

    repo1 = SQLiteRuntimeRepository(db_path)
    ids = seed_registry(repo1)
    proposal_id = submit_demo_proposal(repo1, ids)

    repo1.record_decision(
        decision_id="decision:r4:accepted",
        proposal_id=proposal_id,
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        decision="accepted",
        reason="validated commit",
        committed_rids=["rid:1"],
        error_codes=[],
    )

    repo2 = SQLiteRuntimeRepository(db_path)

    assert repo2.get_workflow(ids["workflow_id"]) is not None
    assert repo2.get_proposal(proposal_id)["status"] == "accepted"
    assert repo2.get_decision_for_proposal(proposal_id)["committed_rids"] == ["rid:1"]
    assert len(repo2.list_trace_events(proposal_id=proposal_id)) == 2


def test_repository_rejects_duplicate_proposal_and_second_decision(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)
    proposal_id = submit_demo_proposal(repo, ids)

    with pytest.raises(sqlite3.IntegrityError):
        submit_demo_proposal(repo, ids)

    repo.record_decision(
        decision_id="decision:r4:accepted",
        proposal_id=proposal_id,
        tenant_id=ids["tenant_id"],
        workflow_id=ids["workflow_id"],
        binding_id=ids["binding_id"],
        agent_id=ids["agent_id"],
        decision="accepted",
        reason="validated commit",
        committed_rids=["rid:1"],
        error_codes=[],
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.record_decision(
            decision_id="decision:r4:second",
            proposal_id=proposal_id,
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            decision="rejected",
            reason="second decision forbidden",
            committed_rids=[],
            error_codes=["SECOND_DECISION_FORBIDDEN"],
        )


def test_repository_rejects_malformed_accepted_decision(tmp_path):
    repo = SQLiteRuntimeRepository(tmp_path / "runtime.sqlite3")
    ids = seed_registry(repo)
    proposal_id = submit_demo_proposal(repo, ids)

    with pytest.raises(sqlite3.IntegrityError):
        repo.record_decision(
            decision_id="decision:r4:bad",
            proposal_id=proposal_id,
            tenant_id=ids["tenant_id"],
            workflow_id=ids["workflow_id"],
            binding_id=ids["binding_id"],
            agent_id=ids["agent_id"],
            decision="accepted",
            reason="missing committed ids",
            committed_rids=[],
            error_codes=[],
        )
