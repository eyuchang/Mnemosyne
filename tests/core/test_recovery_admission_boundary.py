from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.commitments import (
    ActiveCommitment,
    COMMITMENT_FSM,
    CommitmentEventType,
    CommitmentStatus,
    commitment_entity_id,
    extract_commitment_events_from_ctl_records,
    make_commitment_admitted_candidate,
    make_commitment_rejected_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
    replay_commitments,
)
from mnemosyne.core.models import CommitBatch, CTLRecord, TransitionCandidate
from mnemosyne.core.recovery import RecoveryContext, RecoveryProposal, orchestrate_recovery
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:recovery-boundary"
W = "workflow:recovery-boundary"
G = "tx:recovery-boundary"
DOMAIN_EID = "domain:entity:1"
DOMAIN_FSM = "domain.fsm"
FT = datetime(2026, 6, 26, tzinfo=timezone.utc)


def record_from_candidate(candidate: TransitionCandidate, *, version: int) -> CTLRecord:
    return CTLRecord(
        rid=candidate.rid,
        op_id=candidate.op_id or candidate.rid,
        tenant_id=candidate.tenant_id,
        tx_group_id=candidate.tx_group_id,
        workflow_id=candidate.workflow_id,
        binding_id=candidate.binding_id,
        eid=candidate.eid,
        fsm=candidate.fsm,
        version=version,
        state_before=candidate.state_before,
        state_after=candidate.state_after,
        action_type=candidate.action_type,
        triggers=list(candidate.triggers),
        dependencies=list(candidate.dependencies),
        metadata=dict(candidate.metadata),
        extension=dict(candidate.extension),
        app_id=candidate.app_id,
        app_version=candidate.app_version,
        schema_id=candidate.schema_id,
        schema_version=candidate.schema_version,
        fsm_version=candidate.fsm_version,
        policy_id=candidate.policy_id,
        policy_version=candidate.policy_version,
        validator_id=candidate.validator_id,
        validator_version=candidate.validator_version,
        timestamp=FT,
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
        action_type="domain_repair",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "domain_repair"},
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


def batch(batch_id: str, candidates: list[TransitionCandidate]) -> CommitBatch:
    return CommitBatch(
        batch_id=batch_id,
        tenant_id=T,
        workflow_id=W,
        tx_group_id=G,
        candidates=candidates,
    )


def commitment() -> ActiveCommitment:
    return ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
        dependency_scope={"entity_id": DOMAIN_EID},
    )


@pytest.mark.asyncio
async def test_recovery_proposal_does_not_mutate_domain_state():
    store = SQLiteStore()
    c = commitment()

    initial_domain = domain_record(
        rid="rid:domain-initial",
        version=1,
        state_before="none",
        state_after="stale",
    )
    await store.commit_batch(batch("batch:domain-initial", []), [initial_domain])

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    proposal = orchestrate_recovery(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        ),
        workflow_id=W,
        rid="rid:proposal",
    ).candidate

    await store.commit_batch(
        batch("batch:commitment-proposal", [register, fire, proposal]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(proposal, version=3),
        ],
    )

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]

    commitment_history = await store.get_full_entity_history(
        T,
        commitment_entity_id("c1"),
        COMMITMENT_FSM,
    )
    projection = replay_commitments(extract_commitment_events_from_ctl_records(commitment_history))

    assert projection.status("c1") == CommitmentStatus.PROPOSED


@pytest.mark.asyncio
async def test_domain_state_changes_only_when_domain_repair_record_is_committed():
    store = SQLiteStore()
    c = commitment()

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
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    proposal = orchestrate_recovery(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        ),
        workflow_id=W,
        rid="rid:proposal",
    ).candidate

    admitted_domain = domain_record(
        rid="rid:domain-repair",
        version=2,
        state_before="stale",
        state_after="repaired",
    )

    admitted = make_commitment_admitted_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        admitted_record_ids=["rid:domain-repair"],
        workflow_id=W,
        rid="rid:commitment-admitted",
    )

    await store.commit_batch(
        batch("batch:recovery-admitted", [register, fire, proposal, admitted]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(proposal, version=3),
            admitted_domain,
            record_from_candidate(admitted, version=4),
        ],
    )

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    assert domain_view.state == "repaired"
    assert domain_view.version == 2
    assert domain_view.effective_records == [
        "rid:domain-initial",
        "rid:domain-repair",
    ]

    commitment_history = await store.get_full_entity_history(
        T,
        commitment_entity_id("c1"),
        COMMITMENT_FSM,
    )
    events = extract_commitment_events_from_ctl_records(commitment_history)
    projection = replay_commitments(events)

    assert [event.event_type for event in events] == [
        CommitmentEventType.REGISTERED,
        CommitmentEventType.FIRED,
        CommitmentEventType.PROPOSAL_EMITTED,
        CommitmentEventType.ADMITTED,
    ]
    assert projection.status("c1") == CommitmentStatus.ADMITTED
    assert "c1" not in projection.live_commitments()


@pytest.mark.asyncio
async def test_rejected_recovery_leaves_domain_state_unchanged():
    store = SQLiteStore()
    c = commitment()

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
        commitment=c,
        workflow_id=W,
        rid="rid:register",
    )
    fire = make_fire_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:fire",
    )
    proposal = orchestrate_recovery(
        tenant_id=T,
        tx_group_id=G,
        commitment=c,
        context=RecoveryContext(commitment_id="c1", depth=0, attempt_index=0),
        proposal=RecoveryProposal(
            proposal_ref="proposal:repair:1",
            proposal_scope={"entity_id": DOMAIN_EID},
        ),
        workflow_id=W,
        rid="rid:proposal",
    ).candidate
    rejected = make_commitment_rejected_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        rejection_code="CONSTRAINT_FAILED",
        rejection_evidence={"reason": "repair_invalid"},
        workflow_id=W,
        rid="rid:commitment-rejected",
        state_before=CommitmentStatus.PROPOSED.value,
    )

    await store.commit_batch(
        batch("batch:recovery-rejected", [register, fire, proposal, rejected]),
        [
            record_from_candidate(register, version=1),
            record_from_candidate(fire, version=2),
            record_from_candidate(proposal, version=3),
            record_from_candidate(rejected, version=4),
        ],
    )

    domain_view = await store.get_state_view(T, DOMAIN_EID, DOMAIN_FSM)

    assert domain_view.state == "stale"
    assert domain_view.version == 1
    assert domain_view.effective_records == ["rid:domain-initial"]

    commitment_history = await store.get_full_entity_history(
        T,
        commitment_entity_id("c1"),
        COMMITMENT_FSM,
    )
    projection = replay_commitments(extract_commitment_events_from_ctl_records(commitment_history))

    assert projection.status("c1") == CommitmentStatus.REJECTED
    assert "c1" in projection.live_commitments()
