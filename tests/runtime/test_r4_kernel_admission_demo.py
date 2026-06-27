from __future__ import annotations

from mnemosyne.runtime.r4_kernel_admission_demo import run_demo


def test_r4_kernel_admission_demo(tmp_path):
    result = run_demo(tmp_path / "kernel_admission.sqlite3")

    assert result["pass"] is True
    assert result["kernel_call_count"] == 3
    assert result["checks"] == {
        "accepted_has_committed_rid": True,
        "preflight_rejection_did_not_call_kernel": True,
        "validator_rejection_has_no_committed_rids": True,
        "commit_failure_has_no_committed_rids": True,
        "kernel_called_three_times": True,
    }

    cases = {case["case_id"]: case for case in result["cases"]}

    assert cases["accepted_and_committed"]["runtime_decision"] == "accepted"
    assert cases["accepted_and_committed"]["committed_rids"] == ["rid:r4-kernel:accepted"]

    assert cases["rejected_before_commit"]["runtime_decision"] == "rejected"
    assert cases["rejected_before_commit"]["kernel_commit_performed"] is False

    assert cases["validator_rejected"]["runtime_decision"] == "rejected"
    assert cases["validator_rejected"]["committed_rids"] == []

    assert cases["commit_failed"]["runtime_decision"] == "rejected"
    assert cases["commit_failed"]["committed_rids"] == []
