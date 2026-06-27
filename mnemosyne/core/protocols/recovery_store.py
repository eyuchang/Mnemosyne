from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable


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

RECOVERY_EVENT_METHODS = (
    "append_recovery_event",
    "list_recovery_events",
)

RECOVERY_STORE_REQUIRED_METHODS = (
    RECOVERY_READ_METHODS + RECOVERY_WRITE_METHODS + RECOVERY_EVENT_METHODS
)

T = TypeVar("T")


class RecoveryStoreCapabilityError(TypeError):
    """Raised when an object does not satisfy the recovery store boundary."""


@runtime_checkable
class RecoveryReadStore(Protocol):
    """Read surface required by recovery audit, lineage, and unresolved-state APIs."""

    async def get_record(self, tenant_id: str, rid: str) -> Any | None:
        ...

    async def get_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[Any]:
        ...

    async def get_full_entity_history(self, tenant_id: str, eid: str, fsm: str) -> list[Any]:
        ...

    async def get_state_view(self, tenant_id: str, eid: str, fsm: str) -> Any:
        ...

    async def get_by_op_id(self, tenant_id: str, op_id: str) -> Any | None:
        ...


@runtime_checkable
class RecoveryWriteStore(RecoveryReadStore, Protocol):
    """Write surface required by validated recovery admission/finalization APIs."""

    async def commit_batch(self, batch: Any, records: list[Any]) -> list[Any]:
        ...


@runtime_checkable
class RecoveryEventStore(Protocol):
    """Durable append-only recovery event-log surface."""

    async def append_recovery_event(self, event: Any) -> Any:
        ...

    async def list_recovery_events(
        self,
        tenant_id: str,
        *,
        workflow_id: str | None = None,
        recovery_id: str | None = None,
        event_type: str | None = None,
    ) -> list[Any]:
        ...


@runtime_checkable
class RecoveryStore(RecoveryWriteStore, RecoveryEventStore, Protocol):
    """Complete R7 recovery store protocol surface."""


def missing_recovery_store_methods(
    store: object,
    required_methods: tuple[str, ...] = RECOVERY_STORE_REQUIRED_METHODS,
) -> tuple[str, ...]:
    return tuple(
        method
        for method in required_methods
        if not callable(getattr(store, method, None))
    )


def require_recovery_store(
    store: T,
    *,
    required_methods: tuple[str, ...] = RECOVERY_STORE_REQUIRED_METHODS,
) -> T:
    missing = missing_recovery_store_methods(store, required_methods)
    if missing:
        raise RecoveryStoreCapabilityError(
            "store does not satisfy RecoveryStore capability boundary; "
            f"missing methods: {', '.join(missing)}"
        )

    return store
