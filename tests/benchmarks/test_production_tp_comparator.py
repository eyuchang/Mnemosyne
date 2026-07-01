from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "benchmarks" / "realm" / "production_tp_comparator.py"


def load_module():
    import sys

    spec = importlib.util.spec_from_file_location(
        "production_tp_comparator", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None

    # Required for Python 3.9 dataclasses when postponed annotations are used.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)
    return module


def test_cases_encode_expected_layer_boundary():
    module = load_module()
    cases = module.build_cases()
    module.validate_cases(cases)

    assert len(cases) == 9
    assert all(case.atp_mnemosyne == "caught" for case in cases)

    by_hazard = {case.hazard: case for case in cases}

    assert by_hazard["primary_key_unique_duplicate"].postgres_style_tp == "caught"
    assert by_hazard["missing_foreign_key_dependency"].postgres_style_tp == "caught"

    assert by_hazard["finite_state_invalid_transition"].postgres_style_tp == "app-only"
    assert by_hazard["finite_state_invalid_transition"].workflow_saga == "caught"

    atp_specific = [
        "stale_world_proposal",
        "orphaning_compensation_effective_state",
        "evidence_destroying_repair",
        "acr_direct_domain_mutation",
        "generative_conflict_scope_collision",
        "duplicate_side_effect_intent",
    ]

    for hazard in atp_specific:
        case = by_hazard[hazard]
        assert case.atp_mnemosyne == "caught"
        assert case.postgres_style_tp in {"missed", "partial", "app-only"}
        assert case.workflow_saga in {"missed", "partial"}


def test_report_generation(tmp_path):
    module = load_module()
    summary = module.run(tmp_path)

    assert summary["benchmark"] == "ProductionTPComparatorBench"
    assert summary["kind"] == "deterministic coverage audit"
    assert summary["not_a_throughput_benchmark"] is True
    assert summary["num_cases"] == 9
    assert summary["layers"]["atp_mnemosyne"]["caught"] == 9

    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.csv").exists()
    assert (tmp_path / "report.md").exists()

    report = (tmp_path / "report.md").read_text()
    assert "not a throughput benchmark" in report
    assert "proposal-authority semantics" in report
