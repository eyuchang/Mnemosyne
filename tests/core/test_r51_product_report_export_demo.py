from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.r51_product_report_export_demo import run_demo


@pytest.mark.asyncio
async def test_r51_product_report_export_demo(tmp_path: Path):
    result = await run_demo(tmp_path)

    assert result.active_commitment_count == 1
    assert result.unresolved_commitment_count == 1
    assert result.commitment_lineage_count == 3
    assert result.recovery_lineage_count == 1

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    active_json = json.loads(result.files["active_json"].read_text(encoding="utf-8"))
    unresolved_json = json.loads(result.files["unresolved_json"].read_text(encoding="utf-8"))
    recovery_json = json.loads(result.files["recovery_lineage_json"].read_text(encoding="utf-8"))

    assert active_json[0]["commitment_id"] == "c-report"
    assert active_json[0]["status"] == "proposed"
    assert unresolved_json["count"] == 1
    assert recovery_json[0]["proposal_ref"] == "proposal:r51-report-repair"
    assert recovery_json[0]["package_id"] == "pkg:r51-report-repair"

    active_md = result.files["active_md"].read_text(encoding="utf-8")
    unresolved_md = result.files["unresolved_md"].read_text(encoding="utf-8")
    recovery_md = result.files["recovery_lineage_md"].read_text(encoding="utf-8")

    assert "# R5.1 Active Commitment Audit" in active_md
    assert "# R5.1 Unresolved Commitments" in unresolved_md
    assert "# R5.1 Recovery Lineage" in recovery_md
    assert "commitment_proposal_emitted" in recovery_md
