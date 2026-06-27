# File: tests/benchmarks/test_p1_solver_runner.py
#
# Purpose:
#   Verify R0.2 and R2.0 P1 solver CLI/report path.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.p1_solver_runner import main


@pytest.mark.realm
def test_p1_solver_runner_writes_jsonl(tmp_path: Path):
    output_path = tmp_path / "p1_solver.jsonl"

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 1

    row = rows[0]

    assert row["case_id"] == "local-p1-compatible-campus-tour-solver-001"
    assert row["ok"] is True
    assert row["error_codes"] == []
    assert row["metrics"]["final_state"] == "completed"

    assert row["details"]["official_realm_bench"] is False
    assert row["details"]["p1_trace"]["feasible"] is True
    assert row["details"]["p1_trace"]["route"] == ["S", "D", "A", "B", "L", "S"]
    assert row["details"]["p1_trace"]["finish_time"] == "12:10"
    assert row["details"]["observed"]["committed"] is True

    assert row["source_case_path"].endswith(
        "benchmarks/realm/p1_solver/campus_tour_solver_001.json"
    )

    assert row["solver_certificate"]["solver_id"] == "p1_campus_tour_bruteforce"
    assert row["solver_certificate"]["solver_version"] == "0.1"
    assert row["solver_certificate"]["feasible"] is True
    assert row["solver_certificate"]["optimality_status"] == "optimal_for_enumerated_space"
    assert row["solver_certificate"]["objective_name"] == "minimize_total_minutes"
    assert row["solver_certificate"]["objective_value"] == 190

    assert row["plan_proposal"]["proposal_id"] == (
        "proposal:local-p1-compatible-campus-tour-solver-001"
    )
    assert row["plan_proposal"]["route"] == ["S", "D", "A", "B", "L", "S"]


@pytest.mark.realm
def test_p1_solver_runner_output_can_be_reported(tmp_path: Path):
    from mnemosyne.benchmarks.report import build_markdown_report, load_jsonl

    output_path = tmp_path / "p1_solver.jsonl"

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    rows = load_jsonl(output_path)

    report = build_markdown_report(
        results=rows,
        title="REALM Local Benchmark Report — P1 Solver",
    )

    assert "# REALM Local Benchmark Report — P1 Solver" in report
    assert "local-p1-compatible-campus-tour-solver-001" in report
    assert "solver-derived plan" in report
    assert "Route: `S -> D -> A -> B -> L -> S`" in report

    assert "### Solver certificate" in report
    assert "p1_campus_tour_bruteforce" in report
    assert "optimal_for_enumerated_space" in report
    assert "minimize_total_minutes" in report

    assert "### Plan proposal" in report
    assert "proposal:local-p1-compatible-campus-tour-solver-001" in report

    assert (
        "The feasible trace or solver-derived plan committed successfully through Mnemosyne."
        in report
    )


@pytest.mark.realm
def test_p1_solver_runner_rejects_conflicting_active_proposals(tmp_path: Path):
    source_path = Path("benchmarks/realm/p1_solver/campus_tour_solver_001.json")
    data_left = json.loads(source_path.read_text(encoding="utf-8"))
    data_right = json.loads(source_path.read_text(encoding="utf-8"))

    data_left["case_id"] = "local-p1-conflict-left"
    data_right["case_id"] = "local-p1-conflict-right"

    # Same tenant + same entity creates an active proposal conflict.
    data_left["entity_id"] = "campus-tour-conflict-shared"
    data_right["entity_id"] = "campus-tour-conflict-shared"

    case_dir = tmp_path / "cases"
    case_dir.mkdir()

    (case_dir / "left.json").write_text(
        json.dumps(data_left),
        encoding="utf-8",
    )
    (case_dir / "right.json").write_text(
        json.dumps(data_right),
        encoding="utf-8",
    )

    output_path = tmp_path / "conflicts.jsonl"

    exit_code = main(
        [
            "--cases",
            str(case_dir),
            "--solver",
            "p1-bruteforce",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 1

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 2

    for row in rows:
        assert row["ok"] is False
        assert row["committed_rids"] == []
        assert row["metrics"] is None
        assert "SOLVER_PROPOSAL_CONFLICT" in row["error_codes"]
        assert "ENTITY_PROPOSAL_CONFLICT" in row["error_codes"]
        assert row["details"]["observed"]["committed"] is False
        assert row["details"]["solver_certificate"]["solver_id"] == "p1_campus_tour_bruteforce"
        assert row["details"]["proposal_conflicts"]["ok"] is False


@pytest.mark.realm
def test_p1_solver_runner_accepts_matching_world_snapshot(tmp_path: Path):
    output_path = tmp_path / "matching_world.jsonl"
    snapshot_path = tmp_path / "world.json"

    snapshot_path.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "tenant_id": "*",
                        "entity_id": "*",
                        "key": "deadline",
                        "value": "17:00",
                        "source": "test-world-snapshot",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--solver",
            "p1-bruteforce",
            "--world-snapshot",
            str(snapshot_path),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])

    assert row["ok"] is True
    assert row["details"]["observed"]["committed"] is True


