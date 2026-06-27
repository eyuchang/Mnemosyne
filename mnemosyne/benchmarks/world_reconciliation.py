# File: mnemosyne/benchmarks/world_reconciliation.py
#
# Purpose:
#   Stale-world reconciliation for solver/agent plan proposals.
#
# Stage:
#   R2.3 — stale-world reconciliation.
#
# Design rule:
#   A proposal may be solver-feasible and conflict-free, but still stale if
#   the observed external world has drifted from the assumptions carried by
#   the proposal.
#
#   Stale proposals must be rejected before commit admission.
#
#   Mnemosyne remains the commit authority.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from mnemosyne.benchmarks.solver import PlanProposal


JsonValue = Any
JsonDict = dict[str, Any]


@dataclass(frozen=True)
class WorldAssumption:
    """A world fact assumed by a plan proposal."""

    tenant_id: str
    entity_id: str
    key: str
    expected_value: JsonValue
    source: str = ""
    required: bool = True


@dataclass(frozen=True)
class ObservedWorldFact:
    """A currently observed world fact.

    tenant_id or entity_id may be "*" to indicate a wildcard fact.
    """

    tenant_id: str
    entity_id: str
    key: str
    observed_value: JsonValue
    source: str = ""


@dataclass(frozen=True)
class WorldReconciliationIssue:
    """A mismatch between proposal assumptions and observed world facts."""

    issue_type: str
    tenant_id: str
    entity_id: str
    key: str
    expected_value: JsonValue
    observed_value: JsonValue | None
    message: str


@dataclass(frozen=True)
class WorldReconciliationReport:
    """Result of stale-world reconciliation."""

    ok: bool
    issues: list[WorldReconciliationIssue] = field(default_factory=list)

    @property
    def error_codes(self) -> list[str]:
        return [
            issue.issue_type
            for issue in self.issues
        ]


def _canonical(value: JsonValue) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    )


def _matches_scope(
    *,
    assumption: WorldAssumption,
    fact: ObservedWorldFact,
) -> bool:
    tenant_matches = fact.tenant_id in {"*", assumption.tenant_id}
    entity_matches = fact.entity_id in {"*", assumption.entity_id}

    return (
        tenant_matches
        and entity_matches
        and fact.key == assumption.key
    )


def assumption_from_dict(
    *,
    proposal: PlanProposal,
    raw: JsonDict,
) -> WorldAssumption:
    if "key" not in raw:
        raise ValueError(f"world assumption missing key: {raw}")

    if "expected_value" in raw:
        expected_value = raw["expected_value"]
    elif "value" in raw:
        expected_value = raw["value"]
    else:
        raise ValueError(f"world assumption missing expected_value/value: {raw}")

    return WorldAssumption(
        tenant_id=str(raw.get("tenant_id", proposal.tenant_id)),
        entity_id=str(raw.get("entity_id", proposal.entity_id)),
        key=str(raw["key"]),
        expected_value=expected_value,
        source=str(raw.get("source", "")),
        required=bool(raw.get("required", True)),
    )


def observed_fact_from_dict(raw: JsonDict) -> ObservedWorldFact:
    if "key" not in raw:
        raise ValueError(f"observed world fact missing key: {raw}")

    if "observed_value" in raw:
        observed_value = raw["observed_value"]
    elif "value" in raw:
        observed_value = raw["value"]
    else:
        raise ValueError(f"observed world fact missing observed_value/value: {raw}")

    return ObservedWorldFact(
        tenant_id=str(raw.get("tenant_id", "*")),
        entity_id=str(raw.get("entity_id", "*")),
        key=str(raw["key"]),
        observed_value=observed_value,
        source=str(raw.get("source", "")),
    )


def extract_world_assumptions(
    proposal: PlanProposal,
) -> list[WorldAssumption]:
    raw_items = proposal.attrs.get("world_assumptions", [])

    if raw_items is None:
        return []

    if not isinstance(raw_items, list):
        raise ValueError("proposal attrs.world_assumptions must be a list")

    return [
        assumption_from_dict(
            proposal=proposal,
            raw=item,
        )
        for item in raw_items
    ]


def load_world_snapshot(path: Path) -> list[ObservedWorldFact]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        raw_facts = payload
    elif isinstance(payload, dict):
        raw_facts = payload.get("facts", [])
    else:
        raise ValueError("world snapshot must be a JSON object or list")

    if not isinstance(raw_facts, list):
        raise ValueError("world snapshot facts must be a list")

    return [
        observed_fact_from_dict(raw)
        for raw in raw_facts
    ]


def reconcile_world(
    *,
    proposals: Iterable[PlanProposal],
    observed_facts: Iterable[ObservedWorldFact],
) -> WorldReconciliationReport:
    facts = list(observed_facts)
    issues: list[WorldReconciliationIssue] = []

    for proposal in proposals:
        assumptions = extract_world_assumptions(proposal)

        for assumption in assumptions:
            matching_facts = [
                fact
                for fact in facts
                if _matches_scope(
                    assumption=assumption,
                    fact=fact,
                )
            ]

            if not matching_facts:
                if assumption.required:
                    issues.append(
                        WorldReconciliationIssue(
                            issue_type="WORLD_FACT_MISSING",
                            tenant_id=assumption.tenant_id,
                            entity_id=assumption.entity_id,
                            key=assumption.key,
                            expected_value=assumption.expected_value,
                            observed_value=None,
                            message=(
                                "required observed world fact is missing "
                                "for proposal assumption"
                            ),
                        )
                    )
                continue

            # Prefer the last matching fact in the snapshot. This allows a
            # later observation to override an earlier one within the same
            # snapshot file.
            fact = matching_facts[-1]

            if _canonical(fact.observed_value) != _canonical(assumption.expected_value):
                issues.append(
                    WorldReconciliationIssue(
                        issue_type="STALE_WORLD_FACT",
                        tenant_id=assumption.tenant_id,
                        entity_id=assumption.entity_id,
                        key=assumption.key,
                        expected_value=assumption.expected_value,
                        observed_value=fact.observed_value,
                        message=(
                            "observed world fact differs from proposal assumption"
                        ),
                    )
                )

    return WorldReconciliationReport(
        ok=not issues,
        issues=issues,
    )


def assert_world_reconciled(
    *,
    proposals: Iterable[PlanProposal],
    observed_facts: Iterable[ObservedWorldFact],
) -> None:
    report = reconcile_world(
        proposals=proposals,
        observed_facts=observed_facts,
    )

    if report.ok:
        return

    details = "; ".join(
        f"{issue.issue_type}:{issue.entity_id}:{issue.key}"
        for issue in report.issues
    )

    raise ValueError(f"world reconciliation failed: {details}")
