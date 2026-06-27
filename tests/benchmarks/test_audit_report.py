from __future__ import annotations

import json
from pathlib import Path

from mnemosyne.benchmarks.audit_report import (
    build_markdown_report,
    classify_row,
    load_jsonl,
    summarize_rows,
    write_markdown_report,
)


def proposal_conflict_row():
    return {
        "case_id": "conflict-case",
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": [
            "SOLVER_PROPOSAL_CONFLICT",
            "ENTITY_PROPOSAL_CONFLICT",
        ],
        "error_message": "solver proposal conflict detected before commit",
        "details": {
            "observed": {
                "committed": False,
            },
            "solver_certificate": {
                "solver_id": "p1_campus_tour_bruteforce",
                "solver_version": "0.1",
                "feasible": True,
                "objective_name": "minimize_total_minutes",
                "objective_value": 190,
            },
            "plan_proposal": {
                "proposal_id": "proposal:conflict",
                "case_id": "conflict-case",
                "tenant_id": "tenant:test",
                "workflow_id": "workflow:test",
                "entity_id": "entity:shared",
                "app_id": "campus_tour",
                "schema_id": "campus_tour.transition",
                "route": ["S", "D", "A", "B", "L", "S"],
                "steps": [],
                "attrs": {
                    "deadline": "17:00",
                    "total_minutes": 190,
                },
            },
            "proposal_conflicts": {
                "ok": False,
                "conflicts": [
                    {
                        "conflict_type": "ENTITY_PROPOSAL_CONFLICT",
                        "left_proposal_id": "proposal:a",
                        "right_proposal_id": "proposal:b",
                        "scope": "tenant:tenant:test/entity:entity:shared",
                        "message": "two different active proposals target the same entity",
                    }
                ],
            },
        },
        "source_case_path": "tmp/conflict.json",
    }


def stale_world_row():
    return {
        "case_id": "stale-case",
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": [
            "STALE_WORLD_RECONCILIATION",
            "STALE_WORLD_FACT",
        ],
        "error_message": "world reconciliation failed before commit",
        "details": {
            "observed": {
                "committed": False,
            },
            "solver_certificate": {
                "solver_id": "p1_campus_tour_bruteforce",
                "solver_version": "0.1",
                "feasible": True,
            },
            "plan_proposal": {
                "proposal_id": "proposal:stale",
                "case_id": "stale-case",
                "tenant_id": "tenant:test",
                "workflow_id": "workflow:test",
                "entity_id": "entity:test",
                "app_id": "campus_tour",
                "schema_id": "campus_tour.transition",
                "route": ["S", "D", "A", "B", "L", "S"],
                "steps": [],
                "attrs": {
                    "deadline": "17:00",
                    "world_assumptions": [
                        {
                            "key": "deadline",
                            "value": "17:00",
                            "source": "p1_campus_tour_solver",
                        }
                    ],
                },
            },
            "world_reconciliation": {
                "ok": False,
                "issues": [
                    {
                        "issue_type": "STALE_WORLD_FACT",
                        "tenant_id": "tenant:test",
                        "entity_id": "entity:test",
                        "key": "deadline",
                        "expected_value": "17:00",
                        "observed_value": "11:00",
                        "message": "observed world fact differs from proposal assumption",
                    }
                ],
            },
        },
        "source_case_path": "tmp/stale.json",
    }


def success_row():
    return {
        "case_id": "success-case",
        "ok": True,
        "committed_rids": ["rid-1"],
        "metrics": {
            "final_state": "completed",
        },
        "error_codes": [],
        "details": {
            "observed": {
                "committed": True,
            }
        },
    }


def test_classify_rows():
    assert classify_row(proposal_conflict_row()) == "proposal_conflict_rejection"
    assert classify_row(stale_world_row()) == "stale_world_rejection"
    assert classify_row(success_row()) == "committed_or_expected_success"


def test_summarize_rows():
    rows = [
        success_row(),
        proposal_conflict_row(),
        stale_world_row(),
    ]

    summary = summarize_rows(rows)

    assert summary["total"] == 3
    assert summary["ok"] == 1
    assert summary["failed"] == 2
    assert summary["committed"] == 1
    assert summary["rejected_before_commit"] == 2
    assert summary["by_error_code"]["ENTITY_PROPOSAL_CONFLICT"] == 1
    assert summary["by_error_code"]["STALE_WORLD_FACT"] == 1


def test_build_markdown_report_renders_rejection_evidence():
    rows = [
        proposal_conflict_row(),
        stale_world_row(),
    ]

    markdown = build_markdown_report(
        rows=rows,
        title="R2.4 Audit Report",
    )

    assert "# R2.4 Audit Report" in markdown
    assert "proposal_conflict_rejection" in markdown
    assert "stale_world_rejection" in markdown
    assert "ENTITY_PROPOSAL_CONFLICT" in markdown
    assert "STALE_WORLD_FACT" in markdown
    assert "Proposal conflict analysis" in markdown
    assert "World reconciliation" in markdown
    assert "expected=`17:00`" in markdown
    assert "observed=`11:00`" in markdown
    assert "No committed records should appear" in markdown


def test_write_and_load_audit_report(tmp_path: Path):
    jsonl_path = tmp_path / "rows.jsonl"
    report_path = tmp_path / "audit.md"

    rows = [
        proposal_conflict_row(),
        stale_world_row(),
    ]

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    loaded = load_jsonl(jsonl_path)

    assert len(loaded) == 2

    write_markdown_report(
        rows=loaded,
        output_path=report_path,
        title="Audit",
    )

    rendered = report_path.read_text(encoding="utf-8")

    assert "Audit" in rendered
    assert "rejected before commit: `2`" in rendered
    assert "proposal:conflict" in rendered
    assert "proposal:stale" in rendered
