from __future__ import annotations

from uuid import uuid4

from mnemosyne.core.commitments.ctl import event_to_extension
from mnemosyne.core.commitments.models import (
    ActiveCommitment,
    CommitmentEvent,
    CommitmentEventType,
    CommitmentStatus,
)
from mnemosyne.core.models import TransitionCandidate

COMMITMENT_FSM = "mnemosyne.commitment"
COMMITMENT_APP_ID = "mnemosyne"
COMMITMENT_SCHEMA_ID = "mnemosyne.active_commitment_event"
COMMITMENT_SCHEMA_VERSION = "1.0"


def commitment_entity_id(commitment_id: str) -> str:
    return f"commitment:{commitment_id}"


def _rid(prefix: str, commitment_id: str) -> str:
    return f"{prefix}:{commitment_id}:{uuid4().hex}"


def make_register_commitment_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment: ActiveCommitment,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-register", commitment.commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.REGISTERED,
        commitment_id=commitment.commitment_id,
        payload={"commitment": commitment},
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment.commitment_id),
        fsm=COMMITMENT_FSM,
        state_before="none",
        state_after=CommitmentStatus.LIVE.value,
        action_type=CommitmentEventType.REGISTERED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[],
        dependencies=[],
        extension=event_to_extension(event),
        metadata={"commitment_id": commitment.commitment_id},
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )


def make_fire_commitment_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    reason: str = "trigger_true",
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-fire", commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.FIRED,
        commitment_id=commitment_id,
        payload={"reason": reason},
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment_id),
        fsm=COMMITMENT_FSM,
        state_before=CommitmentStatus.LIVE.value,
        state_after=CommitmentStatus.FIRED.value,
        action_type=CommitmentEventType.FIRED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[dependency_rid] if dependency_rid else [],
        dependencies=[dependency_rid] if dependency_rid else [],
        extension=event_to_extension(event),
        metadata={"commitment_id": commitment_id},
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )


def make_discharge_commitment_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    reason: str = "obligation_satisfied",
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-discharge", commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.DISCHARGED,
        commitment_id=commitment_id,
        payload={"reason": reason},
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment_id),
        fsm=COMMITMENT_FSM,
        state_before=CommitmentStatus.FIRED.value,
        state_after=CommitmentStatus.DISCHARGED.value,
        action_type=CommitmentEventType.DISCHARGED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[dependency_rid] if dependency_rid else [],
        dependencies=[dependency_rid] if dependency_rid else [],
        extension=event_to_extension(event),
        metadata={"commitment_id": commitment_id},
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )

def make_commitment_proposal_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    proposal_ref: str,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    proposal_scope: dict | None = None,
    state_before: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-proposal", commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.PROPOSAL_EMITTED,
        commitment_id=commitment_id,
        payload={
            "proposal_ref": proposal_ref,
            "proposal_scope": proposal_scope or {},
        },
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment_id),
        fsm=COMMITMENT_FSM,
        state_before=state_before or CommitmentStatus.FIRED.value,
        state_after=CommitmentStatus.PROPOSED.value,
        action_type=CommitmentEventType.PROPOSAL_EMITTED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[dependency_rid] if dependency_rid else [],
        dependencies=[dependency_rid] if dependency_rid else [],
        extension=event_to_extension(event),
        metadata={
            "commitment_id": commitment_id,
            "proposal_ref": proposal_ref,
        },
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )


def make_commitment_admitted_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    admitted_record_ids: list[str],
    workflow_id: str | None = None,
    binding_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-admitted", commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.ADMITTED,
        commitment_id=commitment_id,
        payload={"admitted_record_ids": admitted_record_ids},
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment_id),
        fsm=COMMITMENT_FSM,
        state_before=CommitmentStatus.PROPOSED.value,
        state_after=CommitmentStatus.ADMITTED.value,
        action_type=CommitmentEventType.ADMITTED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[dependency_rid] if dependency_rid else [],
        dependencies=[dependency_rid] if dependency_rid else [],
        extension=event_to_extension(event),
        metadata={
            "commitment_id": commitment_id,
            "admitted_record_ids": admitted_record_ids,
        },
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )


def make_commitment_rejected_candidate(
    *,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    rejection_code: str,
    rejection_evidence: dict | None = None,
    state_before: str | None = None,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> TransitionCandidate:
    final_rid = rid or _rid("acr-rejected", commitment_id)

    event = CommitmentEvent(
        event_type=CommitmentEventType.REJECTED,
        commitment_id=commitment_id,
        payload={
            "rejection_code": rejection_code,
            "rejection_evidence": rejection_evidence or {},
        },
        record_id=final_rid,
        workflow_id=workflow_id,
    )

    return TransitionCandidate(
        rid=final_rid,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        eid=commitment_entity_id(commitment_id),
        fsm=COMMITMENT_FSM,
        state_before=state_before or CommitmentStatus.PROPOSED.value,
        state_after=CommitmentStatus.REJECTED.value,
        action_type=CommitmentEventType.REJECTED.value,
        workflow_id=workflow_id,
        binding_id=binding_id,
        triggers=[dependency_rid] if dependency_rid else [],
        dependencies=[dependency_rid] if dependency_rid else [],
        extension=event_to_extension(event),
        metadata={
            "commitment_id": commitment_id,
            "rejection_code": rejection_code,
        },
        app_id=COMMITMENT_APP_ID,
        app_version="1.0",
        schema_id=COMMITMENT_SCHEMA_ID,
        schema_version=COMMITMENT_SCHEMA_VERSION,
        fsm_version="1.0",
        op_id=op_id,
    )