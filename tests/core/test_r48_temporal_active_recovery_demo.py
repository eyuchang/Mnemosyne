import pytest

from examples.r48_temporal_active_recovery_demo import run_demo


@pytest.mark.asyncio
async def test_r48_temporal_active_recovery_demo_runs_end_to_end():
    result = await run_demo()

    assert result["workflow_id"] == "workflow:r48-demo"
    assert result["runtime_status_before"] == "submitted"
    assert result["runtime_status_after"] == "submitted"

    # Durable recovery work happens through the activity boundary.
    assert result["first_activity_committed_fsms"] == ["mnemosyne.commitment"]
    assert result["first_activity_actions"] == ["commitment_proposal_emitted"]
    assert result["first_activity_validation_ok"] == [True]
    assert result["first_activity_commitment_statuses"] == {"c1": "proposed"}
    assert result["commitment_status_after_first"] == "proposed"

    # A replay/retry after success is a no-op because proposed is not recoverable.
    assert result["second_activity_committed_rids"] == []
    assert result["second_activity_skipped"] == {"c1": "status_proposed_not_recoverable"}
    assert result["second_activity_commitment_statuses"] == {"c1": "proposed"}

    # Temporal orchestration does not mutate domain truth.
    assert result["domain_state_before_activity"] == "stale"
    assert result["domain_state_after_first"] == "stale"
    assert result["domain_state_after_second"] == "stale"
    assert result["domain_version_after_second"] == 1
    assert result["domain_effective_records_after_second"] == ["rid:domain-initial"]

    # Runtime driver remains orchestration-only.
    assert not result["runtime_exposes_commit_batch"]
    assert not result["runtime_exposes_get_state_view"]
