# File: mnemosyne/runtime/models.py
#
# Purpose:
#   R3 runtime vocabulary models.
#
# Design rule:
#   Runtime objects describe workflow/agent/proposal/admission state.
#   They do not commit records and do not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _tuple_of_str(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _copy_dict(value: JsonDict | None) -> JsonDict:
    if value is None:
        return {}
    return dict(value)


@dataclass(frozen=True)
class WorkflowSpec:
    """User- or system-created workflow definition.

    A WorkflowSpec describes the intended workflow surface.
    It does not create committed state by itself.
    """

    workflow_id: str
    tenant_id: str
    app_id: str
    schema_id: str
    fsm: str
    workflow_type: str = "generic"
    created_by: str = "system"
    app_version: str = "1.0"
    schema_version: str = "1.0"
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.app_id, "app_id")
        _require_nonempty(self.schema_id, "schema_id")
        _require_nonempty(self.fsm, "fsm")
        _require_nonempty(self.workflow_type, "workflow_type")
        _require_nonempty(self.created_by, "created_by")
        object.__setattr__(self, "metadata", _copy_dict(self.metadata))


@dataclass(frozen=True)
class WorkflowBinding:
    """Binding between a workflow definition and an entity instance."""

    binding_id: str
    workflow_id: str
    tenant_id: str
    entity_id: str
    fsm: str
    initial_state: str
    created_by: str = "system"
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.binding_id, "binding_id")
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.entity_id, "entity_id")
        _require_nonempty(self.fsm, "fsm")
        _require_nonempty(self.initial_state, "initial_state")
        _require_nonempty(self.created_by, "created_by")
        object.__setattr__(self, "metadata", _copy_dict(self.metadata))


@dataclass(frozen=True)
class AgentSpec:
    """Runtime identity for an agent that may propose actions."""

    agent_id: str
    tenant_id: str
    agent_type: str
    display_name: str
    created_by: str = "system"
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    model_id: str | None = None
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.agent_id, "agent_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.agent_type, "agent_type")
        _require_nonempty(self.display_name, "display_name")
        _require_nonempty(self.created_by, "created_by")
        object.__setattr__(self, "capabilities", _tuple_of_str(self.capabilities))
        object.__setattr__(self, "metadata", _copy_dict(self.metadata))


@dataclass(frozen=True)
class AgentBinding:
    """Binding between an agent and a workflow/entity scope."""

    agent_binding_id: str
    agent_id: str
    workflow_id: str
    tenant_id: str
    binding_id: str
    entity_id: str
    role: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.agent_binding_id, "agent_binding_id")
        _require_nonempty(self.agent_id, "agent_id")
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.binding_id, "binding_id")
        _require_nonempty(self.entity_id, "entity_id")
        _require_nonempty(self.role, "role")
        object.__setattr__(self, "permissions", _tuple_of_str(self.permissions))
        object.__setattr__(self, "metadata", _copy_dict(self.metadata))


@dataclass(frozen=True)
class RuntimeProposalEnvelope:
    """Envelope for an agent/tool/solver proposal before admission.

    This is the R3 counterpart of the R2 solver proposal boundary.
    The envelope is not truth and does not imply commit.
    """

    proposal_id: str
    tenant_id: str
    workflow_id: str
    binding_id: str
    entity_id: str
    agent_id: str
    app_id: str
    schema_id: str
    proposal_kind: str
    payload: JsonDict
    assumptions: tuple[JsonDict, ...] = field(default_factory=tuple)
    provenance: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.proposal_id, "proposal_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.binding_id, "binding_id")
        _require_nonempty(self.entity_id, "entity_id")
        _require_nonempty(self.agent_id, "agent_id")
        _require_nonempty(self.app_id, "app_id")
        _require_nonempty(self.schema_id, "schema_id")
        _require_nonempty(self.proposal_kind, "proposal_kind")
        object.__setattr__(self, "payload", _copy_dict(self.payload))
        object.__setattr__(
            self,
            "assumptions",
            tuple(_copy_dict(item) for item in self.assumptions),
        )
        object.__setattr__(self, "provenance", _copy_dict(self.provenance))


@dataclass(frozen=True)
class RuntimeAdmissionDecision:
    """Result of runtime admission for a proposal."""

    decision_id: str
    proposal_id: str
    tenant_id: str
    workflow_id: str
    accepted: bool
    reason: str
    error_codes: tuple[str, ...] = field(default_factory=tuple)
    committed_rids: tuple[str, ...] = field(default_factory=tuple)
    audit_ref: str | None = None
    metadata: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.decision_id, "decision_id")
        _require_nonempty(self.proposal_id, "proposal_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.reason, "reason")
        object.__setattr__(self, "error_codes", _tuple_of_str(self.error_codes))
        object.__setattr__(self, "committed_rids", _tuple_of_str(self.committed_rids))
        object.__setattr__(self, "metadata", _copy_dict(self.metadata))


@dataclass(frozen=True)
class RuntimeTraceEvent:
    """Trace event emitted by the runtime substrate."""

    event_id: str
    tenant_id: str
    workflow_id: str
    event_type: str
    actor_id: str
    proposal_id: str | None = None
    decision_id: str | None = None
    details: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.event_id, "event_id")
        _require_nonempty(self.tenant_id, "tenant_id")
        _require_nonempty(self.workflow_id, "workflow_id")
        _require_nonempty(self.event_type, "event_type")
        _require_nonempty(self.actor_id, "actor_id")
        object.__setattr__(self, "details", _copy_dict(self.details))
