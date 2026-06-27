from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mnemosyne.core.commitments import (
    ActiveCommitment,
    CommitmentEventType,
    CommitmentStatus,
    COMMITMENT_FSM,
    active_commitment_index_from_store,
    commitment_entity_id,
    event_from_extension,
)
from mnemosyne.core.commitments.store_index import ctl_record_from_sqlite_row
from mnemosyne.core.models import CTLRecord
from mnemosyne.core.recovery import proposal_package_reference_from_event_payload


UNRESOLVED_COMMITMENT_STATUSES = {
    CommitmentStatus.LIVE.value,
    CommitmentStatus.FIRED.value,
    CommitmentStatus.PROPOSED.value,
    CommitmentStatus.REJECTED.value,
}

RECOVERY_ACTION_TYPES = {
    CommitmentEventType.PROPOSAL_EMITTED.value,
    CommitmentEventType.ADMITTED.value,
    CommitmentEventType.REJECTED.value,
}


@dataclass(frozen=True)
class ActiveCommitmentAuditRow:
    commitment_id: str
    commitment_type: str
    status: str
    is_unresolved: bool
    description: str
    dependency_scope: dict[str, Any]
    workflow_id: str | None
    record_count: int
    first_record_id: str | None
    last_record_id: str | None
    last_action_type: str | None
    last_log_position: int | None


@dataclass(frozen=True)
class CommitmentLineageRow:
    commitment_id: str
    record_id: str
    action_type: str
    status_before: str
    status_after: str
    payload: dict[str, Any] = field(default_factory=dict)
    workflow_id: str | None = None
    tx_group_id: str | None = None
    log_position: int | None = None
    local_log_position: int | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class RecoveryLineageRow:
    commitment_id: str
    record_id: str
    action_type: str
    status_before: str
    status_after: str
    proposal_ref: str | None = None
    package_id: str | None = None
    admitted_record_ids: list[str] = field(default_factory=list)
    rejection_code: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    workflow_id: str | None = None
    tx_group_id: str | None = None
    log_position: int | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class UnresolvedCommitmentReport:
    tenant_id: str
    workflow_id: str | None
    rows: list[ActiveCommitmentAuditRow]

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def commitment_ids(self) -> list[str]:
        return [row.commitment_id for row in self.rows]


def _status_value(status: CommitmentStatus | str | None) -> str:
    if isinstance(status, CommitmentStatus):
        return status.value
    if isinstance(status, str):
        return status
    return "unknown"


def _commitment_id_from_record(record: CTLRecord) -> str:
    event = event_from_extension(record.extension)
    if event is not None:
        return event.commitment_id

    value = record.metadata.get("commitment_id")
    if isinstance(value, str):
        return value

    prefix = "commitment:"
    if record.eid.startswith(prefix):
        return record.eid[len(prefix):]

    return record.eid


def _payload_from_record(record: CTLRecord) -> dict[str, Any]:
    event = event_from_extension(record.extension)
    if event is not None:
        return dict(event.payload)
    return {}


def _package_reference_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    ref = proposal_package_reference_from_event_payload(payload)
    if ref:
        return ref

    value = payload.get("proposal_package")
    if isinstance(value, dict):
        return value

    return None


def _proposal_ref_from_payload(payload: dict[str, Any]) -> str | None:
    value = payload.get("proposal_ref")
    if isinstance(value, str):
        return value

    ref = _package_reference_from_payload(payload)
    if ref and isinstance(ref.get("proposal_ref"), str):
        return ref["proposal_ref"]

    return None


def _package_id_from_payload(payload: dict[str, Any]) -> str | None:
    ref = _package_reference_from_payload(payload)
    if ref and isinstance(ref.get("package_id"), str):
        return ref["package_id"]
    return None


def _admitted_record_ids_from_payload(payload: dict[str, Any]) -> list[str]:
    value = payload.get("admitted_record_ids")
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _rejection_code_from_payload(payload: dict[str, Any]) -> str | None:
    value = payload.get("rejection_code")
    if isinstance(value, str):
        return value

    value = payload.get("code")
    if isinstance(value, str):
        return value

    return None


def _commitment_records_from_store(
    store: Any,
    *,
    tenant_id: str,
    workflow_id: str | None = None,
    commitment_id: str | None = None,
) -> list[CTLRecord]:
    """Read commitment-FSM CTL records from the local store.

    This is read-only. It does not validate, commit, mutate CTL, or execute
    recovery.
    """

    params: list[Any] = [tenant_id, COMMITMENT_FSM]
    where = "tenant_id = ? AND fsm = ?"

    if workflow_id is not None:
        where += " AND workflow_id = ?"
        params.append(workflow_id)

    if commitment_id is not None:
        where += " AND eid = ?"
        params.append(commitment_entity_id(commitment_id))

    rows = store.conn.execute(
        f"""
        SELECT *
        FROM ctl_records
        WHERE {where}
        ORDER BY log_position ASC
        """,
        params,
    ).fetchall()

    return [ctl_record_from_sqlite_row(row) for row in rows]


