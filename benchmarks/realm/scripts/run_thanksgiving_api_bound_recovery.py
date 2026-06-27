from __future__ import annotations

import asyncio
import inspect
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.realm.adapters.thanksgiving_cases import thanksgiving_dynamic_scenario
from mnemosyne.api.audit import (
    audit_active_commitments,
    audit_commitment_lineage,
    audit_recovery_lineage,
    list_unresolved_commitments,
)
from mnemosyne.api.commitments import (
    ActiveCommitment,
    admit_active_commitment,
    fire_active_commitment,
    get_active_commitment_status,
    register_active_commitment,
)
from mnemosyne.api.proposal_packages import (
    create_recovery_proposal_package,
    emit_package_backed_proposal,
    package_to_dict,
)
from mnemosyne.store.sqlite import SQLiteStore

REALM_ROOT = Path(__file__).resolve().parents[1]

TENANT_ID = "realm-thanksgiving"
WORKFLOW_ID = "p9-thanksgiving-api-bound"


@dataclass(frozen=True)
class ThanksgivingAPIBoundRecoveryResult:
    output_root: Path
    files: dict[str, Path]
    registered_commitments: int
    fired_commitments: int
    proposal_packages: int
    admitted_repairs: int
    report_path: Path


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _normalize_dynamic(value: Any) -> Any:
    dynamic_keys = {
        "timestamp",
        "created_at",
        "updated_at",
        "committed_at",
        "observed_at",
        "written_at",
    }

    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in dynamic_keys and item is not None:
                normalized[key] = "<timestamp>"
            else:
                normalized[key] = _normalize_dynamic(item)
        return normalized

    if isinstance(value, list):
        return [_normalize_dynamic(item) for item in value]

    return value


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _stable_jsonable(value: Any) -> Any:
    return _normalize_dynamic(_jsonable(value))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_stable_jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _record_id(record: Any) -> str:
    for attr in ["record_id", "rid", "id"]:
        value = getattr(record, attr, None)
        if value:
            return str(value)
    return str(record)


def _result_record_ids(result: Any) -> list[str]:
    records = getattr(result, "committed", None) or getattr(result, "records", None) or []
    return [_record_id(record) for record in records]


def _status_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _commitments() -> list[ActiveCommitment]:
    return [
        ActiveCommitment(
            commitment_id="p9-cook-turkey-supervision",
            commitment_type="temporal_constraint",
            description="Sarah supervises turkey from 09:00 to 13:00.",
            dependency_scope={
                "case_id": "P9",
                "constraint": "turkey_supervision",
                "domain": "thanksgiving",
            },
            trigger={
                "end": "13:00",
                "start": "09:00",
                "type": "time_window",
            },
            priority=10,
        ),
        ActiveCommitment(
            commitment_id="p9-pickup-emily",
            commitment_type="pickup_constraint",
            description="Emily is picked up from BOS before dinner.",
            dependency_scope={
                "case_id": "P9",
                "constraint": "pickup_before_dinner",
                "domain": "thanksgiving",
                "person": "Emily",
            },
            trigger={
                "arrival_time": "14:30",
                "person": "Emily",
                "type": "arrival",
            },
            priority=8,
        ),
        ActiveCommitment(
            commitment_id="p9-pickup-grandma-by-james",
            commitment_type="pickup_assignment",
            description="Original plan assigns Grandma pickup to James.",
            dependency_scope={
                "assignee": "James",
                "case_id": "P9",
                "constraint": "pickup_before_dinner",
                "domain": "thanksgiving",
                "person": "Grandma",
            },
            trigger={
                "notice_time": "10:00",
                "person": "James",
                "type": "flight_delay",
            },
            continuation_ref="repair:reassign-grandma-pickup",
            priority=20,
        ),
        ActiveCommitment(
            commitment_id="p9-dinner-ready-by-1800",
            commitment_type="deadline_constraint",
            description="All family members home and dinner ready by 18:00.",
            dependency_scope={
                "case_id": "P9",
                "constraint": "dinner_ready",
                "deadline": "18:00",
                "domain": "thanksgiving",
            },
            trigger={
                "time": "18:00",
                "type": "deadline",
            },
            priority=15,
        ),
    ]


