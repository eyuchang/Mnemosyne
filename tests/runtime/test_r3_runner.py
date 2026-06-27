from __future__ import annotations

from pathlib import Path

from mnemosyne.runtime.r3_runner import (
    render_markdown_report,
    run_runtime_command_demo,
    write_runtime_command_demo_artifacts,
)


def test_run_runtime_command_demo_produces_command_shaped_evidence():
    result = run_runtime_command_demo()

    assert result["stage"] == "R3.7"
    assert result["demo_id"] == "runtime_command_demo_001"
    assert result["all_commands_ok"] is True
    assert result["command_count"] == 10

    command_types = [
        item["command_type"]
        for item in result["command_results"]
    ]

    assert command_types == [
        "CreateWorkflowCommand",
        "BindWorkflowCommand",
        "CreateAgentCommand",
        "BindAgentCommand",
        "SubmitProposalCommand",
        "AcceptProposalCommand",
        "SubmitProposalCommand",
        "RejectProposalCommand",
        "QueryWorkflowStatusCommand",
        "ListTraceEventsCommand",
    ]

    status = result["runtime_status"]
    assert status["workflow_id"] == "workflow:r3-command-demo"
    assert status["proposal_count"] == 2
    assert status["decision_count"] == 2
    assert status["accepted_count"] == 1
    assert status["rejected_count"] == 1
    assert status["trace_event_count"] == 4

    trace_types = [
        event["event_type"]
        for event in result["trace_events"]
    ]

    assert trace_types == [
        "proposal_submitted",
        "admission_accepted",
        "proposal_submitted",
        "admission_rejected",
    ]


def test_render_markdown_report_contains_command_and_trace_evidence():
    result = run_runtime_command_demo()
    report = render_markdown_report(result)

    assert "# R3.7 Runtime Command Demo" in report
    assert "CreateWorkflowCommand" in report
    assert "SubmitProposalCommand" in report
    assert "AcceptProposalCommand" in report
    assert "RejectProposalCommand" in report
    assert "admission_accepted" in report
    assert "admission_rejected" in report
    assert "not production runtime" in report


def test_write_runtime_command_demo_artifacts(tmp_path: Path):
    results_path = tmp_path / "results" / "r3" / "runtime_command_demo_001.json"
    report_path = tmp_path / "reports" / "r3" / "runtime_command_demo_001.md"

    result = write_runtime_command_demo_artifacts(
        results_path=results_path,
        report_path=report_path,
    )

    assert result["demo_id"] == "runtime_command_demo_001"
    assert results_path.exists()
    assert report_path.exists()

    results_text = results_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")

    assert '"stage": "R3.7"' in results_text
    assert "Runtime Command Demo" in report_text
    assert "admission_rejected" in results_text
    assert "RejectProposalCommand" in report_text
