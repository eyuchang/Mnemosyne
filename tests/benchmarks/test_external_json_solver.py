from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.external_json_solver import ExternalJsonSolver
from mnemosyne.benchmarks.p1_solver_runner import main
from mnemosyne.benchmarks.solver_registry import default_solver_registry


FIXTURE = Path("benchmarks/realm/p1_external/campus_tour_external_001.json")


def test_external_json_solver_produces_proposal_and_certificate():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    result = ExternalJsonSolver().solve(data)

    assert result.ok is True
    assert result.benchmark_case is not None
    assert result.plan_proposal is not None
    assert result.certificate is not None

    assert result.certificate.solver_id == "external_json_solver"
    assert result.certificate.feasible is True

    assert result.plan_proposal.proposal_id.startswith(
        "proposal:external_json_solver:"
    )
    assert result.plan_proposal.route == ["S", "D", "A", "B", "L", "S"]
    assert result.plan_proposal.attrs["deadline"] == "17:00"
    assert result.plan_proposal.attrs["world_assumptions"] == [
        {
            "key": "deadline",
            "value": "17:00",
            "source": "external_json_solver",
        }
    ]


def test_external_json_solver_rejects_bad_route():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["external_solution"]["route"] = "not-a-list"

    result = ExternalJsonSolver().solve(data)

    assert result.ok is False
    assert result.plan_proposal is None
    assert result.certificate.feasible is False
    assert "route must be a list" in (result.error_message or "")


def test_external_json_solver_is_registered():
    registry = default_solver_registry()
    solver = registry.create("p1-external-json")

    assert isinstance(solver, ExternalJsonSolver)


@pytest.mark.realm
def test_external_json_solver_runner_commits_fixture(tmp_path: Path):
    output_path = tmp_path / "external_json.jsonl"

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_external/campus_tour_external_001.json",
            "--solver",
            "p1-external-json",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) == 1
    row = rows[0]

    assert row["ok"] is True
    assert row["committed_rids"]
    assert row["solver_certificate"]["solver_id"] == "external_json_solver"
    assert row["plan_proposal"]["attrs"]["external_solver_id"] == "external_json_solver"


@pytest.mark.realm
def test_external_json_solver_runner_rejects_bad_deadline_before_commit(
    tmp_path: Path,
):
    output_path = tmp_path / "external_json_bad_deadline.jsonl"

    exit_code = main(
        [
            "--cases",
            "benchmarks/realm/p1_external/campus_tour_external_bad_deadline_001.json",
            "--solver",
            "p1-external-json",
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

    assert len(rows) == 1
    row = rows[0]

    assert row["ok"] is False
    assert row["committed_rids"] == []
    assert row["error_codes"] == ["SOLVER_FAILED"]
    assert row["error_message"] == "external JSON solution failed adapter checks"
    assert row["details"]["observed"]["committed"] is False

    certificate = row["details"]["solver_certificate"]
    assert certificate["solver_id"] == "external_json_solver"
    assert certificate["feasible"] is False
    assert any(
        "external solution finishes after deadline" in violation
        for violation in certificate["violations"]
    )
