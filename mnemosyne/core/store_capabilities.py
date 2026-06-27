from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STORE_SCHEMA_ID = "mnemosyne.store.sqlite"
STORE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class StoreCapabilityReport:
    store_type: str
    schema_id: str
    schema_version: str
    durable_recovery_events: bool
    idempotent_recovery_events: bool
    deterministic_recovery_replay_order: bool
    supports_restart_persistence: bool
    supports_postgres_conformance_target: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


def store_capability_report_to_dict(report: StoreCapabilityReport) -> dict[str, Any]:
    return {
        "store_type": report.store_type,
        "schema_id": report.schema_id,
        "schema_version": report.schema_version,
        "durable_recovery_events": report.durable_recovery_events,
        "idempotent_recovery_events": report.idempotent_recovery_events,
        "deterministic_recovery_replay_order": report.deterministic_recovery_replay_order,
        "supports_restart_persistence": report.supports_restart_persistence,
        "supports_postgres_conformance_target": report.supports_postgres_conformance_target,
        "notes": list(report.notes),
    }
