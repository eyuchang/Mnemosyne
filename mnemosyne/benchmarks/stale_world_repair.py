# File: mnemosyne/benchmarks/stale_world_repair.py
#
# Stage:
#   R2.5 — deterministic repair/replan after stale-world rejection.
#
# Purpose:
#   Convert a stale-world reconciliation failure into a repaired benchmark case,
#   when the repair is deterministic and explicitly supported.
#
# Current supported repair:
#   P1 Campus Tour deadline update.
#
# Design rule:
#   Stale-world repair creates a new proposal. It does not patch committed truth.
#   The repaired proposal must pass the same solver, conflict, reconciliation,
#   validation, and commit path.

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class StaleWorldRepairResult:
    ok: bool
    repaired_case_data: JsonDict | None = None
    repair_actions: list[JsonDict] = field(default_factory=list)
    error_message: str | None = None


def _issues_from_report(reconciliation_report: Any) -> list[JsonDict]:
    if reconciliation_report is None:
        return []

    if isinstance(reconciliation_report, dict):
        issues = reconciliation_report.get("issues", [])
    else:
        issues = getattr(reconciliation_report, "issues", [])

    normalized: list[JsonDict] = []

    for issue in issues:
        if isinstance(issue, dict):
            normalized.append(issue)
        else:
            normalized.append(
                {
                    "issue_type": getattr(issue, "issue_type", None),
                    "tenant_id": getattr(issue, "tenant_id", None),
                    "entity_id": getattr(issue, "entity_id", None),
                    "key": getattr(issue, "key", None),
                    "expected_value": getattr(issue, "expected_value", None),
                    "observed_value": getattr(issue, "observed_value", None),
                    "message": getattr(issue, "message", None),
                }
            )

    return normalized


def _patch_deadline(
    *,
    repaired: JsonDict,
    observed_value: Any,
) -> JsonDict:
    action = {
        "repair_type": "PATCH_DEADLINE_FROM_WORLD_FACT",
        "key": "deadline",
        "observed_value": observed_value,
        "patched_paths": [],
    }

    # The current P1 solver fixture uses top-level `deadline`.
    if "deadline" in repaired:
        repaired["deadline"] = observed_value
        action["patched_paths"].append("deadline")

    # Some benchmark fixtures may also carry a nested REALM metadata block.
    realm_bench = repaired.get("realm_bench")
    if isinstance(realm_bench, dict) and "deadline" in realm_bench:
        realm_bench["deadline"] = observed_value
        action["patched_paths"].append("realm_bench.deadline")

    # Preserve provenance that the case was repaired from observed world facts.
    provenance = repaired.setdefault("provenance", {})
    if isinstance(provenance, dict):
        provenance["stale_world_repair"] = {
            "key": "deadline",
            "observed_value": observed_value,
            "stage": "R2.5",
        }

    return action


def repair_case_data_from_stale_world(
    *,
    case_data: JsonDict,
    reconciliation_report: Any,
) -> StaleWorldRepairResult:
    """Create repaired case data from stale-world reconciliation issues.

    Current conservative support:
    - issue_type must be STALE_WORLD_FACT
    - key must be deadline
    - observed_value must be non-null
    - the input case must expose a patchable deadline field
    """
    issues = _issues_from_report(reconciliation_report)

    if not issues:
        return StaleWorldRepairResult(
            ok=False,
            error_message="no world reconciliation issues to repair",
        )

    repaired = deepcopy(case_data)
    repair_actions: list[JsonDict] = []

    for issue in issues:
        issue_type = issue.get("issue_type")
        key = issue.get("key")
        observed_value = issue.get("observed_value")

        if issue_type != "STALE_WORLD_FACT":
            return StaleWorldRepairResult(
                ok=False,
                error_message=f"unsupported world issue type: {issue_type}",
            )

        if key != "deadline":
            return StaleWorldRepairResult(
                ok=False,
                error_message=f"unsupported stale-world key: {key}",
            )

        if observed_value is None:
            return StaleWorldRepairResult(
                ok=False,
                error_message="cannot repair deadline from null observed value",
            )

        before_deadline = repaired.get("deadline")
        if before_deadline is None:
            realm_bench = repaired.get("realm_bench")
            if isinstance(realm_bench, dict):
                before_deadline = realm_bench.get("deadline")

        action = _patch_deadline(
            repaired=repaired,
            observed_value=observed_value,
        )
        action["previous_value"] = before_deadline

        if not action["patched_paths"]:
            return StaleWorldRepairResult(
                ok=False,
                error_message="case data has no patchable deadline field",
            )

        repair_actions.append(action)

    return StaleWorldRepairResult(
        ok=True,
        repaired_case_data=repaired,
        repair_actions=repair_actions,
    )