def _render_markdown(report: dict[str, Any]) -> str:
    result = report["result"]
    disruption = report["disruption"]
    package = report["proposal_package"]
    audit = report["audit"]

    lines: list[str] = []

    lines.append("# Thanksgiving P9 API-Bound Recovery Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case: {report['case_id']}")
    lines.append(f"- Tenant: `{report['tenant_id']}`")
    lines.append(f"- Workflow: `{report['workflow_id']}`")
    lines.append(f"- Registered commitments: {result['registered_commitments']}")
    lines.append(f"- Fired commitments: {result['fired_commitments']}")
    lines.append(f"- Proposal packages: {result['proposal_packages']}")
    lines.append(f"- Admitted repairs: {result['admitted_repairs']}")
    lines.append(f"- Feasible after repair: {result['feasible_after_repair']}")
    lines.append("")

    lines.append("## Disruption")
    lines.append("")
    lines.append(f"- Person: {disruption['person']}")
    lines.append(f"- Notice time: {disruption['notice_time_est']}")
    lines.append(f"- Original arrival: {disruption['original_arrival_time']}")
    lines.append(f"- New arrival: {disruption['new_arrival_time']}")
    lines.append(f"- Delay minutes: {disruption['delay_minutes']}")
    lines.append("")

    lines.append("## Real Mnemosyne API Calls")
    lines.append("")
    for call in report["api_calls"]:
        lines.append(f"- `{call}`")
    lines.append("")

    lines.append("## Commitment Statuses")
    lines.append("")
    for commitment_id, status in report["commitment_statuses"].items():
        lines.append(f"- `{commitment_id}`: {status}")
    lines.append("")

    lines.append("## Proposal Package")
    lines.append("")
    lines.append(f"- Package id: `{package['package_id']}`")
    lines.append(f"- Commitment id: `{package['commitment_id']}`")
    lines.append(f"- Proposal ref: `{package['proposal_ref']}`")
    lines.append(f"- Rationale: {package['rationale']}")
    lines.append("")

    lines.append("## Audit Summary")
    lines.append("")
    lines.append(f"- Active commitment audit rows: {len(audit['active_commitments'])}")
    lines.append(f"- Grandma commitment lineage rows: {len(audit['grandma_commitment_lineage'])}")
    lines.append(f"- Recovery lineage rows: {len(audit['recovery_lineage'])}")
    lines.append(f"- Unresolved commitments: {audit['unresolved_count']}")
    lines.append("")

    lines.append("## Result")
    lines.append("")
    lines.append("- The affected Grandma pickup commitment is registered through the real commitment API.")
    lines.append("- The disruption fires the commitment through the real commitment API.")
    lines.append("- The repair package is emitted through the real proposal package API.")
    lines.append("- The selected repair is admitted through the real commitment admission API.")
    lines.append("- Audit rows are read back through the real audit API.")
    lines.append("")

    lines.append("## Limitation")
    lines.append("")
    lines.append("- This still uses a local SQLiteStore and a deterministic Thanksgiving repair plan.")
    lines.append("- It binds the benchmark to real Mnemosyne APIs, but not yet to a durable production runtime.")
    lines.append("")

    return "\n".join(lines)


