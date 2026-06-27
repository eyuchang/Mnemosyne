from __future__ import annotations

from mnemosyne.core.models import CTLRecord, StateView


def fold_attrs(attrs: dict, record: CTLRecord) -> dict:
    updated = dict(attrs)
    extension = record.extension or {}
    if "attrs_after" in extension and isinstance(extension["attrs_after"], dict):
        updated.update(extension["attrs_after"])
    if "attrs" in extension and isinstance(extension["attrs"], dict):
        updated.update(extension["attrs"])
    return updated


def replay_state_view(tenant_id: str, eid: str, fsm: str, records: list[CTLRecord]) -> StateView:
    state: str | None = None
    version = 0
    attrs: dict = {}
    effective_records: list[str] = []
    as_of: int | None = None
    workflow_id: str | None = None
    binding_id: str | None = None
    for record in sorted(records, key=lambda r: (r.version, r.log_position or 0)):
        if state is not None and record.state_before != state:
            raise ValueError(
                f"Replay mismatch for {eid}/{fsm}: record {record.rid} starts at "
                f"{record.state_before}, expected {state}"
            )
        if state is None:
            # First transition must start at the entity initial state; validator enforces that.
            pass
        state = record.state_after
        version = record.version
        attrs = fold_attrs(attrs, record)
        effective_records.append(record.rid)
        as_of = record.log_position or as_of
        workflow_id = record.workflow_id or workflow_id
        binding_id = record.binding_id or binding_id
    return StateView(
        tenant_id=tenant_id,
        eid=eid,
        fsm=fsm,
        state=state,
        version=version,
        attrs=attrs,
        effective_records=effective_records,
        as_of_log_position=as_of,
        workflow_id=workflow_id,
        binding_id=binding_id,
    )
