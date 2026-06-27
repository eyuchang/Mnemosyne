from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_thanksgiving_benchmark import run_benchmark


def test_thanksgiving_benchmark_generates_solutions_evaluations_and_report(
    tmp_path: Path,
):
    result = run_benchmark(tmp_path)

    assert result.p6_feasible is True
    assert result.p9_feasible is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    p6_solution = json.loads(result.files["p6_solution"].read_text(encoding="utf-8"))
    p9_solution = json.loads(result.files["p9_solution"].read_text(encoding="utf-8"))
    p6_eval = json.loads(result.files["p6_evaluation"].read_text(encoding="utf-8"))
    p9_eval = json.loads(result.files["p9_evaluation"].read_text(encoding="utf-8"))
    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert p6_solution["case_id"] == "P6"
    assert p6_solution["optimality_status"] == "feasible_not_proven_optimal"
    assert p6_solution["plan"]["final_state"] == {
        "all_family_home_by": "15:30",
        "dinner_ready_at": "18:00",
    }

    assert p9_solution["case_id"] == "P9"
    assert p9_solution["repair"]["repair_trigger_time"] == "10:00"
    assert p9_solution["repair"]["changed_assignments"] == [
        {
            "after": "Sarah",
            "before": "James",
            "reason": "James now lands too late to complete Grandma pickup before dinner.",
            "task": "Grandma pickup",
        }
    ]
    assert p9_solution["plan"]["final_state"] == {
        "all_family_home_by": "17:30",
        "dinner_ready_at": "18:00",
    }

    assert p6_eval["feasible"] is True
    assert p9_eval["feasible"] is True
    assert all(check["passed"] for check in p6_eval["checks"])
    assert all(check["passed"] for check in p9_eval["checks"])

    assert report["benchmark_id"] == "thanksgiving_p6_p9"
    assert report["result_summary"] == {
        "p6_feasible": True,
        "p6_optimality_status": "feasible_not_proven_optimal",
        "p9_feasible": True,
        "p9_optimality_status": "feasible_not_proven_optimal",
        "report_type": "executable_deterministic_baseline",
    }

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# Thanksgiving P6/P9 Executable Benchmark Report" in md
    assert "## P6 Baseline Solution" in md
    assert "## P9 Dynamic Disruption" in md
    assert "James" in md
    assert "Grandma pickup: James -> Sarah" in md
    assert "Optimality is not proven" in md


def test_committed_thanksgiving_benchmark_artifacts_are_current(tmp_path: Path):
    generated = run_benchmark(tmp_path)

    committed = {
        "p6_solution": Path("benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json"),
        "p9_solution": Path("benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json"),
        "p6_evaluation": Path("benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json"),
        "p9_evaluation": Path("benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json"),
        "report_json": Path("benchmarks/realm/reports/thanksgiving_p6_p9_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/thanksgiving_p6_p9_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
