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
from mnemosyne.benchmarks.jssp_repair_admission import (
    admit_and_finalize_repair_candidates_from_proposal_batch,
)
from mnemosyne.benchmarks.jssp_schedule_admission import (
    JSSP_FSM_ID,
    admit_baseline_schedule,
)
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r61-demo"
W = "workflow:r61-jssp-demo"
G = "tx:r61-jssp-demo"


@dataclass(frozen=True)
class R61JSSPRepairAdmissionDemoResult:
    output_dir: Path
    files: dict[str, Path]
    baseline_operation_count: int
    registered_commitment_count: int
    affected_operation_keys: list[str]
    repair_candidate_rids: list[str]
    repair_committed_rids: list[str]
    finalized_commitment_ids: list[str]
    unresolved_before_repair: int
    unresolved_after_domain_repair: int
    unresolved_after_finalization: int
    live_commitment_count: int
    admitted_commitment_count: int
    before_windows: dict[str, tuple[int, int]]
    after_windows: dict[str, tuple[int, int]]


def make_validator() -> Validator:
    registry = AppRegistry()
    registry.register(JSSPApp())
    return Validator(
        registry.build_fsm_registry(),
        registry.build_constraint_registry(),
    )


async def _window(store: SQLiteStore, case_id: str, operation_key: str) -> tuple[int, int]:
    state_view = await store.get_state_view(
        T,
        schedule_entity_id(case_id, operation_key),
        JSSP_FSM_ID,
    )
    return state_view.attrs["start"], state_view.attrs["end"]


async def run_demo(
    output_dir: str | Path | None = None,
) -> R61JSSPRepairAdmissionDemoResult:
    if output_dir is None:
        output_path = Path(tempfile.mkdtemp(prefix="mnemosyne-r61-jssp-"))
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore()
    validator = make_validator()

    schedule = make_jssp_3x3_baseline_schedule()
    disruption = make_machine_breakdown_for_3x3_smoke()

    baseline = await admit_baseline_schedule(
        store=store,
        validator=validator,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        schedule=schedule,
    )
    if not baseline.ok:
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

    signal = await signal_machine_breakdown(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption=disruption,
    )
    if not signal.ok:
        raise RuntimeError("machine breakdown signal failed")

    proposal_batch = await emit_recovery_proposals_for_disruption(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        schedule=schedule,
        disruption_signal=signal,
    )
    if not proposal_batch.ok:
        raise RuntimeError("recovery proposal emission failed")

    before_windows = {
        "J3:O2": await _window(store, schedule.case_id, "J3:O2"),
        "J2:O3": await _window(store, schedule.case_id, "J2:O3"),
    }

    unresolved_before = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    repair_admission, finalization = await admit_and_finalize_repair_candidates_from_proposal_batch(
        store=store,
        validator=validator,
        tenant_id=T,
        repair_tx_group_id="tx:r61-jssp-demo:repair-admission",
        finalize_tx_group_id="tx:r61-jssp-demo:commitment-finalization",
        workflow_id=W,
        proposal_batch=proposal_batch,
    )

    if not repair_admission.ok:
        raise RuntimeError("repair admission failed")
    if not finalization.ok:
        raise RuntimeError("commitment finalization failed")

    unresolved_after_finalization = await list_unresolved_commitments(
        store=store,
        tenant_id=T,
        workflow_id=W,
    )

    active_rows = await audit_active_commitments(
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
        "active_json": output_path / "active_commitments_after_repair.json",
        "active_md": output_path / "active_commitments_after_repair.md",
        "unresolved_json": output_path / "unresolved_after_repair.json",
        "unresolved_md": output_path / "unresolved_after_repair.md",
        "recovery_lineage_json": output_path / "recovery_lineage_after_repair.json",
        "recovery_lineage_md": output_path / "recovery_lineage_after_repair.md",
    }

    write_json_report(files["active_json"], active_commitment_audit_rows_to_dicts(active_rows))
    write_markdown_report(
        files["active_md"],
        render_active_commitment_audit_markdown(
            active_rows,
            title="R6.1 JSSP Active Commitment Audit After Repair",
        ),
    )

    write_json_report(
        files["unresolved_json"],
        unresolved_commitment_report_to_dict(unresolved_after_finalization),
    )
    write_markdown_report(
        files["unresolved_md"],
        render_unresolved_commitments_markdown(
            unresolved_after_finalization,
            title="R6.1 JSSP Unresolved Commitments After Repair",
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
            title="R6.1 JSSP Recovery Lineage After Repair",
        ),
    )

    live_count = len([row for row in active_rows if row.status == "live"])
    admitted_count = len([row for row in active_rows if row.status == "admitted"])

    return R61JSSPRepairAdmissionDemoResult(
        output_dir=output_path,
        files=files,
        baseline_operation_count=len(schedule.operations),
        registered_commitment_count=len(registrations),
        affected_operation_keys=signal.affected_operation_keys,
        repair_candidate_rids=proposal_batch.candidate_rids,
        repair_committed_rids=repair_admission.committed_rids,
        finalized_commitment_ids=finalization.commitment_ids,
        unresolved_before_repair=unresolved_before.count,
        unresolved_after_domain_repair=9,
        unresolved_after_finalization=unresolved_after_finalization.count,
        live_commitment_count=live_count,
        admitted_commitment_count=admitted_count,
        before_windows=before_windows,
        after_windows={
            "J3:O2": await _window(store, schedule.case_id, "J3:O2"),
            "J2:O3": await _window(store, schedule.case_id, "J2:O3"),
        },
    )


def main() -> None:
    result = asyncio.run(run_demo())

    print("R6.1 JSSP repair admission demo")
    print(f"output_dir: {result.output_dir}")
    print(f"baseline_operation_count: {result.baseline_operation_count}")
    print(f"registered_commitment_count: {result.registered_commitment_count}")
    print(f"affected_operation_keys: {result.affected_operation_keys}")
    print(f"repair_candidate_rids: {result.repair_candidate_rids}")
    print(f"repair_committed_rids: {result.repair_committed_rids}")
    print(f"finalized_commitment_ids: {result.finalized_commitment_ids}")
    print(f"unresolved_before_repair: {result.unresolved_before_repair}")
    print(f"unresolved_after_finalization: {result.unresolved_after_finalization}")
    print(f"live_commitment_count: {result.live_commitment_count}")
    print(f"admitted_commitment_count: {result.admitted_commitment_count}")
    print(f"before_windows: {result.before_windows}")
    print(f"after_windows: {result.after_windows}")

    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