@pytest.mark.realm
def test_p1_solver_runner_rejects_stale_world_snapshot_before_commit(tmp_path: Path):
    output_path = tmp_path / "stale_world.jsonl"
    snapshot_path = tmp_path / "world.json"

    snapshot_path.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "tenant_id": "*",
                        "entity_id": "*",
                        "key": "deadline",
                        "value": "11:00",
                        "source": "test-world-snapshot",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--solver",
            "p1-bruteforce",
            "--world-snapshot",
            str(snapshot_path),
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 1

    row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert row["metrics"] is None
    assert "STALE_WORLD_RECONCILIATION" in row["error_codes"]
    assert "STALE_WORLD_FACT" in row["error_codes"]
    assert row["details"]["observed"]["committed"] is False
    assert row["details"]["world_reconciliation"]["ok"] is False
    assert row["details"]["world_reconciliation"]["issues"][0]["key"] == "deadline"
    assert row["details"]["world_reconciliation"]["issues"][0]["expected_value"] == "17:00"
    assert row["details"]["world_reconciliation"]["issues"][0]["observed_value"] == "11:00"


@pytest.mark.realm
def test_p1_solver_runner_repairs_stale_world_deadline_before_commit(tmp_path: Path):
    output_path = tmp_path / "repaired_stale_world.jsonl"
    snapshot_path = tmp_path / "world.json"

    # 13:00 differs from the proposal's original 17:00 assumption,
    # so the first reconciliation is stale. The route finishing at 12:10
    # remains feasible after deterministic deadline repair.
    snapshot_path.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "tenant_id": "*",
                        "entity_id": "*",
                        "key": "deadline",
                        "value": "13:00",
                        "source": "test-world-snapshot",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--solver",
            "p1-bruteforce",
            "--world-snapshot",
            str(snapshot_path),
            "--repair-stale-world",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])

    assert row["ok"] is True
    assert row["committed_rids"]
    assert row["details"]["observed"]["committed"] is True
    assert row["details"]["stale_world_repair"]["applied"] is True

    actions = row["details"]["stale_world_repair"]["actions"]
    assert actions == [
        {
            "repair_type": "PATCH_DEADLINE_FROM_WORLD_FACT",
            "key": "deadline",
            "observed_value": "13:00",
            "patched_paths": ["realm_bench.deadline"],
            "previous_value": "17:00",
        }
    ]

    assert row["plan_proposal"]["attrs"]["deadline"] == "13:00"
    assert row["plan_proposal"]["attrs"]["world_assumptions"] == [
        {
            "key": "deadline",
            "value": "13:00",
            "source": "p1_campus_tour_solver",
        }
    ]


@pytest.mark.realm
def test_p1_solver_runner_repair_stale_world_still_rejects_infeasible_deadline(
    tmp_path: Path,
):
    output_path = tmp_path / "unrepairable_stale_world.jsonl"
    snapshot_path = tmp_path / "world.json"

    # 11:00 is stale and too early for the P1 route finishing at 12:10.
    # Deterministic repair patches the deadline, reruns the solver, and the
    # repaired proposal remains infeasible.
    snapshot_path.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "tenant_id": "*",
                        "entity_id": "*",
                        "key": "deadline",
                        "value": "11:00",
                        "source": "test-world-snapshot",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_solver",
            "--solver",
            "p1-bruteforce",
            "--world-snapshot",
            str(snapshot_path),
            "--repair-stale-world",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 1

    row = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert "STALE_WORLD_REPAIR_FAILED" in row["error_codes"]
    assert row["details"]["observed"]["committed"] is False
