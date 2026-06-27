from __future__ import annotations

from mnemosyne.runtime.r4_recovery_demo import run_demo


def test_r4_recovery_demo_recovers_runtime_metadata(tmp_path):
    result = run_demo(tmp_path / "runtime_recovery.sqlite3")

    assert result["pass"] is True
    assert result["checks"] == {
        "workflow_recovered": True,
        "workflow_binding_recovered": True,
        "agent_recovered": True,
        "agent_binding_recovered": True,
        "proposal_recovered": True,
        "decision_recovered": True,
        "trace_events_recovered": True,
        "status_counts_match": True,
        "proposal_status_recovered": True,
        "decision_committed_rids_recovered": True,
    }

    assert result["before"]["runtime_status"] == {
        "proposal_count": 1,
        "decision_count": 1,
        "accepted_count": 1,
        "rejected_count": 0,
        "trace_event_count": 2,
    }

    assert result["after"]["runtime_status"] == result["before"]["runtime_status"]
    assert result["after"]["proposal"]["status"] == "accepted"
    assert result["after"]["decision"]["committed_rids"] == ["rid:r4-recovery-demo"]
    assert [event["event_type"] for event in result["after"]["trace_events"]] == [
        "proposal_submitted",
        "admission_accepted",
    ]
