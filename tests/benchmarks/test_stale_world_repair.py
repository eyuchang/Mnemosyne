from __future__ import annotations

from mnemosyne.benchmarks.stale_world_repair import (
    repair_case_data_from_stale_world,
)


def test_repair_case_data_patches_deadline_from_stale_world_issue():
    case_data = {
        "case_id": "case-1",
        "deadline": "17:00",
        "provenance": {
            "source": "test",
        },
    }

    report = {
        "ok": False,
        "issues": [
            {
                "issue_type": "STALE_WORLD_FACT",
                "key": "deadline",
                "expected_value": "17:00",
                "observed_value": "13:00",
            }
        ],
    }

    result = repair_case_data_from_stale_world(
        case_data=case_data,
        reconciliation_report=report,
    )

    assert result.ok is True
    assert result.repaired_case_data is not None
    assert result.repaired_case_data["deadline"] == "13:00"

    # Original data must not be mutated.
    assert case_data["deadline"] == "17:00"

    assert result.repair_actions == [
        {
            "repair_type": "PATCH_DEADLINE_FROM_WORLD_FACT",
            "key": "deadline",
            "observed_value": "13:00",
            "patched_paths": ["deadline"],
            "previous_value": "17:00",
        }
    ]

    assert result.repaired_case_data["provenance"]["stale_world_repair"] == {
        "key": "deadline",
        "observed_value": "13:00",
        "stage": "R2.5",
    }


def test_repair_case_data_rejects_unsupported_key():
    case_data = {
        "case_id": "case-1",
        "deadline": "17:00",
    }

    report = {
        "ok": False,
        "issues": [
            {
                "issue_type": "STALE_WORLD_FACT",
                "key": "road_closure",
                "expected_value": False,
                "observed_value": True,
            }
        ],
    }

    result = repair_case_data_from_stale_world(
        case_data=case_data,
        reconciliation_report=report,
    )

    assert result.ok is False
    assert "unsupported stale-world key" in (result.error_message or "")


def test_repair_case_data_requires_patchable_deadline():
    case_data = {
        "case_id": "case-1",
    }

    report = {
        "ok": False,
        "issues": [
            {
                "issue_type": "STALE_WORLD_FACT",
                "key": "deadline",
                "expected_value": "17:00",
                "observed_value": "13:00",
            }
        ],
    }

    result = repair_case_data_from_stale_world(
        case_data=case_data,
        reconciliation_report=report,
    )

    assert result.ok is False
    assert result.error_message == "case data has no patchable deadline field"
