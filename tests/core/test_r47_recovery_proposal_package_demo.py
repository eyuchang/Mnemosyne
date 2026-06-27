import pytest

from examples.r47_recovery_proposal_package_demo import run_demo


@pytest.mark.asyncio
async def test_r47_recovery_proposal_package_demo_runs_end_to_end():
    result = await run_demo()

    assert result["proposal_validation_ok"]
    assert result["proposal_committed_actions"] == ["commitment_proposal_emitted"]
    assert result["proposal_committed_fsms"] == ["mnemosyne.commitment"]

    assert result["package_ref"]["package_id"] == "pkg:c1:repair:1"
    assert result["package_ref"]["candidate_rids"] == ["rid:domain-repair-candidate"]

    # The commitment proposal was admitted, so the commitment advances.
    assert result["commitment_status_after_proposal"] == "proposed"

    # But the package's domain candidate remains inert.
    assert result["domain_state_after_proposal"] == "stale"
    assert result["domain_version_after_proposal"] == 1
    assert not result["inert_domain_candidate_was_committed"]

    # Domain repair happens only through a separate domain CTL admission.
    assert result["domain_state_after_separate_admission"] == "repaired"
    assert result["domain_version_after_separate_admission"] == 2
    assert result["domain_effective_records_after_separate_admission"] == [
        "rid:domain-initial",
        "rid:domain-repair-admitted",
    ]
