import pytest

from examples.r46_validated_runtime_recovery_demo import run_demo


@pytest.mark.asyncio
async def test_r46_validated_runtime_recovery_demo_runs_end_to_end():
    result = await run_demo()

    assert result["validation_ok"] == [True]
    assert result["committed_actions"] == ["commitment_proposal_emitted"]
    assert result["committed_fsms"] == ["mnemosyne.commitment"]

    # Runtime recovery updates commitment state only.
    assert result["commitment_status"] == "proposed"

    # Domain state remains unchanged until a separate domain repair is admitted.
    assert result["domain_state"] == "stale"
    assert result["domain_version"] == 1
    assert result["domain_effective_records"] == ["rid:domain-initial"]
