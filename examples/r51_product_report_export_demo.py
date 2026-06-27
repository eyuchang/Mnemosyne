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
    audit_commitment_lineage,
    audit_recovery_lineage,
    commitment_lineage_rows_to_dicts,
    create_recovery_proposal_package,
    emit_package_backed_proposal,
    fire_active_commitment,
    list_unresolved_commitments,
    recovery_lineage_rows_to_dicts,
    register_active_commitment,
    render_active_commitment_audit_markdown,
    render_commitment_lineage_markdown,
    render_recovery_lineage_markdown,
    render_unresolved_commitments_markdown,
    unresolved_commitment_report_to_dict,
    write_json_report,
    write_markdown_report,
)
from mnemosyne.core.commitments import ActiveCommitment
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r51-demo"
W = "workflow:r51-demo"
G = "tx:r51-demo"
DOMAIN_EID = "domain:entity:r51-demo"


@dataclass(frozen=True)
class R51ProductReportExportDemoResult:
    output_dir: Path
    files: dict[str, Path]
    active_commitment_count: int
    unresolved_commitment_count: int
    commitment_lineage_count: int
    recovery_lineage_count: int


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c-report",
        commitment_type="dependency_guard",
        description="R5.1 report export demo commitment.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


async def seed_store(store: SQLiteStore) -> None:
    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:r51-report-register",
        batch_id="batch:r51-report-register",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c-report",
        reason="dependency_changed",
        rid="rid:r51-report-fire",
        batch_id="batch:r51-report-fire",
    )

    package = create_recovery_proposal_package(
        package_id="pkg:r51-report-repair",
        commitment_id="c-report",
        proposal_ref="proposal:r51-report-repair",
        proposal_scope={"entity_id": DOMAIN_EID},
        rationale="Demonstrate product report export over recovery lineage.",
        created_from_record_id="rid:r51-report-fire",
        created_by="r51_product_report_export_demo",
    )

    await emit_package_backed_proposal(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        package=package,
        commitment=commitment(),
        rid="rid:r51-report-proposal",
        batch_id="batch:r51-report-proposal",
    )


async def run_demo(output_dir: str | Path | None = None) -> R51ProductReportExportDemoResult:
    if output_dir is None:
        output_path = Path(tempfile.mkdtemp(prefix="mnemosyne-r51-reports-"))
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore()
    await seed_store(store)

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
    commitment_lineage = await audit_commitment_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c-report",
    )
    recovery_lineage = await audit_recovery_lineage(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c-report",
    )

    files = {
        "active_json": output_path / "active_commitments.json",
        "active_md": output_path / "active_commitments.md",
        "unresolved_json": output_path / "unresolved_commitments.json",
        "unresolved_md": output_path / "unresolved_commitments.md",
        "commitment_lineage_json": output_path / "commitment_lineage.json",
        "commitment_lineage_md": output_path / "commitment_lineage.md",
        "recovery_lineage_json": output_path / "recovery_lineage.json",
        "recovery_lineage_md": output_path / "recovery_lineage.md",
    }

    write_json_report(files["active_json"], active_commitment_audit_rows_to_dicts(active_rows))
    write_markdown_report(
        files["active_md"],
        render_active_commitment_audit_markdown(
            active_rows,
            title="R5.1 Active Commitment Audit",
        ),
    )

    write_json_report(files["unresolved_json"], unresolved_commitment_report_to_dict(unresolved))
    write_markdown_report(
        files["unresolved_md"],
        render_unresolved_commitments_markdown(
            unresolved,
            title="R5.1 Unresolved Commitments",
        ),
    )

    write_json_report(
        files["commitment_lineage_json"],
        commitment_lineage_rows_to_dicts(commitment_lineage),
    )
    write_markdown_report(
        files["commitment_lineage_md"],
        render_commitment_lineage_markdown(
            commitment_lineage,
            title="R5.1 Commitment Lineage",
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
            title="R5.1 Recovery Lineage",
        ),
    )

    return R51ProductReportExportDemoResult(
        output_dir=output_path,
        files=files,
        active_commitment_count=len(active_rows),
        unresolved_commitment_count=unresolved.count,
        commitment_lineage_count=len(commitment_lineage),
        recovery_lineage_count=len(recovery_lineage),
    )


def main() -> None:
    result = asyncio.run(run_demo())

    print("R5.1 product report export demo")
    print(f"output_dir: {result.output_dir}")
    print(f"active_commitment_count: {result.active_commitment_count}")
    print(f"unresolved_commitment_count: {result.unresolved_commitment_count}")
    print(f"commitment_lineage_count: {result.commitment_lineage_count}")
    print(f"recovery_lineage_count: {result.recovery_lineage_count}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
