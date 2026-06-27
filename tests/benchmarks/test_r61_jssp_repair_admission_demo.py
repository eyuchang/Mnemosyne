from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.r61_jssp_repair_admission_demo import run_demo


@pytest.mark.asyncio
async def test_r61_jssp_repair_admission_demo_exports_reports(tmp_path: Path):
    result = await run_demo(tmp_path)

    assert result.baseline_operation_count == 9
    assert result.registered_commitment_count == 9
    assert result.affected_operation_keys == ["J3:O2", "J2:O3"]
    assert result.repair_candidate_rids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]
    assert result.repair_committed_rids == result.repair_candidate_rids
    assert result.unresolved_before_repair == 9
    assert result.unresolved_after_domain_repair == 9
    assert result.unresolved_after_finalization == 7
    assert result.live_commitment_count == 7
    assert result.admitted_commitment_count == 2

    assert result.before_windows == {
        "J3:O2": (4, 7),
        "J2:O3": (7, 11),
    }
    assert result.after_windows == {
        "J3:O2": (9, 12),
        "J2:O3": (12, 16),
    }

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    active = json.loads(result.files["active_json"].read_text(encoding="utf-8"))
    unresolved = json.loads(result.files["unresolved_json"].read_text(encoding="utf-8"))
    recovery = json.loads(result.files["recovery_lineage_json"].read_text(encoding="utf-8"))

    assert len(active) == 9
    assert {
        row["status"]
        for row in active
    } == {"live", "admitted"}

    assert unresolved["count"] == 7
    assert len(recovery) == 4
    assert [
        row["action_type"]
        for row in recovery
    ] == [
        "commitment_proposal_emitted",
        "commitment_proposal_emitted",
        "commitment_admitted",
        "commitment_admitted",
    ]

    active_md = result.files["active_md"].read_text(encoding="utf-8")
    unresolved_md = result.files["unresolved_md"].read_text(encoding="utf-8")
    recovery_md = result.files["recovery_lineage_md"].read_text(encoding="utf-8")

    assert "# R6.1 JSSP Active Commitment Audit After Repair" in active_md
    assert "# R6.1 JSSP Unresolved Commitments After Repair" in unresolved_md
    assert "# R6.1 JSSP Recovery Lineage After Repair" in recovery_md
