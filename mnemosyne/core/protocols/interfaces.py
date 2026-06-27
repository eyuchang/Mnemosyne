from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mnemosyne.core.fsm import FSMDef
from mnemosyne.core.models import (
    CTLRecord,
    Command,
    CommitBatch,
    ConstraintResult,
    ExternalEvent,
    OutboxIntent,
    PolicyDef,
    RuntimeStatus,
    SchemaDef,
    SolverProfile,
    StateView,
    TransitionCandidate,
    ValidationResult,
    WorkflowHandle,
)


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------
#
# Store is the durable persistence boundary for Mnemosyne/ALAS.
#
# Architectural role:
#
#   - CTL is the source of truth for committed state.
#   - Event log is the source of truth for observed causes and non-commit
#     decisions.
#   - Inbox dedupes external inbound events.
#   - Outbox durably records external side-effect intents.
#   - StateView exposes the current effective state to runtime/planner code.
#
# Why this protocol matters:
#
#   SQLiteStore is the current local/test implementation.
#   PostgresStore will later be the production implementation.
#
#   Both must satisfy this same Store contract.
#
# runtime_checkable:
#
#   The @runtime_checkable decorator allows tests to check:
#
#       isinstance(SQLiteStore(), Store)
#
#   This does not fully type-check method signatures at runtime, but it catches
#   missing methods early and gives us a useful contract test.
# ---------------------------------------------------------------------------


@runtime_checkable
class Store(Protocol):
    """Durable persistence API for commands, events, CTL, projections, and effects."""

    # -----------------------------------------------------------------------
    # Command log
    # -----------------------------------------------------------------------
    #
    # Commands represent instructions from humans, APIs, CLIs, or runtimes.
    # The store should enforce tenant-scoped idempotency by command
    # idempotency_key.
    # -----------------------------------------------------------------------

    async def append_command(self, command: Command) -> Command:
        """Append or dedupe a command by tenant-scoped idempotency key."""
        ...

    # -----------------------------------------------------------------------
    # Event log
    # -----------------------------------------------------------------------
    #
    # Event log records observed causes. These may come from providers,
    # runtimes, operators, or external systems.
    # -----------------------------------------------------------------------

    async def append_event(self, event: ExternalEvent) -> ExternalEvent:
        """Append or dedupe an observed external event by tenant/event id."""
        ...

    async def has_event(self, tenant_id: str, event_id: str) -> bool:
        """Return whether an event has already been recorded for a tenant."""
        ...

    # -----------------------------------------------------------------------
    # Event inbox
    # -----------------------------------------------------------------------
    #
    # Inbox is distinct from event_log.
    #
    # Inbox role:
    #   - receive external events;
    #   - dedupe retries by tenant/source/dedupe_key;
    #   - track processing status.
    #
    # Event log role:
    #   - record observed causes as durable memory.
    #
    # A later worker may move/process inbox events into transition candidates,
    # CTL commits, or event_log entries depending on the application.
    # -----------------------------------------------------------------------

    async def record_inbox_event(self, event: ExternalEvent) -> ExternalEvent:
        """Record an inbound external event once, deduped by tenant/source/dedupe_key."""
        ...

    # -----------------------------------------------------------------------
    # CTL effectiveness and StateView read APIs
    # -----------------------------------------------------------------------
    #
    # CTL stores append-only committed transition records.
    #
    # effective_record_index distinguishes:
    #   - historical records that remain effective;
    #   - historical records later compensated or superseded.
    #
    # StateView exposes the current operational state reconstructed/materialized
    # from effective CTL records.
    # -----------------------------------------------------------------------

    async def is_effective(self, tenant_id: str, rid: str) -> bool:
        """Return whether a CTL record currently remains effective."""
        ...

    async def get_state_view(self, tenant_id: str, eid: str, fsm: str) -> StateView:
        """Return the current effective StateView for an entity/FSM."""
        ...

    async def get_latest_version(self, tenant_id: str, eid: str, fsm: str) -> int:
        """Return the latest committed version for an entity/FSM."""
        ...

    async def get_record(self, tenant_id: str, rid: str) -> CTLRecord | None:
        """Return a CTL record by tenant/rid, or None if it does not exist."""
        ...

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[CTLRecord]:
        """Return effective CTL history for an entity/FSM in version order."""
        ...

    async def get_full_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[CTLRecord]:
        """Return ALL CTL records for an entity/FSM, including compensated/superseded ones."""
        ...

    async def get_by_op_id(self, tenant_id: str, op_id: str) -> CTLRecord | None:
        """Return a committed record by tenant-scoped op_id (idempotency key), or None."""
        ...

    async def get_effective_dependents(self, tenant_id: str, rid: str) -> list[CTLRecord]:
        """Return effective records whose dependencies include rid."""
        ...

    # -----------------------------------------------------------------------
    # CTL commit API
    # -----------------------------------------------------------------------
    #
    # commit_batch is the atomic write boundary.
    #
    # It should commit together:
    #   - CTL records;
    #   - effective-record updates;
    #   - entity projection updates;
    #   - outbox intents.
    #
    # If any part fails, the store must roll back all writes in the batch.
    # -----------------------------------------------------------------------

    async def commit_batch(self, batch: CommitBatch, records: list[CTLRecord]) -> list[CTLRecord]:
        """Atomically commit CTL records and associated outbox intents."""
        ...

    # -----------------------------------------------------------------------
    # Outbox API
    # -----------------------------------------------------------------------
    #
    # Outbox records external side-effect intents.
    #
    # The store should not directly call external systems. Instead, it writes
    # durable intents. Later workers/provider adapters execute those intents.
    # -----------------------------------------------------------------------

    async def enqueue_outbox(self, intents: list[OutboxIntent]) -> None:
        """Insert outbox intents, deduped by tenant/provider/provider_idempotency_key."""
        ...


