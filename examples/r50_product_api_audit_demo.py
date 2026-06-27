from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mnemosyne.api import (
    audit_active_commitments,
    audit_recovery_lineage,
    create_recovery_proposal_package,
    emit_package_backed_proposal,
    fire_active_commitment,
    list_unresolved_commitments,
    register_active_commitment,
    validate_and_commit_active_recovery,
)
from mnemosyne.core.commitments import ActiveCommitment
from mnemosyne.core.models import TransitionCandidate
from mnemosyne.core.recovery import RecoveryContext, RecoveryProposal
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r50-demo"
W = "workflow:r50-demo"
G = "tx:r50-demo"
DOMAIN_EID = "domain:entity:demo"
DOMAIN_FSM = "domain.fsm"


@dataclass(frozen=True)
class R50ProductApiDemoResult:
    active_commitment_ids: list[str]
    unresolved_commitment_ids: list[str]
    recovery_record_ids: list[str]
    recovery_action_types: list[str]
    package_record_ids: list[str]
    package_action_types: list[str]
    audit_statuses: dict[str, str]
    recovery_lineage_actions: list[str]
    committed_only_commitment_fsm: bool


def commitment(commitment_id: str) -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id=commitment_id,
        commitment_type="dependency_guard",
        description=f"R5.0 demo commitment {commitment_id}.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def proposal_provider(
    _commitment: ActiveCommitment,
    _context: RecoveryContext,
) -> Iterable[RecoveryProposal]:
    return [
        RecoveryProposal(
            proposal_ref="proposal:r50-demo-runtime-recovery",
            proposal_scope={"entity_id": DOMAIN_EID},
            rationale="Demonstrate product-facing active recovery API.",
        )
    ]


def inert_domain_candidate() -> TransitionCandidate:
    return TransitionCandidate(
        rid="rid:r50-demo-domain-repair-candidate",
        op_id="op:r50-demo-domain-repair-candidate",
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        binding_id=None,
        eid=DOMAIN_EID,
        fsm=DOMAIN_FSM,
        fsm_version="1.0",
        state_before="stale",
        state_after="repaired",
        action_type="domain_repair",
        triggers=[],
        dependencies=[],
        metadata={"source": "r50_product_api_demo"},
        extension={"kind": "domain_repair"},
        app_id="demo",
        app_version="1.0",
        schema_id="demo.domain.repair",
        schema_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id=None,
        validator_version=None,
    )


async def run_demo() -> R50ProductApiDemoResult:
    store = SQLiteStore()

    # Path A: commitment API + recovery API.
    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment("c-runtime"),
        rid="rid:r50-demo-register-runtime",
        batch_id="batch:r50-demo-register-runtime",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c-runtime",
        reason="dependency_changed",
        rid="rid:r50-demo-fire-runtime",
        batch_id="batch:r50-demo-fire-runtime",
    )

    recovery = await validate_and_commit_active_recovery(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        batch_id="batch:r50-demo-runtime-recovery",
        proposal_provider=proposal_provider,
    )

    # Path B: commitment API + proposal package API.
    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment("c-package"),
        rid="rid:r50-demo-register-package",
        batch_id="batch:r50-demo-register-package",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c-package",
        reason="dependency_changed",
        rid="rid:r50-demo-fire-package",
        batch_id="batch:r50-demo-fire-package",
    )

    package = create_recovery_proposal_package(
        package_id="pkg:r50-demo-package-repair",
        commitment_id="c-package",
        proposal_ref="proposal:r50-demo-package-repair",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[inert_domain_candidate()],
        rationale="Demonstrate package-backed proposal without domain mutation.",
        created_from_record_id="rid:r50-demo-fire-package",
        created_by="r50_product_api_demo",
    )

    package_result = await emit_package_backed_proposal(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        package=package,
        commitment=commitment("c-package"),
        rid="rid:r50-demo-package-proposal",
        batch_id="batch:r50-demo-package-proposal",
    )

    audit_rows = await audit_active_commitments(
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

    domain_candidate_record = await store.get_record(
        T,
        "rid:r50-demo-domain-repair-candidate",
    )

    return R50ProductApiDemoResult(
        active_commitment_ids=[row.commitment_id for row in audit_rows],
        unresolved_commitment_ids=unresolved.commitment_ids,
        recovery_record_ids=recovery.committed_rids,
        recovery_action_types=recovery.committed_action_types,
        package_record_ids=package_result.committed_rids,
        package_action_types=package_result.committed_action_types,
        audit_statuses={row.commitment_id: row.status for row in audit_rows},
        recovery_lineage_actions=[row.action_type for row in recovery_lineage],
        committed_only_commitment_fsm=(
            recovery.committed_only_commitment_fsm
            and package_result.committed_only_commitment_fsm
            and domain_candidate_record is None
        ),
    )


def main() -> None:
    result = asyncio.run(run_demo())

    print("R5.0 product API demo")
    print(f"active commitments: {result.active_commitment_ids}")
    print(f"unresolved commitments: {result.unresolved_commitment_ids}")
    print(f"recovery records: {result.recovery_record_ids}")
    print(f"package records: {result.package_record_ids}")
    print(f"audit statuses: {result.audit_statuses}")
    print(f"recovery lineage actions: {result.recovery_lineage_actions}")
    print(f"commitment-FSM only: {result.committed_only_commitment_fsm}")


if __name__ == "__main__":
    main()
