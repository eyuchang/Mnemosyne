from __future__ import annotations

from mnemosyne.core.commitments.models import CommitmentEventType, CommitmentStatus
from mnemosyne.core.fsm import FSMDef, FSMEdge, FSMRegistry

COMMITMENT_FSM_VERSION = "1.0"


def commitment_fsm_def() -> FSMDef:
    return FSMDef(
        fsm_id="mnemosyne.commitment",
        fsm_version=COMMITMENT_FSM_VERSION,
        initial_state="none",
        edges=(
            FSMEdge("none", CommitmentStatus.LIVE.value, CommitmentEventType.REGISTERED.value),
            FSMEdge(CommitmentStatus.LIVE.value, CommitmentStatus.FIRED.value, CommitmentEventType.FIRED.value),
            FSMEdge(CommitmentStatus.FIRED.value, CommitmentStatus.PROPOSED.value, CommitmentEventType.PROPOSAL_EMITTED.value),
            FSMEdge(CommitmentStatus.REJECTED.value, CommitmentStatus.PROPOSED.value, CommitmentEventType.PROPOSAL_EMITTED.value),
            FSMEdge(CommitmentStatus.FIRED.value, CommitmentStatus.REJECTED.value, CommitmentEventType.REJECTED.value),
            FSMEdge(CommitmentStatus.PROPOSED.value, CommitmentStatus.REJECTED.value, CommitmentEventType.REJECTED.value),
            FSMEdge(CommitmentStatus.PROPOSED.value, CommitmentStatus.ADMITTED.value, CommitmentEventType.ADMITTED.value),
            FSMEdge(CommitmentStatus.FIRED.value, CommitmentStatus.DISCHARGED.value, CommitmentEventType.DISCHARGED.value),
            FSMEdge(CommitmentStatus.PROPOSED.value, CommitmentStatus.DISCHARGED.value, CommitmentEventType.DISCHARGED.value),
            FSMEdge(CommitmentStatus.REJECTED.value, CommitmentStatus.DISCHARGED.value, CommitmentEventType.DISCHARGED.value),
            FSMEdge(CommitmentStatus.LIVE.value, CommitmentStatus.EXPIRED.value, CommitmentEventType.EXPIRED.value),
            FSMEdge(CommitmentStatus.FIRED.value, CommitmentStatus.EXPIRED.value, CommitmentEventType.EXPIRED.value),
            FSMEdge(CommitmentStatus.PROPOSED.value, CommitmentStatus.EXPIRED.value, CommitmentEventType.EXPIRED.value),
            FSMEdge(CommitmentStatus.REJECTED.value, CommitmentStatus.EXPIRED.value, CommitmentEventType.EXPIRED.value),
        ),
    )


def register_commitment_fsm(registry: FSMRegistry) -> FSMRegistry:
    registry.register(commitment_fsm_def())
    return registry


def build_commitment_fsm_registry() -> FSMRegistry:
    registry = FSMRegistry()
    register_commitment_fsm(registry)
    return registry
