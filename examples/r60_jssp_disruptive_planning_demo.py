from __future__ import annotations

import asyncio
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mnemosyne.api import (
    active_commitment_audit_rows_to_dicts,
    audit_active_commitments,
    audit_recovery_lineage,
    list_unresolved_commitments,
    recovery_lineage_rows_to_dicts,
    render_active_commitment_audit_markdown,
    render_recovery_lineage_markdown,
    render_unresolved_commitments_markdown,
    unresolved_commitment_report_to_dict,
    write_json_report,
    write_markdown_report,
)
from mnemosyne.apps import AppRegistry
from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.benchmarks.jssp_disruption_commitments import (
    register_schedule_commitments,
    signal_machine_breakdown,
)
from mnemosyne.benchmarks.jssp_disruptions import (
    make_jssp_3x3_baseline_schedule,
    make_machine_breakdown_for_3x3_smoke,
    schedule_entity_id,
)
from mnemosyne.benchmarks.jssp_recovery_proposals import (
    emit_recovery_proposals_for_disruption,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
)
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r60-demo"
W = "workflow:r60-jssp-demo"
G = "tx:r60-jssp-demo"


@dataclass(frozen=True)
class R60JSSPDisruptivePlanningDemoResult:
    output_dir: Path
    files: dict[str, Path]
    baseline_operation_count: int
    registered_commitment_count: int
    affected_operation_keys: list[str]
    fired_commitment_count: int
    proposed_commitment_count: int
    live_commitment_count: int
    recovery_package_count: int
    repair_candidate_rids: list[str]
    schedule_unchanged: bool


def make_validator() -> Validator:
    registry = AppRegistry()
    registry.register(JSSPApp())
    return Validator(
        registry.build_fsm_registry(),
        registry.build_constraint_registry(),
    )


async def _schedule_unchanged(store: SQLiteStore, schedule) -> bool:
    for scheduled_operation in schedule.operations:
        state_view = await store.get_state_view(
            T,
            schedule_entity_id(schedule.case_id, scheduled_operation.key),
            JSSP_FSM_ID,
        )

        if state_view is None:
            return False
        if state_view.state != "scheduled":
            return False
        if state_view.attrs["machine_id"] != scheduled_operation.machine_id:
            return False
        if state_view.attrs["start"] != scheduled_operation.start:
            return False
        if state_view.attrs["end"] != scheduled_operation.end:
            return False
        if state_view.attrs["duration"] != scheduled_operation.duration:
            return False

    return True


async def run_demo(
    output_dir: str | Path | None = None,
) -> R60JSSPDisruptivePlanningDemoResult:
    if output_dir is None:
        output_path = Path(tempfile.mkdtemp(prefix="mnemosyne-r60-jssp-"))
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore()
    validator = make_validator()

    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    admission = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=schedule,
    )
    if not admission.ok:
        raise RuntimeError("baseline schedule admission failed")

    registrations = await register_schedule_commitments(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
    )
    if not all(item.result.ok for item in registrations):
        raise RuntimeError("commitment registration failed")

    disruption_signal = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )
    if not disruption_signal.ok:
        raise RuntimeError("machine breakdown signal failed")

    proposal_batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption_signal=disruption_signal,
    )
    if not proposal_batch.ok:
        raise RuntimeError("recovery proposal emission failed")

    active_rows = await audit_active_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    unresolved = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )
    recovery_lineage = await audit_recovery_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    files = {
        "active_json": output_path / "active_commitments.json",
        "active_md": output_path / "active_commitments.md",
        "unresolved_json": output_path / "unresolved_commitments.json",
        "unresolved_md": output_path / "unresolved_commitments.md",
        "recovery_lineage_json": output_path / "recovery_lineage.json",
        "recovery_lineage_md": output_path / "recovery_lineage.md",
    }

    write_json_report(files["active_json"], active_commitment_audit_rows_to_dicts(active_rows))
    write_markdown_report(
        files["active_md"],
        render_active_commitment_audit_markdown(
            active_rows,
            title="R6.0 JSSP Active Commitment Audit",
        ),
    )

    write_json_report(files["unresolved_json"], unresolved_commitment_report_to_dict(unresolved))
    write_markdown_report(
        files["unresolved_md"],
        render_unresolved_commitments_markdown(
            unresolved,
            title="R6.0 JSSP Unresolved Commitments",
        ),
    )

    write_json_report(
        files["recovery_lineage_json"],
        recovery_lineage_rows_to_dicts(recovery_lineage),
    )
    write_markdown_report(
        files["recovery_lineage_md"],
        render_recovery_lineage_markdown(
            recovery_lineage,
            title="R6.0 JSSP Recovery Lineage",
        ),
    )

    proposed_commitment_count = len(
        [row for row in active_rows if row.status == "proposed"]
    )
    live_commitment_count = len(
        [row for row in active_rows if row.status == "live"]
    )

    return R60JSSPDisruptivePlanningDemoResult(
        output_dir=output_path,
        files=files,
        baseline_operation_count=len(schedule.operations),
        registered_commitment_count=len(registrations),
        affected_operation_keys=disruption_signal.affected_operation_keys,
        fired_commitment_count=len(disruption_signal.fired),
        proposed_commitment_count=proposed_commitment_count,
        live_commitment_count=live_commitment_count,
        recovery_package_count=len(proposal_batch.proposals),
        repair_candidate_rids=proposal_batch.candidate_rids,
        schedule_unchanged=await _schedule_unchanged(store, schedule),
    )


def main() -> None:
    result = asyncio.run(run_demo())

    print("R6.0 JSSP disruptive planning demo")
    print(f"output_dir: {result.output_dir}")
    print(f"baseline_operation_count: {result.baseline_operation_count}")
    print(f"registered_commitment_count: {result.registered_commitment_count}")
    print(f"affected_operation_keys: {result.affected_operation_keys}")
    print(f"fired_commitment_count: {result.fired_commitment_count}")
    print(f"proposed_commitment_count: {result.proposed_commitment_count}")
    print(f"live_commitment_count: {result.live_commitment_count}")
    print(f"recovery_package_count: {result.recovery_package_count}")
    print(f"repair_candidate_rids: {result.repair_candidate_rids}")
    print(f"schedule_unchanged: {result.schedule_unchanged}")

    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
