from __future__ import annotations

from datetime import datetime, timezone

import pytest

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

T = "tenant:r47-package-candidates"
W = "workflow:r47-package-candidates"
G = "tx:r47-package-candidates"
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


def domain_candidate(rid: str = "rid:domain-repair:1") -> TransitionCandidate:
    return TransitionCandidate(
        rid=rid,
        op_id=rid,
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
        metadata={},
        extension={"kind": "domain_repair"},
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
        validator_id="test.validator",
        validator_version="1.0",
        timestamp=FT,
    )


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def package() -> RecoveryProposalPackage:
    return RecoveryProposalPackage(
        package_id="pkg:c1:repair:1",
        commitment_id="c1",
        proposal_ref="proposal:repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[
            domain_candidate("rid:domain-repair:1"),
            domain_candidate("rid:domain-repair:2"),
        ],
        rationale="Repair stale dependent entity.",
        validator_context={"source": "runtime"},
        created_from_record_id="rid:commitment-fire",
        created_by="r47.test",
    )


async def seed_fired_commitment(store: SQLiteStore) -> None:
    c = commitment()

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
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


def test_package_proposal_candidate_records_reference_not_domain_candidates():
    candidate = make_package_proposal_candidate(
        tenant_id=T,
        tx_group_id=G,
        package=package(),
        dependency_scope={"entity_id": DOMAIN_EID},
        workflow_id=W,
        rid="rid:commitment-proposal",
    )

    event = event_from_extension(candidate.extension)
    ref = proposal_package_reference_from_event_payload(event.payload)

    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_proposal_emitted"
    assert candidate.state_after == "proposed"
    assert candidate.metadata["proposal_package_id"] == "pkg:c1:repair:1"
    assert candidate.metadata["proposal_candidate_rids"] == [
        "rid:domain-repair:1",
        "rid:domain-repair:2",
    ]

    assert ref is not None
    assert ref["package_id"] == "pkg:c1:repair:1"
    assert ref["candidate_rids"] == ["rid:domain-repair:1", "rid:domain-repair:2"]
    assert "proposed_domain_candidates" not in ref


def test_package_proposal_candidate_rejects_out_of_scope_package():
    bad_package = RecoveryProposalPackage(
        package_id="pkg:c1:bad",
        commitment_id="c1",
        proposal_ref="proposal:bad",
        proposal_scope={"entity_id": "domain:outside"},
        proposed_domain_candidates=[domain_candidate()],
    )

    with pytest.raises(ValueError, match="outside commitment dependency scope"):
        make_package_proposal_candidate(
            tenant_id=T,
            tx_group_id=G,
            package=bad_package,
            dependency_scope={"entity_id": DOMAIN_EID},
            workflow_id=W,
        )


def test_package_proposal_candidate_rejects_commitment_fsm_candidates_inside_package():
    bad_inner_candidate = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:bad-inner-commitment-candidate",
    )
    bad_package = RecoveryProposalPackage(
        package_id="pkg:c1:bad-commitment-candidate",
        commitment_id="c1",
        proposal_ref="proposal:bad",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[bad_inner_candidate],
    )

    with pytest.raises(ValueError, match="only domain candidates"):
        make_package_proposal_candidate(
            tenant_id=T,
            tx_group_id=G,
            package=bad_package,
            dependency_scope={"entity_id": DOMAIN_EID},
            workflow_id=W,
        )


@pytest.mark.asyncio
async def test_committing_package_proposal_candidate_does_not_mutate_domain_state():
    store = SQLiteStore()

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

    await seed_fired_commitment(store)

    candidate = make_package_proposal_candidate(
        tenant_id=T,
        tx_group_id=G,
        package=package(),
        dependency_scope={"entity_id": DOMAIN_EID},
        workflow_id=W,
        rid="rid:commitment-proposal",
    )

    validator = Validator(build_commitment_fsm_registry())
    candidate_batch = batch("batch:package-backed-proposal", [candidate])
    validation = await validator.validate_batch(candidate_batch, store)

    assert validation.ok

    records = await validator.records_from_batch(candidate_batch, store)
    committed = await store.commit_batch(candidate_batch, records)

    assert len(committed) == 1
    assert committed[0].fsm == "mnemosyne.commitment"
    assert committed[0].action_type == "commitment_proposal_emitted"

    index = await active_commitment_index_from_store(store, tenant_id=T, workflow_id=W)
    assert index.status("c1") == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]

    # The package's proposed domain records were not admitted into CTL.
    assert await store.get_record(T, "rid:domain-repair:1") is None
    assert await store.get_record(T, "rid:domain-repair:2") is None
