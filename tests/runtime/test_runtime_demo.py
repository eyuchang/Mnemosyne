from __future__ import annotations

from pathlib import Path

from mnemosyne.runtime.demo import (
    render_markdown_report,
    run_local_runtime_demo,
    write_local_runtime_demo_artifacts,
)


def test_run_local_runtime_demo_produces_integrated_runtime_evidence():
    result = run_local_runtime_demo()

    assert result["stage"] == "R3.5"
    assert result["workflow_id"] == "workflow:r3-local-demo"
    assert result["agent_id"] == "agent:r3-planner"

    status = result["runtime_status"]
    assert status["proposal_count"] == 2
    assert status["decision_count"] == 2
    assert status["accepted_count"] == 1
    assert status["rejected_count"] == 1
    assert status["trace_event_count"] == 4

    assert result["accepted_decision"]["accepted"] is True
    assert result["accepted_decision"]["metadata"]["kernel_commit_performed"] is False

    assert result["rejected_decision"]["accepted"] is False
    assert result["rejected_decision"]["committed_rids"] == ()
    assert "DOMAIN_FEASIBILITY_REJECTED" in result["rejected_decision"]["error_codes"]

    trace_types = [event["event_type"] for event in result["trace_events"]]
    assert trace_types == [
        "proposal_submitted",
        "admission_accepted",
        "proposal_submitted",
        "admission_rejected",
    ]


def test_render_markdown_report_contains_key_evidence():
    result = run_local_runtime_demo()
    report = render_markdown_report(result)

    assert "# R3.5 Local Runtime Demo" in report
    assert "workflow:r3-local-demo" in report
    assert "Accepted count" in report
    assert "Rejected count" in report
    assert "DOMAIN_FEASIBILITY_REJECTED" in report
    assert "not production runtime yet" in report


def test_write_local_runtime_demo_artifacts(tmp_path: Path):
    results_path = tmp_path / "results" / "r3" / "local_runtime_demo_001.json"
    report_path = tmp_path / "reports" / "r3" / "local_runtime_demo_001.md"

    result = write_local_runtime_demo_artifacts(
        results_path=results_path,
        report_path=report_path,
    )

    assert result["demo_id"] == "local_runtime_demo_001"
    assert results_path.exists()
    assert report_path.exists()

    results_text = results_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert '"stage": "R3.5"' in results_text
    assert "R3.5 Local Runtime Demo" in report_text
    assert "proposal_submitted" in results_text
    assert "admission_rejected" in results_text
