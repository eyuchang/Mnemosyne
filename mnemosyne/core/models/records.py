from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CommandStatus(str, Enum):
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PROCESSED = "processed"


class InboxStatus(str, Enum):
    RECEIVED = "received"
    DEDUPED = "deduped"
    BUFFERED = "buffered"
    PROCESSED = "processed"
    REJECTED = "rejected"
    DEAD_LETTERED = "dead_lettered"


class OutboxStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    COMPENSATED = "compensated"
    SUPERSEDED = "superseded"


class ValidationCode(str, Enum):
    OK = "OK"
    UNKNOWN_FSM = "UNKNOWN_FSM"
    STATE_MISMATCH = "STATE_MISMATCH"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    DEPENDENCY_NOT_EFFECTIVE = "DEPENDENCY_NOT_EFFECTIVE"
    TRIGGER_MISSING = "TRIGGER_MISSING"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    CONSTRAINT_FAILED = "CONSTRAINT_FAILED"
    DUPLICATE_IDEMPOTENCY_KEY = "DUPLICATE_IDEMPOTENCY_KEY"


@dataclass(frozen=True)
class Command:
    command_id: str
    tenant_id: str
    actor_id: str
    command_type: str
    payload: dict[str, Any]
    idempotency_key: str
    workflow_id: str | None = None
    submitted_at: datetime = field(default_factory=now_utc)


@dataclass(frozen=True)
class ExternalEvent:
    event_id: str
    tenant_id: str
    event_type: str
    entity_refs: dict[str, str]
    payload: dict[str, Any]
    source: str = "system"
    dedupe_key: str | None = None
    workflow_id: str | None = None
    binding_id: str | None = None
    schema_id: str = "core.external_event"
    schema_version: str = "1.0"
    timestamp: datetime = field(default_factory=now_utc)


@dataclass(frozen=True)
class TransitionCandidate:
    rid: str
    tenant_id: str
    tx_group_id: str
    eid: str
    fsm: str
    state_before: str
    state_after: str
    action_type: str = "transition"
    workflow_id: str | None = None
    binding_id: str | None = None
    triggers: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    extension: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    app_id: str = "core"
    app_version: str = "1.0"
    schema_id: str = "core.transition"
    schema_version: str = "1.0"
    fsm_version: str = "1.0"
    policy_id: str | None = None
    policy_version: str | None = None
    validator_id: str | None = None
    validator_version: str | None = None
    op_id: str | None = None


@dataclass(frozen=True)
class OutboxIntent:
    outbox_id: str
    tenant_id: str
    provider: str
    effect_type: str
    payload: dict[str, Any]
    provider_idempotency_key: str
    workflow_id: str | None = None
    binding_id: str | None = None
    created_at: datetime = field(default_factory=now_utc)


@dataclass(frozen=True)
class CommitBatch:
    batch_id: str
    tenant_id: str
    workflow_id: str | None
    tx_group_id: str
    candidates: list[TransitionCandidate]
    expected_versions: dict[tuple[str, str], int] = field(default_factory=dict)
    outbox_intents: list[OutboxIntent] = field(default_factory=list)
    command_id: str | None = None


@dataclass(frozen=True)
class CTLRecord:
    rid: str
    tenant_id: str
    tx_group_id: str
    eid: str
    fsm: str
    version: int
    state_before: str
    state_after: str
    action_type: str
    workflow_id: str | None
    binding_id: str | None
    triggers: list[str]
    dependencies: list[str]
    metadata: dict[str, Any]
    extension: dict[str, Any]
    app_id: str
    app_version: str
    schema_id: str
    schema_version: str
    fsm_version: str
    timestamp: datetime
    op_id: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    validator_id: str | None = None
    validator_version: str | None = None
    log_position: int | None = None
    local_log_position: int | None = None


@dataclass(frozen=True)
class StateView:
    tenant_id: str
    eid: str
    fsm: str
    state: str | None
    version: int
    attrs: dict[str, Any]
    effective_records: list[str]
    as_of_log_position: int | None = None
    workflow_id: str | None = None
    binding_id: str | None = None


@dataclass(frozen=True)
class ConstraintResult:
    ok: bool
    code: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def pass_() -> "ConstraintResult":
        return ConstraintResult(ok=True)

    @staticmethod
    def fail(code: str, evidence: dict[str, Any] | None = None) -> "ConstraintResult":
        return ConstraintResult(ok=False, code=code, evidence=evidence or {})


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[ConstraintResult] = field(default_factory=list)
    validator_id: str = "core.validator"
    validator_version: str = "1.0"

    @staticmethod
    def pass_() -> "ValidationResult":
        return ValidationResult(ok=True)

    @staticmethod
    def fail(errors: list[ConstraintResult]) -> "ValidationResult":
        return ValidationResult(ok=False, errors=errors)
