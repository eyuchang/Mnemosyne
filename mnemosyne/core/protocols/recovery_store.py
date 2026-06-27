from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


RECOVERY_READ_METHODS = (
    "get_record",
    "get_entity_history",
    "get_full_entity_history",
    "get_state_view",
    "get_by_op_id",
)

RECOVERY_WRITE_METHODS = (
    "commit_batch",
)

RECOVERY_STORE_REQUIRED_METHODS = RECOVERY_READ_METHODS + RECOVERY_WRITE_METHODS


@runtime_checkable
class RecoveryReadStore(Protocol):
    """Read surface required by recovery audit, lineage, and unresolved-state APIs.

    R7 keeps this protocol narrower than the full Store protocol so recovery
    code can be hardened and tested against a durable-store boundary before
    introducing PostgreSQL or production runtime execution.
    """

    async def get_record(self, tenant_id: str, rid: str) -> Any | None:
        """Return one committed transition record by tenant/rid."""
        ...

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[Any]:
        """Return effective committed history for an entity/FSM."""
        ...

    async def get_full_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[Any]:
        """Return all committed history, including superseded or admitted rows."""
        ...

    async def get_state_view(self, tenant_id: str, eid: str, fsm: str) -> Any:
        """Return the current materialized StateView for an entity/FSM."""
        ...

    async def get_by_op_id(self, tenant_id: str, op_id: str) -> Any | None:
        """Return a committed record by tenant-scoped idempotency key."""
        ...


@runtime_checkable
class RecoveryWriteStore(RecoveryReadStore, Protocol):
    """Write surface required by validated recovery admission/finalization APIs."""

    async def commit_batch(self, batch: Any, records: list[Any]) -> list[Any]:
        """Atomically commit recovery-related CTL records."""
        ...


@runtime_checkable
class RecoveryStore(RecoveryWriteStore, Protocol):
    """Complete R7 recovery store protocol surface.

    This is the durability boundary that SQLiteStore already satisfies locally
    and that PostgresRecoveryStore should satisfy later in R7.
    """
