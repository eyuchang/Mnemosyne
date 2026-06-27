from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_thanksgiving_api_bound_recovery import (
    run_api_bound_recovery,
)


def test_thanksgiving_api_bound_recovery_uses_real_mnemosyne_apis(tmp_path: Path):
    result = run_api_bound_recovery(tmp_path)

    assert result.registered_commitments == 4
    assert result.fired_commitments == 2
    assert result.proposal_packages == 1
    assert result.admitted_repairs == 1

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["api_bound_json"].read_text(encoding="utf-8"))

    assert report["schema_version"] == "thanksgiving_api_bound_recovery.v1"
    assert report["case_id"] == "P9"
    assert report["tenant_id"] == "realm-thanksgiving"
    assert report["workflow_id"] == "p9-thanksgiving-api-bound"

    for api_name in [
        "SQLiteStore",
        "register_active_commitment",
        "fire_active_commitment",
        "create_recovery_proposal_package",
        "emit_package_backed_proposal",
        "admit_active_commitment",
        "audit_active_commitments",
        "audit_commitment_lineage",
        "audit_recovery_lineage",
        "list_unresolved_commitments",
    ]:
        assert api_name in report["api_calls"]

    assert report["proposal_package"]["package_id"] == "p9-package-reassign-grandma-to-sarah"
    assert report["proposal_package"]["commitment_id"] == "p9-pickup-grandma-by-james"
    assert report["proposal_package"]["proposal_ref"] == "repair:grandma-pickup-james-to-sarah"

    statuses = report["commitment_statuses"]
    assert statuses["p9-pickup-grandma-by-james"] == "admitted"
    assert statuses["p9-dinner-ready-by-1800"] == "fired"
    assert statuses["p9-cook-turkey-supervision"] == "live"
    assert statuses["p9-pickup-emily"] == "live"

    assert report["result"] == {
        "admitted_repairs": 1,
        "dinner_ready_time": "18:00",
        "feasible_after_repair": True,
        "fired_commitments": 2,
        "latest_family_home_time": "17:30",
        "optimality_status": "feasible_not_proven_optimal",
        "proposal_packages": 1,
        "registered_commitments": 4,
        "repair_trigger_time": "10:00",
    }

    assert len(report["audit"]["active_commitments"]) == 4
    assert len(report["audit"]["grandma_commitment_lineage"]) >= 4
    assert len(report["audit"]["recovery_lineage"]) >= 1
    assert report["audit"]["unresolved_count"] == 3


def test_thanksgiving_api_bound_recovery_report_is_human_readable(tmp_path: Path):
    result = run_api_bound_recovery(tmp_path)

    md = result.files["report_markdown"].read_text(encoding="utf-8")

    assert "# Thanksgiving P9 API-Bound Recovery Report" in md
    assert "register_active_commitment" in md
    assert "fire_active_commitment" in md
    assert "emit_package_backed_proposal" in md
    assert "admit_active_commitment" in md
    assert "p9-pickup-grandma-by-james" in md
    assert "admitted" in md


def test_committed_thanksgiving_api_bound_recovery_artifacts_are_current(
    tmp_path: Path,
):
    generated = run_api_bound_recovery(tmp_path)

    committed = {
        "api_bound_json": Path("benchmarks/realm/api_bound/p9_thanksgiving_api_bound_recovery.json"),
        "report_json": Path("benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