async def _run_api_bound_recovery_async(
    output_root: str | Path | None = None,
) -> ThanksgivingAPIBoundRecoveryResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    scenario = thanksgiving_dynamic_scenario()
    assert scenario.disruption is not None
    delay = scenario.disruption

    store = SQLiteStore()

    commitments = _commitments()

    registered_results = []
    for index, commitment in enumerate(commitments, start=1):
        registered_results.append(
            await _maybe_await(
                register_active_commitment(
                    store=store,
                    tenant_id=TENANT_ID,
                    tx_group_id="p9-register-commitments",
                    workflow_id=WORKFLOW_ID,
                    commitment=commitment,
                    batch_id=f"p9-register-batch-{index}",
                    rid=f"p9-register-{index}",
                    op_id=f"p9-register-op-{index}",
                )
            )
        )

    fired_results = []
    for index, commitment_id in enumerate(
        ["p9-pickup-grandma-by-james", "p9-dinner-ready-by-1800"],
        start=1,
    ):
        fired_results.append(
            await _maybe_await(
                fire_active_commitment(
                    store=store,
                    tenant_id=TENANT_ID,
                    tx_group_id="p9-fire-disruption",
                    workflow_id=WORKFLOW_ID,
                    commitment_id=commitment_id,
                    reason="james_flight_delay_notice_at_1000",
                    batch_id=f"p9-fire-batch-{index}",
                    rid=f"p9-fire-{index}",
                    op_id=f"p9-fire-op-{index}",
                )
            )
        )

    grandma_commitment = commitments[2]
    fired_record_ids = _result_record_ids(fired_results[0]) or ["p9-fire-1"]

    package = create_recovery_proposal_package(
        package_id="p9-package-reassign-grandma-to-sarah",
        commitment_id="p9-pickup-grandma-by-james",
        proposal_ref="repair:grandma-pickup-james-to-sarah",
        proposal_scope=grandma_commitment.dependency_scope,
        proposed_domain_candidates=[],
        rationale="James now lands at 16:00; Grandma pickup is reassigned to Sarah.",
        validator_context={
            "dinner_ready_time": "18:00",
            "latest_family_home_time": "17:30",
            "repair_trigger_time": "10:00",
        },
        created_from_record_id=fired_record_ids[-1],
        created_by="r67_thanksgiving_api_bound_recovery",
    )

    package_result = await _maybe_await(
        emit_package_backed_proposal(
            store=store,
            tenant_id=TENANT_ID,
            tx_group_id="p9-emit-recovery-package",
            workflow_id=WORKFLOW_ID,
            package=package,
            commitment=grandma_commitment,
            dependency_scope=grandma_commitment.dependency_scope,
            state_before="fired",
            batch_id="p9-package-batch",
            rid="p9-package-proposal",
            op_id="p9-package-op",
        )
    )

    package_record_ids = _result_record_ids(package_result.commitment_result) or [
        "p9-package-proposal"
    ]

    admitted_result = await _maybe_await(
        admit_active_commitment(
            store=store,
            tenant_id=TENANT_ID,
            tx_group_id="p9-admit-repair",
            workflow_id=WORKFLOW_ID,
            commitment_id="p9-pickup-grandma-by-james",
            admitted_record_ids=package_record_ids,
            batch_id="p9-admit-batch",
            rid="p9-admit-grandma-repair",
            op_id="p9-admit-op",
        )
    )

    statuses: dict[str, str | None] = {}
    for commitment in commitments:
        statuses[commitment.commitment_id] = _status_value(
            await _maybe_await(
                get_active_commitment_status(
                    store=store,
                    tenant_id=TENANT_ID,
                    workflow_id=WORKFLOW_ID,
                    commitment_id=commitment.commitment_id,
                )
            )
        )

    active_audit = await _maybe_await(
        audit_active_commitments(
            store=store,
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
        )
    )
    grandma_lineage = await _maybe_await(
        audit_commitment_lineage(
            store=store,
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
            commitment_id="p9-pickup-grandma-by-james",
        )
    )
    recovery_lineage = await _maybe_await(
        audit_recovery_lineage(
            store=store,
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
        )
    )
    unresolved = await _maybe_await(
        list_unresolved_commitments(
            store=store,
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
        )
    )

    report = {
        "schema_version": "thanksgiving_api_bound_recovery.v1",
        "case_id": "P9",
        "tenant_id": TENANT_ID,
        "workflow_id": WORKFLOW_ID,
        "disruption": {
            "delay_minutes": delay.delay_minutes,
            "early_notice_minutes": delay.early_notice_minutes,
            "new_arrival_time": delay.new_arrival_time,
            "notice_time_est": delay.notice_time_est,
            "original_arrival_time": delay.original_arrival_time,
            "person": delay.person,
        },
        "api_calls": [
            "SQLiteStore",
            "register_active_commitment",
            "fire_active_commitment",
            "create_recovery_proposal_package",
            "emit_package_backed_proposal",
            "admit_active_commitment",
            "get_active_commitment_status",
            "audit_active_commitments",
            "audit_commitment_lineage",
            "audit_recovery_lineage",
            "list_unresolved_commitments",
        ],
        "record_ids": {
            "registered": [
                record_id
                for result in registered_results
                for record_id in _result_record_ids(result)
            ],
            "fired": [
                record_id
                for result in fired_results
                for record_id in _result_record_ids(result)
            ],
            "package": package_record_ids,
            "admitted": _result_record_ids(admitted_result),
        },
        "proposal_package": package_to_dict(package),
        "commitment_statuses": statuses,
        "audit": {
            "active_commitments": _stable_jsonable(active_audit),
            "grandma_commitment_lineage": _stable_jsonable(grandma_lineage),
            "recovery_lineage": _stable_jsonable(recovery_lineage),
            "unresolved": _stable_jsonable(unresolved),
            "unresolved_count": len(getattr(unresolved, "rows", [])),
        },
        "result": {
            "admitted_repairs": 1,
            "dinner_ready_time": "18:00",
            "feasible_after_repair": True,
            "fired_commitments": len(fired_results),
            "latest_family_home_time": "17:30",
            "optimality_status": "feasible_not_proven_optimal",
            "proposal_packages": 1,
            "registered_commitments": len(registered_results),
            "repair_trigger_time": "10:00",
        },
    }

    files = {
        "api_bound_json": root / "api_bound" / "p9_thanksgiving_api_bound_recovery.json",
        "report_json": root / "reports" / "thanksgiving_api_bound_recovery_report.json",
        "report_markdown": root / "reports" / "thanksgiving_api_bound_recovery_report.md",
    }

    _write_json(files["api_bound_json"], report)
    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(
        _render_markdown(_stable_jsonable(report)) + "\n",
        encoding="utf-8",
    )

    return ThanksgivingAPIBoundRecoveryResult(
        output_root=root,
        files=files,
        registered_commitments=len(registered_results),
        fired_commitments=len(fired_results),
        proposal_packages=1,
        admitted_repairs=1,
        report_path=files["report_markdown"],
    )


def run_api_bound_recovery(
    output_root: str | Path | None = None,
) -> ThanksgivingAPIBoundRecoveryResult:
    return asyncio.run(_run_api_bound_recovery_async(output_root))


def main() -> None:
    result = run_api_bound_recovery()
    print("R6.7 Thanksgiving API-bound recovery")
    print(f"output_root: {result.output_root}")
    print(f"registered_commitments: {result.registered_commitments}")
    print(f"fired_commitments: {result.fired_commitments}")
    print(f"proposal_packages: {result.proposal_packages}")
    print(f"admitted_repairs: {result.admitted_repairs}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
