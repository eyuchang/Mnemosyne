from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
from datetime import date, datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = REALM_ROOT / "cases" / "j2_jssp_simple_dynamic.json"

TENANT_ID = "tenant:realm-j2-api-bound"
WORKFLOW_ID = "workflow:realm-j2-api-bound"
BASELINE_TX_GROUP_ID = "tx:realm-j2:baseline"
REPAIR_TX_GROUP_ID = "tx:realm-j2:repair-admission"
FINALIZE_TX_GROUP_ID = "tx:realm-j2:commitment-finalization"

from mnemosyne.api.audit import (  # noqa: E402
    audit_active_commitments,
    audit_recovery_lineage,
    list_unresolved_commitments,
)
from mnemosyne.benchmarks.jssp_disruption_commitments import (  # noqa: E402
    register_schedule_commitments,
    signal_machine_breakdown,
)
from mnemosyne.benchmarks.jssp_disruptions import (  # noqa: E402
    JSSPBaselineSchedule,
    JSSPOperation,
    JSSPScheduledOperation,
    MachineBreakdown,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_recovery_proposals import (  # noqa: E402
    emit_recovery_proposals_for_disruption,
)
from mnemosyne.benchmarks.jssp_repair_admission import (  # noqa: E402
    admit_and_finalize_repair_candidates_from_proposal_batch,
    repair_candidates_from_proposal_batch,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (  # noqa: E402
    JSSP_FSM_ID,
    admit_baseline_schedule,
)
from mnemosyne.store.sqlite import SQLiteStore  # noqa: E402

from benchmarks.realm.scripts.run_jssp_j2_recovery_baseline import (  # noqa: E402
    _build_greedy_schedule,
    _machine_breakdown,
)


@dataclass(frozen=True)
class J2ApiBoundRecoveryResult:
    output_root: Path
    files: dict[str, Path]
    registered_commitment_count: int
    fired_commitment_count: int
    repair_candidate_count: int
    repair_admission_ok: bool
    finalization_ok: bool
    admitted_commitment_count: int
    live_commitment_count: int
    unresolved_after_finalization: int


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_case() -> dict[str, Any]:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def _make_validator() -> Any:
    from mnemosyne.benchmarks.realm_runner import make_default_validator

    return make_default_validator()


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return "<timestamp>"
    if isinstance(value, date):
        return value.isoformat()
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _json_safe(vars(value))
    return value


def _operation_to_jssp(row: dict[str, Any]) -> JSSPScheduledOperation:
    operation = JSSPOperation(
        job_id=row["job_id"],
        operation_id=f"O{row['operation_index']}",
        machine_id=row["machine"],
        duration=int(row["duration"]),
        sequence_index=int(row["operation_index"]),
    )
    return JSSPScheduledOperation(
        operation=operation,
        start=int(row["start"]),
        end=int(row["end"]),
    )


def _realm_j2_schedule(case: dict[str, Any]) -> tuple[JSSPBaselineSchedule, list[dict[str, Any]]]:
    baseline_rows = _build_greedy_schedule(case)
    operations = tuple(_operation_to_jssp(row) for row in baseline_rows)
    schedule = JSSPBaselineSchedule(case_id="realm-j2", operations=operations)
    return schedule, baseline_rows


def _realm_j2_breakdown(case: dict[str, Any]) -> MachineBreakdown:
    disruption = _machine_breakdown(case)
    machine = disruption["machine"]
    unavailable_start = int(disruption["unavailable_start"])
    unavailable_end = int(disruption["unavailable_end"])

    return MachineBreakdown(
        event_id=f"realm-j2:breakdown:{machine}:{unavailable_start}-{unavailable_end}",
        machine_id=machine,
        unavailable_start=unavailable_start,
        unavailable_end=unavailable_end,
    )


def _candidate_summary(candidates: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        attrs = candidate.extension.get("attrs_after", {})
        rows.append(
            {
                "rid": candidate.rid,
                "eid": candidate.eid,
                "action_type": candidate.action_type,
                "start": attrs.get("start"),
                "end": attrs.get("end"),
                "operation_key": candidate.metadata.get("operation_key"),
            }
        )
    return sorted(rows, key=lambda item: (str(item["start"]), str(item["rid"])))


async def run_j2_api_bound_recovery_async(
    output_root: str | Path | None = None,
    *,
    store: Any | None = None,
    validator: Any | None = None,
) -> J2ApiBoundRecoveryResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    store = store or SQLiteStore()
    validator = validator or _make_validator()

    case = _load_case()
    schedule, baseline_rows = _realm_j2_schedule(case)
    disruption = _realm_j2_breakdown(case)

    baseline_admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
        tx_group_id=BASELINE_TX_GROUP_ID,
        schedule=schedule,
    )

    registrations = await register_schedule_commitments(
        store=store,
        tenant_id=TENANT_ID,
        tx_group_id=BASELINE_TX_GROUP_ID,
        workflow_id=WORKFLOW_ID,
        schedule=schedule,
    )

    disruption_signal = await signal_machine_breakdown(
        store=store,
        tenant_id=TENANT_ID,
        tx_group_id=BASELINE_TX_GROUP_ID,
        workflow_id=WORKFLOW_ID,
        schedule=schedule,
        disruption=disruption,
    )

    proposal_batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=TENANT_ID,
        tx_group_id=BASELINE_TX_GROUP_ID,
        workflow_id=WORKFLOW_ID,
        schedule=schedule,
        disruption_signal=disruption_signal,
    )

    repair_candidates = repair_candidates_from_proposal_batch(proposal_batch)

    repair_admission, finalization = await admit_and_finalize_repair_candidates_from_proposal_batch(
        store=store,
        validator=validator,
        tenant_id=TENANT_ID,
        repair_tx_group_id=REPAIR_TX_GROUP_ID,
        finalize_tx_group_id=FINALIZE_TX_GROUP_ID,
        workflow_id=WORKFLOW_ID,
        proposal_batch=proposal_batch,
    )

    active_rows = await audit_active_commitments(
        store=store,
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
    )
    recovery_rows = await audit_recovery_lineage(
        store=store,
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
    )
    unresolved = await list_unresolved_commitments(
        store=store,
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
    )

    admitted_commitment_ids = sorted(
        row.commitment_id for row in active_rows if row.status == "admitted"
    )
    live_commitment_ids = sorted(
        row.commitment_id for row in active_rows if row.status == "live"
    )
    fired_commitment_ids = sorted(
        row.commitment_id for row in active_rows if row.status == "fired"
    )

    affected_operation_keys = list(disruption_signal.affected_operation_keys)
    state_views_after_admission = []
    for operation_key in sorted(affected_operation_keys):
        state_view = await store.get_state_view(
            TENANT_ID,
            schedule_entity_id(schedule.case_id, operation_key),
            JSSP_FSM_ID,
        )
        state_views_after_admission.append(
            {
                "operation_key": operation_key,
                "entity_id": schedule_entity_id(schedule.case_id, operation_key),
                "state": state_view.state,
                "version": state_view.version,
                "attrs": dict(state_view.attrs),
            }
        )

    artifact = {
        "schema_version": "realm_jssp_j2_api_bound_recovery.v1",
        "case_id": "J2",
        "source_case_path": "benchmarks/realm/cases/j2_jssp_simple_dynamic.json",
        "api_sequence": [
            "admit_baseline_schedule",
            "register_schedule_commitments",
            "signal_machine_breakdown",
            "emit_recovery_proposals_for_disruption",
            "admit_and_finalize_repair_candidates_from_proposal_batch",
            "audit_active_commitments",
            "audit_recovery_lineage",
            "list_unresolved_commitments",
        ],
        "tenant_id": TENANT_ID,
        "workflow_id": WORKFLOW_ID,
        "jssp_schedule": {
            "case_id": schedule.case_id,
            "operation_count": len(schedule.operations),
            "operation_keys": list(schedule.operation_keys),
            "makespan": schedule.makespan,
            "baseline_rows": baseline_rows,
        },
        "disruption": {
            "event_id": disruption.event_id,
            "type": "machine_breakdown",
            "machine_id": disruption.machine_id,
            "unavailable_start": disruption.unavailable_start,
            "unavailable_end": disruption.unavailable_end,
        },
        "results": {
            "baseline_admission_ok": baseline_admission.ok,
            "registered_commitment_count": len(registrations),
            "registered_commitment_operation_keys": [
                item.operation_key for item in registrations
            ],
            "registered_commitment_ids": [
                item.commitment_id for item in registrations
            ],
            "registration_ok": all(item.result.ok for item in registrations),
            "disruption_signal_ok": disruption_signal.ok,
            "affected_operation_keys": affected_operation_keys,
            "fired_commitment_count": len(affected_operation_keys),
            "proposal_batch_ok": proposal_batch.ok,
            "proposal_commitment_ids": list(proposal_batch.commitment_ids),
            "repair_candidate_count": len(repair_candidates),
            "repair_candidates": _candidate_summary(repair_candidates),
            "repair_admission_ok": repair_admission.ok,
            "repair_admission_committed_rids": list(repair_admission.committed_rids),
            "finalization_ok": finalization.ok,
            "finalization_admitted_record_ids": list(finalization.admitted_record_ids),
            "finalization_commitment_ids": list(finalization.commitment_ids),
            "active_commitment_audit_count": len(active_rows),
            "recovery_lineage_count": len(recovery_rows),
            "admitted_commitment_count": len(admitted_commitment_ids),
            "live_commitment_count": len(live_commitment_ids),
            "fired_commitment_count_after_finalization": len(fired_commitment_ids),
            "unresolved_after_finalization": unresolved.count,
        },
        "state_views_after_admission": state_views_after_admission,
        "audit": {
            "admitted_commitment_ids": admitted_commitment_ids,
            "live_commitment_ids": live_commitment_ids,
            "fired_commitment_ids_after_finalization": fired_commitment_ids,
            "active_rows": _json_safe(active_rows),
            "recovery_rows": _json_safe(recovery_rows),
        },
        "claims": {
            "api_bound_recovery_claimed": True,
            "active_commitment_memory_claimed": True,
            "admission_boundary_claimed": True,
            "audit_lineage_claimed": True,
            "benchmark_local_recovery_claimed": True,
            "global_schedule_feasibility_after_api_admission_claimed": False,
            "durable_logs_claimed": False,
            "production_runtime_claimed": False,
            "j4_full_recovery_claimed": False,
        },
        "limitations": [
            "This binds REALM J2 to the active commitment, proposal, admission, and audit APIs.",
            "It does not claim production-runtime durable recovery.",
            "It does not claim J4 material/resource recovery.",
            "The current JSSP repair-admission API mutates selected disrupted operation StateViews; full downstream propagation remains future work.",
        ],
    }

    files = {
        "api_bound_json": root / "api_bound" / "j2_jssp_api_bound_recovery.json",
        "report_json": root / "reports" / "j2_jssp_api_bound_recovery_report.json",
        "report_markdown": root / "reports" / "j2_jssp_api_bound_recovery_report.md",
    }

    _write_json(files["api_bound_json"], artifact)
    _write_json(files["report_json"], artifact)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(artifact) + "\n", encoding="utf-8")

    results = artifact["results"]
    return J2ApiBoundRecoveryResult(
        output_root=root,
        files=files,
        registered_commitment_count=results["registered_commitment_count"],
        fired_commitment_count=results["fired_commitment_count"],
        repair_candidate_count=results["repair_candidate_count"],
        repair_admission_ok=results["repair_admission_ok"],
        finalization_ok=results["finalization_ok"],
        admitted_commitment_count=results["admitted_commitment_count"],
        live_commitment_count=results["live_commitment_count"],
        unresolved_after_finalization=results["unresolved_after_finalization"],
    )


