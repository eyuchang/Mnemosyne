from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.api.commitments import (
    fire_active_commitment,
    get_active_commitment_status,
    register_active_commitment,
)
from mnemosyne.api.proposal_packages import (
    create_recovery_proposal_package,
    emit_package_backed_proposal,
    make_package_backed_proposal_candidate,
    package_from_dict,
    package_reference_from_event_payload,
    package_to_dict,
    package_to_reference,
    validate_recovery_proposal_package,
)
from mnemosyne.core.commitments import ActiveCommitment, CommitmentStatus, event_from_extension
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:r50-api-packages"
W = "workflow:r50-api-packages"
G = "tx:r50-api-packages"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Product-facing package API commitment.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


def domain_candidate(rid: str = "rid:domain-repair-candidate") -> TransitionCandidate:
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
        metadata={"source": "proposal_package_api"},
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


async def seed_domain_and_fired_commitment(store: SQLiteStore) -> None:
    await store.commit_batch(
        CommitBatch(
            batch_id="batch:domain-initial",
            tenant_id=T,
            workflow_id=W,
            tx_group_id=G,
            candidates=[],
        ),
        [
            domain_record(
                rid="rid:domain-initial",
                version=1,
                state_before="none",
                state_after="stale",
            )
        ],
    )

    await register_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment=commitment(),
        rid="rid:api-register",
        batch_id="batch:api-register",
    )

    await fire_active_commitment(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        commitment_id="c1",
        rid="rid:api-fire",
        batch_id="batch:api-fire",
    )


def test_proposal_package_api_creates_inert_package_and_reference():
    pkg = create_recovery_proposal_package(
        package_id="pkg:c1:api-repair:1",
        commitment_id="c1",
        proposal_ref="proposal:api-repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[domain_candidate()],
        rationale="Repair stale dependent entity.",
        validator_context={"source": "api"},
        created_from_record_id="rid:api-fire",
        created_by="test_api",
    )

    validate_recovery_proposal_package(
        package=pkg,
        dependency_scope={"entity_id": DOMAIN_EID},
    )

    ref = package_to_reference(pkg)

    assert pkg.is_inert
    assert pkg.candidate_rids == ["rid:domain-repair-candidate"]
    assert ref["package_id"] == "pkg:c1:api-repair:1"
    assert ref["candidate_rids"] == ["rid:domain-repair-candidate"]
    assert "proposed_domain_candidates" not in ref


def test_proposal_package_api_round_trips_package_dict():
    pkg = create_recovery_proposal_package(
        package_id="pkg:c1:api-repair:1",
        commitment_id="c1",
        proposal_ref="proposal:api-repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[domain_candidate()],
        rationale="Repair stale dependent entity.",
    )

    restored = package_from_dict(package_to_dict(pkg))

    assert restored.package_id == pkg.package_id
    assert restored.proposal_ref == pkg.proposal_ref
    assert restored.candidate_rids == ["rid:domain-repair-candidate"]


def test_proposal_package_api_makes_commitment_fsm_candidate_only():
    pkg = create_recovery_proposal_package(
        package_id="pkg:c1:api-repair:1",
        commitment_id="c1",
        proposal_ref="proposal:api-repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[domain_candidate()],
    )

    candidate = make_package_backed_proposal_candidate(
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        package=pkg,
        commitment=commitment(),
        rid="rid:package-backed-proposal",
    )

    event = event_from_extension(candidate.extension)
    ref = package_reference_from_event_payload(event.payload)

    assert candidate.fsm == "mnemosyne.commitment"
    assert candidate.action_type == "commitment_proposal_emitted"
    assert ref is not None
    assert ref["candidate_rids"] == ["rid:domain-repair-candidate"]


@pytest.mark.asyncio
async def test_proposal_package_api_emits_package_backed_proposal_without_domain_mutation():
    store = SQLiteStore()
    await seed_domain_and_fired_commitment(store)

    pkg = create_recovery_proposal_package(
        package_id="pkg:c1:api-repair:1",
        commitment_id="c1",
        proposal_ref="proposal:api-repair:1",
        proposal_scope={"entity_id": DOMAIN_EID},
        proposed_domain_candidates=[domain_candidate()],
        rationale="Repair stale dependent entity.",
        created_from_record_id="rid:api-fire",
    )

    result = await emit_package_backed_proposal(
        store=store,
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        package=pkg,
        commitment=commitment(),
        rid="rid:package-backed-proposal",
        batch_id="batch:package-backed-proposal",
    )

    assert result.ok
    assert result.committed_only_commitment_fsm
    assert result.committed_action_types == ["commitment_proposal_emitted"]

    status = await get_active_commitment_status(
        store=store,
        tenant_id=T,
        workflow_id=W,
        commitment_id="c1",
    )
    assert status == CommitmentStatus.PROPOSED

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)
    assert domain_view.state == "stale"
    assert domain_view.version == 1

    assert await store.get_record(T, "rid:domain-repair-candidate") is None
