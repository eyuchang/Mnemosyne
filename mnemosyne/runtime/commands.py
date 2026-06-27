# File: mnemosyne/runtime/commands.py
#
# Purpose:
#   R3.6 command-shaped runtime API.
#
# Design rule:
#   Commands describe runtime intent.
#   They do not commit records and do not bypass the kernel.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mnemosyne.runtime.models import (
    AgentBinding,
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CreateWorkflowCommand:
    spec: WorkflowSpec


@dataclass(frozen=True)
class BindWorkflowCommand:
    binding: WorkflowBinding


@dataclass(frozen=True)
class CreateAgentCommand:
    spec: AgentSpec


@dataclass(frozen=True)
class BindAgentCommand:
    binding: AgentBinding


@dataclass(frozen=True)
class SubmitProposalCommand:
    envelope: RuntimeProposalEnvelope


@dataclass(frozen=True)
class AcceptProposalCommand:
    proposal_id: str
    reason: str
    committed_rids: tuple[str, ...]
    decision_id: str | None = None
    audit_ref: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class RejectProposalCommand:
    proposal_id: str
    reason: str
    error_codes: tuple[str, ...]
    decision_id: str | None = None
    audit_ref: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class QueryWorkflowStatusCommand:
    workflow_id: str


@dataclass(frozen=True)
class ListTraceEventsCommand:
    workflow_id: str | None = None


RuntimeCommand = (
    CreateWorkflowCommand
    | BindWorkflowCommand
    | CreateAgentCommand
    | BindAgentCommand
    | SubmitProposalCommand
    | AcceptProposalCommand
    | RejectProposalCommand
    | QueryWorkflowStatusCommand
    | ListTraceEventsCommand
)


@dataclass(frozen=True)
class RuntimeCommandResult:
    ok: bool
    command_type: str
    value: JsonDict | list[JsonDict] | None = None
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def pass_(
        cls,
        *,
        command_type: str,
        value: JsonDict | list[JsonDict] | None = None,
    ) -> "RuntimeCommandResult":
        return cls(
            ok=True,
            command_type=command_type,
            value=value,
            error_code=None,
            error_message=None,
        )

    @classmethod
    def fail(
        cls,
        *,
        command_type: str,
        error_code: str,
        error_message: str,
    ) -> "RuntimeCommandResult":
        return cls(
            ok=False,
            command_type=command_type,
            value=None,
            error_code=error_code,
            error_message=error_message,
        )
