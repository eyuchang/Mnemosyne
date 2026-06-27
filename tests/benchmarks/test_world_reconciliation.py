# File: tests/benchmarks/test_world_reconciliation.py
#
# Purpose:
#   Verify R2.3 stale-world reconciliation semantics.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnemosyne.benchmarks.solver import PlanProposal
from mnemosyne.benchmarks.world_reconciliation import (
    ObservedWorldFact,
    assert_world_reconciled,
    extract_world_assumptions,
    load_world_snapshot,
    reconcile_world,
)


def proposal_with_assumption(
    *,
    proposal_id: str = "proposal:test",
    tenant_id: str = "tenant:test",
    entity_id: str = "entity:test",
    key: str = "deadline",
    value: object = "17:00",
) -> PlanProposal:
    return PlanProposal(
        proposal_id=proposal_id,
        case_id=f"case:{proposal_id}",
        tenant_id=tenant_id,
        workflow_id="workflow:test",
        entity_id=entity_id,
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        route=["S", "D", "A", "B", "L", "S"],
        steps=[],
        attrs={
            "world_assumptions": [
                {
                    "key": key,
                    "value": value,
                    "source": "test",
                }
            ]
        },
        certificate=None,
    )


def test_extract_world_assumptions_defaults_to_proposal_scope():
    proposal = proposal_with_assumption()

    assumptions = extract_world_assumptions(proposal)

    assert len(assumptions) == 1
    assert assumptions[0].tenant_id == "tenant:test"
    assert assumptions[0].entity_id == "entity:test"
    assert assumptions[0].key == "deadline"
    assert assumptions[0].expected_value == "17:00"


def test_reconcile_world_accepts_matching_fact():
    proposal = proposal_with_assumption()

    report = reconcile_world(
        proposals=[proposal],
        observed_facts=[
            ObservedWorldFact(
                tenant_id="tenant:test",
                entity_id="entity:test",
                key="deadline",
                observed_value="17:00",
                source="test-snapshot",
            )
        ],
    )

    assert report.ok is True
    assert report.issues == []


def test_reconcile_world_rejects_stale_fact():
    proposal = proposal_with_assumption()

    report = reconcile_world(
        proposals=[proposal],
        observed_facts=[
            ObservedWorldFact(
                tenant_id="tenant:test",
                entity_id="entity:test",
                key="deadline",
                observed_value="11:00",
                source="test-snapshot",
            )
        ],
    )

    assert report.ok is False
    assert report.error_codes == ["STALE_WORLD_FACT"]
    assert report.issues[0].key == "deadline"
    assert report.issues[0].expected_value == "17:00"
    assert report.issues[0].observed_value == "11:00"


def test_reconcile_world_reports_missing_required_fact():
    proposal = proposal_with_assumption()

    report = reconcile_world(
        proposals=[proposal],
        observed_facts=[],
    )

    assert report.ok is False
    assert report.error_codes == ["WORLD_FACT_MISSING"]


def test_reconcile_world_allows_wildcard_observed_fact():
    proposal = proposal_with_assumption(
        tenant_id="tenant:a",
        entity_id="entity:x",
    )

    report = reconcile_world(
        proposals=[proposal],
        observed_facts=[
            ObservedWorldFact(
                tenant_id="*",
                entity_id="*",
                key="deadline",
                observed_value="17:00",
                source="global-test-snapshot",
            )
        ],
    )

    assert report.ok is True


def test_assert_world_reconciled_raises_on_stale_fact():
    proposal = proposal_with_assumption()

    with pytest.raises(ValueError, match="STALE_WORLD_FACT"):
        assert_world_reconciled(
            proposals=[proposal],
            observed_facts=[
                ObservedWorldFact(
                    tenant_id="tenant:test",
                    entity_id="entity:test",
                    key="deadline",
                    observed_value="11:00",
                )
            ],
        )


def test_load_world_snapshot_from_object(tmp_path: Path):
    snapshot_path = tmp_path / "world.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "tenant_id": "tenant:test",
                        "entity_id": "entity:test",
                        "key": "deadline",
                        "value": "17:00",
                        "source": "snapshot",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    facts = load_world_snapshot(snapshot_path)

    assert len(facts) == 1
    assert facts[0].tenant_id == "tenant:test"
    assert facts[0].entity_id == "entity:test"
    assert facts[0].key == "deadline"
    assert facts[0].observed_value == "17:00"
