from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.r60_jssp_disruptive_planning_demo import run_demo


@pytest.mark.asyncio
async def test_r60_jssp_disruptive_planning_demo_exports_reports(tmp_path: Path):
    result = await run_demo(tmp_path)

    assert result.baseline_operation_count == 9
    assert result.registered_commitment_count == 9
    assert result.affected_operation_keys == ["J3:O2", "J2:O3"]
    assert result.fired_commitment_count == 2
    assert result.proposed_commitment_count == 2
    assert result.live_commitment_count == 7
    assert result.recovery_package_count == 2
    assert result.repair_candidate_rids == [
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J3-O2",
        "rid:jssp:jssp-3x3-smoke:repair-candidate:J2-O3",
    ]
    assert result.schedule_unchanged is True

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    active = json.loads(result.files["active_json"].read_text(encoding="utf-8"))
    unresolved = json.loads(result.files["unresolved_json"].read_text(encoding="utf-8"))
    recovery = json.loads(result.files["recovery_lineage_json"].read_text(encoding="utf-8"))

    assert len(active) == 9
    assert unresolved["count"] == 9
    assert len(recovery) == 2

    assert {
        row["status"]
        for row in active
    } == {"live", "proposed"}

    assert [
        row["package_id"]
        for row in recovery
    ] == [
        "pkg:jssp:jssp-3x3-smoke:repair:J3-O2",
        "pkg:jssp:jssp-3x3-smoke:repair:J2-O3",
    ]

    active_md = result.files["active_md"].read_text(encoding="utf-8")
    unresolved_md = result.files["unresolved_md"].read_text(encoding="utf-8")
    recovery_md = result.files["recovery_lineage_md"].read_text(encoding="utf-8")

    assert "# R6.0 JSSP Active Commitment Audit" in active_md
    assert "# R6.0 JSSP Unresolved Commitments" in unresolved_md
    assert "# R6.0 JSSP Recovery Lineage" in recovery_md
    assert "proposal:jssp:jssp-3x3-smoke:repair:J3-O2" in recovery_md