# ---------------------------------------------------------------------------
# Schema validation protocol
# ---------------------------------------------------------------------------
#
# SchemaValidator validates payloads against app/domain schemas.
# ---------------------------------------------------------------------------


class SchemaValidator(Protocol):
    def validate(
        self,
        schema_id: str,
        schema_version: str,
        payload: dict[str, Any],
    ) -> ValidationResult:
        """Validate a payload against a schema id/version."""
        ...


# ---------------------------------------------------------------------------
# Compensation protocol
# ---------------------------------------------------------------------------
#
# CompensationHandler proposes corrective transitions for already committed
# CTL records.
#
# Important:
#   The handler proposes compensation candidates.
#   The store later commits accepted compensation records into CTL.
# ---------------------------------------------------------------------------


class CompensationHandler(Protocol):
    def can_compensate(self, record: CTLRecord, state: StateView) -> ConstraintResult:
        """Return whether a record can be compensated in the current StateView."""
        ...

    async def propose_compensation(
        self,
        record: CTLRecord,
        state: StateView,
    ) -> list[TransitionCandidate]:
        """Propose compensation transition candidates."""
        ...


# ---------------------------------------------------------------------------
# Event mapping protocol
# ---------------------------------------------------------------------------
#
# EventMapper converts external events into candidate transitions.
# ---------------------------------------------------------------------------


class EventMapper(Protocol):
    def map_event(self, event: ExternalEvent) -> list[TransitionCandidate]:
        """Map an external event into zero or more transition candidates."""
        ...


# ---------------------------------------------------------------------------
# Solver protocol
# ---------------------------------------------------------------------------
#
# Solver is for symbolic, optimization, scheduling, routing, or domain solvers.
# Example later integrations:
#   - OR-Tools
#   - MILP solvers
#   - scheduling solvers
# ---------------------------------------------------------------------------


class Solver(Protocol):
    async def solve(self, problem: dict[str, Any]) -> dict[str, Any]:
        """Solve a structured problem and return a structured result."""
        ...


# ---------------------------------------------------------------------------
# Planner protocol
# ---------------------------------------------------------------------------
#
# Planner is the cognition/planning boundary.
# Later implementations may use LLMs, rules, solvers, or hybrid methods.
# ---------------------------------------------------------------------------


class Planner(Protocol):
    async def plan(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Produce a plan from a structured specification."""
        ...


# ---------------------------------------------------------------------------
# Runtime driver protocol
# ---------------------------------------------------------------------------
#
# RuntimeDriver abstracts orchestration engines.
#
# Current:
#   - deterministic local runtime
#
# Future:
#   - Temporal runtime
#
# Important:
#   Runtime engines are orchestration mechanisms, not domain truth.
#   CTL/store remain the domain source of truth.
# ---------------------------------------------------------------------------


class RuntimeDriver(Protocol):
    async def submit_workflow(self, spec: dict[str, Any]) -> WorkflowHandle:
        """Submit a workflow to the runtime engine."""
        ...

    async def signal_disruption(self, workflow_id: str, event: ExternalEvent) -> None:
        """Signal a disruption or external event into a workflow."""
        ...

    async def query_status(self, workflow_id: str) -> RuntimeStatus:
        """Query runtime-level workflow status."""
        ...


# ---------------------------------------------------------------------------
# Mnemosyne application protocol
# ---------------------------------------------------------------------------
#
# MnemosyneApp is the app/domain plug-in boundary.
#
# Each app contributes:
#   - schemas;
#   - FSMs;
#   - constraints;
#   - policies;
#   - compensation handlers;
#   - event mappers;
#   - solver profiles;
#   - example commit batches.
#
# This is what allows rideshare, travel, JSSP, and future domains to share the
# same CTL/store/runtime core.
# ---------------------------------------------------------------------------


class MnemosyneApp(Protocol):
    app_id: str
    app_version: str

    def schemas(self) -> list[SchemaDef]:
        """Return app-owned schema definitions."""
        ...

    def fsms(self) -> list[FSMDef]:
        """Return app-owned finite-state machine definitions."""
        ...

    def constraints(self) -> list[Any]:
        """Return app-owned constraint definitions or callables."""
        ...

    def policies(self) -> list[PolicyDef]:
        """Return app-owned policy definitions."""
        ...

    def compensation_handlers(self) -> list[CompensationHandler]:
        """Return app-owned compensation handlers."""
        ...

    def event_mappers(self) -> list[EventMapper]:
        """Return app-owned external event mappers."""
        ...

    def solver_profiles(self) -> list[SolverProfile]:
        """Return app-owned solver profile declarations."""
        ...

    def example_commit_batches(self, tenant_id: str) -> list[CommitBatch]:
        """Return example commit batches for tests, demos, and conformance checks."""
        ...