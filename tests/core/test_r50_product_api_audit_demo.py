from __future__ import annotations

import pytest

from examples.r50_product_api_audit_demo import run_demo


@pytest.mark.asyncio
async def test_r50_product_api_audit_demo():
    result = await run_demo()

    assert result.active_commitment_ids == ["c-package", "c-runtime"]
    assert result.unresolved_commitment_ids == ["c-package", "c-runtime"]

    assert len(result.recovery_record_ids) == 1
    assert result.recovery_record_ids[0].startswith("acr-proposal:c-runtime:")
    assert result.recovery_action_types == ["commitment_proposal_emitted"]

    assert result.package_record_ids == ["rid:r50-demo-package-proposal"]
    assert result.package_action_types == ["commitment_proposal_emitted"]

    assert result.audit_statuses == {
        "c-package": "proposed",
        "c-runtime": "proposed",
    }

    assert result.recovery_lineage_actions == [
        "commitment_proposal_emitted",
        "commitment_proposal_emitted",
    ]

    assert result.committed_only_commitment_fsm
