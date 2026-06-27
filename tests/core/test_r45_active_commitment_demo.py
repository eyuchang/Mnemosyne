import pytest

from examples.r45_active_commitment_recovery_demo import run_demo


@pytest.mark.asyncio
async def test_r45_active_commitment_recovery_demo_runs_end_to_end():
    result = await run_demo()

    assert result["plan_candidate_actions"] == [
        "commitment_rejected",
        "commitment_proposal_emitted",
    ]

    # The recovery proposal alone must not mutate the domain state.
    assert result["mid_domain_state"] == "stale"
    assert result["mid_commitment_status"] == "proposed"

    # Domain state changes only after the admitted domain repair record.
    assert result["final_domain_state"] == "repaired"
    assert result["final_domain_effective_records"] == [
        "rid:domain-initial",
        "rid:domain-repair",
    ]

    assert result["final_commitment_status"] == "admitted"
    assert result["final_live_commitments"] == []
