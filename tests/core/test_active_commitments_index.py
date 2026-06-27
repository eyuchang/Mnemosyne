from __future__ import annotations

from datetime import datetime, timezone

from mnemosyne.core.commitments import (
    ActiveCommitment,
    ActiveCommitmentIndex,
    CommitmentStatus,
    make_discharge_commitment_candidate,
    make_fire_commitment_candidate,
    make_register_commitment_candidate,
)
from mnemosyne.core.models import CTLRecord, TransitionCandidate

T = "tenant:commitment-index"
W = "workflow:commitment-index"
G = "tx:commitment-index"
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


def ordinary_record() -> CTLRecord:
    return CTLRecord(
        rid="rid:ordinary",
        op_id="rid:ordinary",
        tenant_id=T,
        tx_group_id=G,
        workflow_id=W,
        binding_id=None,
        eid="domain:entity:1",
        fsm="domain.fsm",
        version=1,
        state_before="none",
        state_after="done",
        action_type="ordinary",
        triggers=[],
        dependencies=[],
        metadata={},
        extension={"kind": "ordinary"},
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


def test_index_reconstructs_live_commitment_from_ctl_records():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
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

    index = ActiveCommitmentIndex.from_ctl_records([
        ordinary_record(),
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
    ])

    assert index.status("c1") == CommitmentStatus.FIRED
    assert index.is_live("c1")
    assert index.live_commitment_ids() == ["c1"]
    assert index.get("c1") == commitment


def test_index_excludes_discharged_commitment_from_live_set():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
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
    discharge = make_discharge_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment_id="c1",
        workflow_id=W,
        rid="rid:discharge",
    )

    index = ActiveCommitmentIndex.from_ctl_records([
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
        record_from_candidate(discharge, version=3),
    ])

    assert index.status("c1") == CommitmentStatus.DISCHARGED
    assert not index.is_live("c1")
    assert index.live_commitment_ids() == []


def test_index_can_filter_commitments_by_type():
    c1 = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Dependency guard.",
    )
    c2 = ActiveCommitment(
        commitment_id="c2",
        commitment_type="temporary_watch",
        description="Temporary watch.",
    )

    r1 = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c1,
        workflow_id=W,
        rid="rid:register:c1",
    )
    r2 = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=c2,
        workflow_id=W,
        rid="rid:register:c2",
    )

    index = ActiveCommitmentIndex.from_ctl_records([
        record_from_candidate(r1, version=1),
        record_from_candidate(r2, version=1),
    ])

    assert list(index.commitments_by_type("dependency_guard").keys()) == ["c1"]
    assert list(index.live_commitments_by_type("temporary_watch").keys()) == ["c2"]


def test_index_is_restart_replay_deterministic():
    commitment = ActiveCommitment(
        commitment_id="c1",
        commitment_type="dependency_guard",
        description="Repair scoped dependent entity.",
    )

    register = make_register_commitment_candidate(
        tenant_id=T,
        tx_group_id=G,
        commitment=commitment,
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

    records = [
        record_from_candidate(register, version=1),
        record_from_candidate(fire, version=2),
    ]

    before_restart = ActiveCommitmentIndex.from_ctl_records(records)
    after_restart = ActiveCommitmentIndex.from_ctl_records(records)

    assert before_restart.live_commitment_ids() == after_restart.live_commitment_ids()
    assert before_restart.status("c1") == after_restart.status("c1")
    assert before_restart.get("c1") == after_restart.get("c1")


def test_index_ignores_non_commitment_ctl_records():
    index = ActiveCommitmentIndex.from_ctl_records([ordinary_record()])

    assert index.live_commitment_ids() == []
    assert index.status("missing") is None
    assert index.get("missing") is None
