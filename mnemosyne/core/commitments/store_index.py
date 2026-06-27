from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from mnemosyne.core.commitments.candidates import COMMITMENT_FSM
from mnemosyne.core.commitments.index import ActiveCommitmentIndex
from mnemosyne.core.models import CTLRecord


def _loads(value: str | None) -> Any:
    return json.loads(value) if value else None


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def ctl_record_from_sqlite_row(row) -> CTLRecord:
    return CTLRecord(
        rid=row["rid"],
        op_id=row["op_id"],
        tenant_id=row["tenant_id"],
        tx_group_id=row["tx_group_id"],
        workflow_id=row["workflow_id"],
        binding_id=row["binding_id"],
        eid=row["eid"],
        fsm=row["fsm"],
        version=row["version"],
        state_before=row["state_before"],
        state_after=row["state_after"],
        action_type=row["action_type"],
        triggers=_loads(row["triggers"]) or [],
        dependencies=_loads(row["dependencies"]) or [],
        metadata=_loads(row["metadata"]) or {},
        extension=_loads(row["extension"]) or {},
        app_id=row["app_id"],
        app_version=row["app_version"],
        schema_id=row["schema_id"],
        schema_version=row["schema_version"],
        fsm_version=row["fsm_version"],
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        validator_id=row["validator_id"],
        validator_version=row["validator_version"],
        timestamp=_parse_dt(row["timestamp"]),
        log_position=row["log_position"],
        local_log_position=row["local_log_position"],
    )


async def active_commitment_index_from_store(
    store,
    *,
    tenant_id: str,
    workflow_id: str | None = None,
) -> ActiveCommitmentIndex:
    """Build replay-derived active commitment index from committed CTL records.

    The returned index is not authoritative. It is reconstructed from CTL.
    """

    params: list[Any] = [tenant_id, COMMITMENT_FSM]
    where = "tenant_id = ? AND fsm = ?"

    if workflow_id is not None:
        where += " AND workflow_id = ?"
        params.append(workflow_id)

    rows = store.conn.execute(
        f"""
        SELECT *
        FROM ctl_records
        WHERE {where}
        ORDER BY log_position ASC
        """,
        params,
    ).fetchall()

    records = [ctl_record_from_sqlite_row(row) for row in rows]
    return ActiveCommitmentIndex.from_ctl_records(records)