def _render_markdown(artifact: dict[str, Any]) -> str:
    results = artifact["results"]
    disruption = artifact["disruption"]

    lines: list[str] = []

    lines.append("# REALM J2 API-Bound JSSP Recovery Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Case: {artifact['case_id']}")
    lines.append(f"- Schedule case id: `{artifact['jssp_schedule']['case_id']}`")
    lines.append(f"- Operation count: {artifact['jssp_schedule']['operation_count']}")
    lines.append(f"- Machine unavailable: `{disruption['machine_id']}`")
    lines.append(f"- Unavailable window: {disruption['unavailable_start']} to {disruption['unavailable_end']}")
    lines.append(f"- Registered commitments: {results['registered_commitment_count']}")
    lines.append(f"- Fired commitments: {results['fired_commitment_count']}")
    lines.append(f"- Repair candidates: {results['repair_candidate_count']}")
    lines.append(f"- Repair admission ok: {results['repair_admission_ok']}")
    lines.append(f"- Finalization ok: {results['finalization_ok']}")
    lines.append(f"- Admitted commitments: {results['admitted_commitment_count']}")
    lines.append(f"- Live commitments: {results['live_commitment_count']}")
    lines.append(f"- Unresolved after finalization: {results['unresolved_after_finalization']}")
    lines.append("")

    lines.append("## API Sequence")
    lines.append("")
    for step in artifact["api_sequence"]:
        lines.append(f"- `{step}`")
    lines.append("")

    lines.append("## Affected Operations")
    lines.append("")
    for operation_key in results["affected_operation_keys"]:
        lines.append(f"- `{operation_key}`")
    lines.append("")

    lines.append("## Repair Candidates")
    lines.append("")
    lines.append("| RID | Entity | Start | End |")
    lines.append("|---|---|---:|---:|")
    for candidate in results["repair_candidates"]:
        lines.append(
            f"| `{candidate['rid']}` | `{candidate['eid']}` | "
            f"{candidate['start']} | {candidate['end']} |"
        )
    lines.append("")

    lines.append("## Claims")
    lines.append("")
    for key, value in artifact["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for item in artifact["limitations"]:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def run_j2_api_bound_recovery(
    output_root: str | Path | None = None,
) -> J2ApiBoundRecoveryResult:
    return asyncio.run(run_j2_api_bound_recovery_async(output_root))


def main() -> None:
    result = run_j2_api_bound_recovery()
    print("R6.8 REALM J2 API-bound recovery")
    print(f"output_root: {result.output_root}")
    print(f"registered_commitment_count: {result.registered_commitment_count}")
    print(f"fired_commitment_count: {result.fired_commitment_count}")
    print(f"repair_candidate_count: {result.repair_candidate_count}")
    print(f"repair_admission_ok: {result.repair_admission_ok}")
    print(f"finalization_ok: {result.finalization_ok}")
    print(f"admitted_commitment_count: {result.admitted_commitment_count}")
    print(f"live_commitment_count: {result.live_commitment_count}")
    print(f"unresolved_after_finalization: {result.unresolved_after_finalization}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
