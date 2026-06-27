# File: mnemosyne/runtime/command_handler.py
#
# Purpose:
#   R3.6 command handler for the local runtime session.
#
# Design rule:
#   The handler routes command-shaped runtime intent into LocalRuntimeSession.
#   It does not commit records and does not bypass the kernel.

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from mnemosyne.runtime.commands import (
    AcceptProposalCommand,
    BindAgentCommand,
    BindWorkflowCommand,
    CreateAgentCommand,
    CreateWorkflowCommand,
    ListTraceEventsCommand,
    QueryWorkflowStatusCommand,
    RejectProposalCommand,
    RuntimeCommand,
    RuntimeCommandResult,
    SubmitProposalCommand,
)
from mnemosyne.runtime.session import LocalRuntimeSession


def _command_type(command: object) -> str:
    return command.__class__.__name__


def _json_value(value: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
    if value is None:
        return None

    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)

    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, list):
        return [
            asdict(item) if is_dataclass(item) and not isinstance(item, type) else dict(item)
            for item in value
        ]

    raise TypeError(f"cannot convert command value to json value: {type(value)!r}")


class RuntimeCommandHandler:
    def __init__(self, session: LocalRuntimeSession | None = None) -> None:
        self.session = session or LocalRuntimeSession()

    def handle(self, command: RuntimeCommand) -> RuntimeCommandResult:
        command_type = _command_type(command)

        try:
            if isinstance(command, CreateWorkflowCommand):
                value = self.session.create_workflow(command.spec)

            elif isinstance(command, BindWorkflowCommand):
                value = self.session.bind_workflow(command.binding)

            elif isinstance(command, CreateAgentCommand):
                value = self.session.create_agent(command.spec)

            elif isinstance(command, BindAgentCommand):
                value = self.session.bind_agent(command.binding)

            elif isinstance(command, SubmitProposalCommand):
                value = self.session.submit_proposal(command.envelope)

            elif isinstance(command, AcceptProposalCommand):
                value = self.session.accept_proposal(
                    proposal_id=command.proposal_id,
                    reason=command.reason,
                    committed_rids=command.committed_rids,
                    decision_id=command.decision_id,
                    audit_ref=command.audit_ref,
                    metadata=command.metadata,
                )

            elif isinstance(command, RejectProposalCommand):
                value = self.session.reject_proposal(
                    proposal_id=command.proposal_id,
                    reason=command.reason,
                    error_codes=command.error_codes,
                    decision_id=command.decision_id,
                    audit_ref=command.audit_ref,
                    metadata=command.metadata,
                )

            elif isinstance(command, QueryWorkflowStatusCommand):
                value = self.session.runtime_status(command.workflow_id)

            elif isinstance(command, ListTraceEventsCommand):
                events = self.session.list_trace_events()
                if command.workflow_id is not None:
                    events = [
                        event
                        for event in events
                        if event.workflow_id == command.workflow_id
                    ]
                value = events

            else:
                return RuntimeCommandResult.fail(
                    command_type=command_type,
                    error_code="UNKNOWN_COMMAND",
                    error_message=f"unknown runtime command: {command_type}",
                )

            return RuntimeCommandResult.pass_(
                command_type=command_type,
                value=_json_value(value),
            )

        except Exception as exc:
            return RuntimeCommandResult.fail(
                command_type=command_type,
                error_code="COMMAND_FAILED",
                error_message=str(exc),
            )
