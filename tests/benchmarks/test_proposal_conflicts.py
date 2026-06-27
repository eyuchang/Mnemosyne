# File: tests/benchmarks/test_proposal_conflicts.py
#
# Purpose:
#   Verify R2.2 proposal conflict semantics.

from __future__ import annotations

import pytest

from mnemosyne.benchmarks.proposal_conflicts import (
    assert_no_proposal_conflicts,
    detect_proposal_conflicts,
)
from mnemosyne.benchmarks.solver import PlanProposal


def proposal(
    *,
    proposal_id: str,
    tenant_id: str = "tenant:test",
    workflow_id: str = "workflow:test",
    entity_id: str = "entity:test",
    route: list[str] | None = None,
) -> PlanProposal:
    return PlanProposal(
        proposal_id=proposal_id,
        case_id=f"case:{proposal_id}",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        entity_id=entity_id,
        app_id="campus_tour",
        schema_id="campus_tour.transition",
        route=route or ["S", "D", "A", "B", "L", "S"],
        steps=[],
        attrs={},
        certificate=None,
    )


def test_duplicate_proposal_ids_conflict():
    left = proposal(proposal_id="proposal:same", entity_id="entity:a")
    right = proposal(proposal_id="proposal:same", entity_id="entity:b")

    report = detect_proposal_conflicts([left, right])

    assert report.ok is False
    assert report.error_codes == ["DUPLICATE_PROPOSAL_ID"]
    assert report.conflicts[0].scope == "proposal:proposal:same"


def test_same_tenant_same_entity_conflicts():
    left = proposal(proposal_id="proposal:left", entity_id="entity:shared")
    right = proposal(proposal_id="proposal:right", entity_id="entity:shared")

    report = detect_proposal_conflicts([left, right])

    assert report.ok is False
    assert report.error_codes == ["ENTITY_PROPOSAL_CONFLICT"]
    assert "entity:entity:shared" in report.conflicts[0].scope


def test_different_entities_do_not_conflict():
    left = proposal(proposal_id="proposal:left", entity_id="entity:left")
    right = proposal(proposal_id="proposal:right", entity_id="entity:right")

    report = detect_proposal_conflicts([left, right])

    assert report.ok is True
    assert report.conflicts == []


def test_different_tenants_do_not_conflict_even_with_same_entity_id():
    left = proposal(
        proposal_id="proposal:left",
        tenant_id="tenant:left",
        entity_id="entity:shared",
    )
    right = proposal(
        proposal_id="proposal:right",
        tenant_id="tenant:right",
        entity_id="entity:shared",
    )

    report = detect_proposal_conflicts([left, right])

    assert report.ok is True
    assert report.conflicts == []


def test_assert_no_proposal_conflicts_raises_on_conflict():
    left = proposal(proposal_id="proposal:left", entity_id="entity:shared")
    right = proposal(proposal_id="proposal:right", entity_id="entity:shared")

    with pytest.raises(ValueError, match="ENTITY_PROPOSAL_CONFLICT"):
        assert_no_proposal_conflicts([left, right])


def test_assert_no_proposal_conflicts_allows_non_conflicting_set():
    left = proposal(proposal_id="proposal:left", entity_id="entity:left")
    right = proposal(proposal_id="proposal:right", entity_id="entity:right")

    assert_no_proposal_conflicts([left, right])
