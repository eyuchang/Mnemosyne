from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from pprint import pprint

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentStatus,
    active_commitment_index_from_store,
    build_commitment_fsm_registry,
    event_from_extension,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery.package_candidates import make_package_proposal_candidate
from mnemosyne.core.recovery.packages import (
    RecoveryProposalPackage,
    proposal_package_reference_from_event_payload,
)
from mnemosyne.core.validation import Validator
from mnemosyne.runtime.local import ctl_record_from_transition_candidate
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r47-demo"
W = "workflow:r47-demo"
G = "tx:r47-demo"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def domain_candidate() -> TransitionCandidate:
    return TransitionCandidate(
        rid="rid:domain-repair-candidate",
        op_id="rid:domain-repair-candidate",
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
        metadata={"source": "proposal_package"},
        extension={"kind": "domain_repair", "repair": "refresh_stale_state"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.repair",
        schema_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id=None,
        validator_version=None,
    )


def domain_record(*, rid: str, version: int, state_before: str, state_after: str) -> CTLRecord:
    return CTLRecord(
        rid=rid,
        op_id=rid,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        binding_id=None,
        eid=DOMAIN_EID,
        fsm=DOMAIN_FSM,
        version=version,
        state_before=state_before,
        state_after=state_after,
        action_type="domain_transition",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_transition"},
        app_id="domain",
        app_version="1.0",
        schema_id="domain.transition",
        schema_version="1.0",
        fsm_version="1.0",
        policy_id=None,
        policy_version=None,
        validator_id="demo.validator",
        validator_version="1.0",
        timestamp=FT,
    )


def package() -> RecoveryProposalPackage:
    return RecoveryProposalPackage(
        package_id="pkg:c1:repair:1",
        commitment_id="c1",
        proposal_ref="proposal:repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[domain_candidate()],
        rationale="Repair stale dependent entity.",
        validator_context={"source": "r47_demo"},
        created_from_record_id="rid:commitment-fire",
        created_by="r47.demo",
    )


async def run_demo() -> dict:
    store = SQLiteStore()

    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Package-backed recovery proposal for scoped dependent entity.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )

    await store.commit_batch(
        batch("batch:domain-initial", []),
        [
            domain_record(
                rid="rid:domain-initial",
                version=1,
                state_before="none",
                state_after="stale",
            )
        ],
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
        workflow_id=W,
        rid="rid:commitment-register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:commitment-fire",
    )

    await store.commit_batch(
        batch("batch:commitment-fire", [register, fire]),
        [
            ctl_record_from_transition_candidate(register, version=1),
            ctl_record_from_transition_candidate(fire, version=2),
        ],
    )

    pkg = package()
    proposal_candidate = make_package_proposal_candidate(
        tenant_id=T,
        tx_group_id=G,
        package=pkg,
        dependency_scope=commitment.dependency_scope,
        workflow_id=W,
        rid="rid:commitment-package-proposal",
    )

    validator = Validator(build_commitment_fsm_registry())
    proposal_batch = batch("batch:package-backed-proposal", [proposal_candidate])
    proposal_validation = await validator.validate_batch(proposal_batch, store)
    if not proposal_validation.ok:
        raise RuntimeError(proposal_validation.errors)

    proposal_records = await validator.records_from_batch(proposal_batch, store)
    proposal_committed = await store.commit_batch(proposal_batch, proposal_records)

    event = event_from_extension(proposal_committed[0].extension)
    package_ref = proposal_package_reference_from_event_payload(event.payload)

    index_after_proposal = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    domain_after_proposal = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    inert_candidate_present = await store.get_record(T, "rid:domain-repair-candidate") is not None

    # Later, domain repair is admitted separately as ordinary domain CTL truth.
    await store.commit_batch(
        batch("batch:domain-repair-admission", []),
        [
            domain_record(
                rid="rid:domain-repair-admitted",
                version=2,
                state_before="stale",
                state_after="repaired",
            )
        ],
    )

    domain_after_admission = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    return {
        "proposal_validation_ok": proposal_validation.ok,
        "proposal_committed_actions": [record.action_type for record in proposal_committed],
        "proposal_committed_fsms": [record.fsm for record in proposal_committed],
        "package_ref": package_ref,
        "commitment_status_after_proposal": index_after_proposal.status("c1").value,
        "domain_state_after_proposal": domain_after_proposal.state,
        "domain_version_after_proposal": domain_after_proposal.version,
        "inert_domain_candidate_was_committed": inert_candidate_present,
        "domain_state_after_separate_admission": domain_after_admission.state,
        "domain_version_after_separate_admission": domain_after_admission.version,
        "domain_effective_records_after_separate_admission": domain_after_admission.effective_records,
    }


def main() -> None:
    pprint(asyncio.run(run_demo()))


if __name__ == "__main__":
    main()
