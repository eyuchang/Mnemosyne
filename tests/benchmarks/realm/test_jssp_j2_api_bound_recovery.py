from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.run_jssp_j2_api_bound_recovery import (
    run_j2_api_bound_recovery,
)


def test_j2_api_bound_recovery_uses_active_commitments_and_admission(tmp_path: Path):
    result = run_j2_api_bound_recovery(tmp_path)

    assert result.registered_commitment_count == 9
    assert result.fired_commitment_count == 2
    assert result.repair_candidate_count == 2
    assert result.repair_admission_ok is True
    assert result.finalization_ok is True
    assert result.admitted_commitment_count == 2
    assert result.live_commitment_count == 7
    assert result.unresolved_after_finalization == 7

    artifact = json.loads(result.files["api_bound_json"].read_text(encoding="utf-8"))

    assert artifact["schema_version"] == "realm_jssp_j2_api_bound_recovery.v1"
    assert artifact["case_id"] == "J2"
    assert artifact["jssp_schedule"]["case_id"] == "realm-j2"
    assert artifact["jssp_schedule"]["operation_count"] == 9

    assert artifact["disruption"] == {
        "event_id": "realm-j2:breakdown:MachineA:4-6",
        "machine_id": "MachineA",
        "type": "machine_breakdown",
        "unavailable_end": 6,
        "unavailable_start": 4,
    }

    assert set(artifact["results"]["affected_operation_keys"]) == {
        "Job2:O1",
        "Job3:O2",
    }
    assert artifact["results"]["baseline_admission_ok"] is True
    assert artifact["results"]["registration_ok"] is True
    assert artifact["results"]["disruption_signal_ok"] is True
    assert artifact["results"]["proposal_batch_ok"] is True
    assert artifact["results"]["repair_admission_ok"] is True
    assert artifact["results"]["finalization_ok"] is True
    assert artifact["results"]["active_commitment_audit_count"] == 9
    assert artifact["results"]["recovery_lineage_count"] > 0


def test_j2_api_bound_recovery_claims_are_precise(tmp_path: Path):
    result = run_j2_api_bound_recovery(tmp_path)
    artifact = json.loads(result.files["report_json"].read_text(encoding="utf-8"))

    assert artifact["claims"] == {
        "active_commitment_memory_claimed": True,
        "admission_boundary_claimed": True,
        "api_bound_recovery_claimed": True,
        "audit_lineage_claimed": True,
        "benchmark_local_recovery_claimed": True,
        "durable_logs_claimed": False,
        "global_schedule_feasibility_after_api_admission_claimed": False,
        "j4_full_recovery_claimed": False,
        "production_runtime_claimed": False,
    }

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM J2 API-Bound JSSP Recovery Report" in md
    assert "`register_schedule_commitments`" in md
    assert "`signal_machine_breakdown`" in md
    assert "`emit_recovery_proposals_for_disruption`" in md
    assert "`admit_and_finalize_repair_candidates_from_proposal_batch`" in md
    assert "api_bound_recovery_claimed: True" in md
    assert "durable_logs_claimed: False" in md
    assert "j4_full_recovery_claimed: False" in md


def test_committed_j2_api_bound_recovery_artifacts_are_current(tmp_path: Path):
    generated = run_j2_api_bound_recovery(tmp_path)

    committed = {
        "api_bound_json": Path("benchmarks/realm/api_bound/j2_jssp_api_bound_recovery.json"),
        "report_json": Path("benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