def _records_by_commitment(records: list[CTLRecord]) -> dict[str, list[CTLRecord]]:
    grouped: dict[str, list[CTLRecord]] = {}
    for record in records:
        grouped.setdefault(_commitment_id_from_record(record), []).append(record)
    return grouped


def _audit_row_from_commitment(
    *,
    commitment: ActiveCommitment,
    status: CommitmentStatus | str | None,
    records: list[CTLRecord],
) -> ActiveCommitmentAuditRow:
    status_value = _status_value(status)
    first = records[0] if records else None
    last = records[-1] if records else None

    return ActiveCommitmentAuditRow(
        commitment_id=commitment.commitment_id,
        commitment_type=commitment.commitment_type,
        status=status_value,
        is_unresolved=status_value in UNRESOLVED_COMMITMENT_STATUSES,
        description=commitment.description,
        dependency_scope=dict(commitment.dependency_scope),
        workflow_id=last.workflow_id if last else None,
        record_count=len(records),
        first_record_id=first.rid if first else None,
        last_record_id=last.rid if last else None,
        last_action_type=last.action_type if last else None,
        last_log_position=last.log_position if last else None,
    )


async def audit_active_commitments(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
) -> list[ActiveCommitmentAuditRow]:
    """Return read-only audit rows for known active commitments."""

    index = await active_commitment_index_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    records = _commitment_records_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    grouped = _records_by_commitment(records)

    rows: list[ActiveCommitmentAuditRow] = []
    for commitment_id in sorted(index.projection.commitments.keys()):
        commitment = index.get(commitment_id)
        if commitment is None:
            continue

        rows.append(
            _audit_row_from_commitment(
                commitment=commitment,
                status=index.status(commitment_id),
                records=grouped.get(commitment_id, []),
            )
        )

    return rows


async def list_unresolved_commitments(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
) -> UnresolvedCommitmentReport:
    """Return unresolved active commitments.

    Unresolved means the commitment remains live in the replay-derived
    commitment projection: live, fired, proposed, or rejected.
    """

    rows = await audit_active_commitments(
        store=store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )

    return UnresolvedCommitmentReport(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        rows=[row for row in rows if row.is_unresolved],
    )


async def audit_commitment_lineage(
    *,
    store: Any,
    tenant_id: str,
    commitment_id: str,
    workflow_id: str | None = None,
) -> list[CommitmentLineageRow]:
    """Return the CTL lineage for one commitment."""

    records = _commitment_records_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        commitment_id=commitment_id,
    )

    return [
        CommitmentLineageRow(
            commitment_id=_commitment_id_from_record(record),
            record_id=record.rid,
            action_type=record.action_type,
            status_before=record.state_before,
            status_after=record.state_after,
            payload=_payload_from_record(record),
            workflow_id=record.workflow_id,
            tx_group_id=record.tx_group_id,
            log_position=record.log_position,
            local_log_position=record.local_log_position,
            timestamp=record.timestamp,
        )
        for record in records
    ]


async def audit_recovery_lineage(
    *,
    store: Any,
    tenant_id: str,
    workflow_id: str | None = None,
    commitment_id: str | None = None,
) -> list[RecoveryLineageRow]:
    """Return read-only lineage rows for recovery-related commitment events."""

    records = _commitment_records_from_store(
        store,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        commitment_id=commitment_id,
    )

    rows: list[RecoveryLineageRow] = []
    for record in records:
        if record.action_type not in RECOVERY_ACTION_TYPES:
            continue

        payload = _payload_from_record(record)

        rows.append(
            RecoveryLineageRow(
                commitment_id=_commitment_id_from_record(record),
                record_id=record.rid,
                action_type=record.action_type,
                status_before=record.state_before,
                status_after=record.state_after,
                proposal_ref=_proposal_ref_from_payload(payload),
                package_id=_package_id_from_payload(payload),
                admitted_record_ids=_admitted_record_ids_from_payload(payload),
                rejection_code=_rejection_code_from_payload(payload),
                payload=payload,
                workflow_id=record.workflow_id,
                tx_group_id=record.tx_group_id,
                log_position=record.log_position,
                timestamp=record.timestamp,
            )
        )

    return rows
