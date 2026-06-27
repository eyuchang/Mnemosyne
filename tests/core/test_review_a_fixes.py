"""Regression tests for the Review Packet A findings (BL-1, BL-2, IM-1/2/5/6).

Each test pins an invariant that the original suite did not cover, because every
original compensation test compensated the sole/first record of an entity.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mnemosyne.core.fsm import FSMDef, FSMEdge, FSMRegistry
from mnemosyne.core.models import CommitBatch, CTLRecord, OutboxIntent, TransitionCandidate
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore

T = "tenant:reviewA"
FT = datetime(2026, 6, 19, tzinfo=timezone.utc)


def fsm_registry() -> FSMRegistry:
    reg = FSMRegistry()
    reg.register(
        FSMDef(
            fsm_id="F",
            fsm_version="1.0",
            initial_state="none",
            edges=(
                FSMEdge("none", "A", "go"),
                FSMEdge("A", "B", "go2"),
                FSMEdge("A", "C", "cancel"),
                FSMEdge("B", "A", "cancelback"),
            ),
        )
    )
    return reg


def cand(rid, eid, sb, sa, action, *, deps=None, compensates=None) -> TransitionCandidate:
    meta = {}
    if compensates:
        meta["compensates"] = compensates
    return TransitionCandidate(
        rid=rid, tenant_id=T, tx_group_id="g", workflow_id="w", binding_id=None,
        eid=eid, fsm="F", state_before=sb, state_after=sa, action_type=action,
        dependencies=deps or [], metadata=meta, app_id="a", schema_id="s",
    )


def batch(bid, candidates, outbox=None) -> CommitBatch:
    return CommitBatch(batch_id=bid, tenant_id=T, workflow_id="w", tx_group_id="g",
                       candidates=candidates, outbox_intents=outbox or [])


async def commit(v: Validator, s: SQLiteStore, b: CommitBatch):
    records = await v.records_from_batch(b, s)
    return await s.commit_batch(b, records)


def raw(rid, eid, v, sb, sa, *, deps=None, compensates=None) -> CTLRecord:
    meta = {}
    if compensates:
        meta["compensates"] = compensates
    return CTLRecord(
        rid=rid, op_id=rid, tenant_id=T, tx_group_id="g", workflow_id="w", binding_id=None,
        eid=eid, fsm="F", version=v, state_before=sb, state_after=sa, action_type="t",
        triggers=[], dependencies=deps or [], metadata=meta, extension={}, app_id="a",
        app_version="1", schema_id="s", schema_version="1", fsm_version="1.0",
        policy_id=None, policy_version=None, validator_id="v", validator_version="1", timestamp=FT,
    )


# --------------------------------------------------------------------------- BL-1
@pytest.mark.asyncio
async def test_bl1_cross_entity_compensation_reprojects_other_entity():
    s = SQLiteStore()
    await s.commit_batch(batch("b1", []), [raw("A1", "entA", 1, "none", "A")])
    await s.commit_batch(batch("b2", []), [raw("B1", "entB", 1, "none", "X", compensates=["A1"])])
    assert not await s.is_effective(T, "A1")
    view = await s.get_state_view(T, "entA", "F")
    assert view.state is None and view.effective_records == []  # not stale "A"


# --------------------------------------------------------------------------- IM-6
@pytest.mark.asyncio
async def test_im6_outbox_only_batch_is_not_dropped():
    s = SQLiteStore()
    intent = OutboxIntent(outbox_id="O1", tenant_id=T, provider="p", effect_type="e",
                          payload={}, provider_idempotency_key="k1", workflow_id="w", binding_id=None)
    await s.commit_batch(batch("b1", [], outbox=[intent]), [])
    n = s.conn.execute("SELECT COUNT(*) FROM outbox WHERE tenant_id=?", (T,)).fetchone()[0]
    assert n == 1


# --------------------------------------------------------------------------- IM-2
@pytest.mark.asyncio
async def test_im2_op_id_idempotent_across_distinct_rids():
    s = SQLiteStore()
    r1 = CTLRecord(**{**raw("R1", "e", 1, "none", "A").__dict__})
    await s.commit_batch(batch("b1", []), [r1])
    # same op_id ("R1") but a different rid -> must be a no-op, not an error or duplicate.
    r2 = raw("R2", "e", 1, "none", "A")
    r2 = CTLRecord(**{**r2.__dict__, "op_id": "R1"})
    await s.commit_batch(batch("b2", []), [r2])
    rows = s.conn.execute("SELECT COUNT(*) FROM ctl_records WHERE tenant_id=?", (T,)).fetchone()[0]
    assert rows == 1


# --------------------------------------------------------------------------- IM-1
@pytest.mark.asyncio
async def test_im1_full_history_includes_compensated_records():
    s = SQLiteStore()
    await s.commit_batch(batch("b1", []), [raw("R1", "e", 1, "none", "A")])
    await s.commit_batch(batch("b2", []), [raw("R2", "e", 2, "A", "C", compensates=["R1"])])
    full = await s.get_full_entity_history(T, "e", "F")
    effective = await s.get_entity_history(T, "e", "F")
    assert [r.rid for r in full] == ["R1", "R2"]      # history preserved
    assert [r.rid for r in effective] == ["R2"]       # effective view excludes compensated


# --------------------------------------------------------------------------- BL-2
@pytest.mark.asyncio
async def test_bl2_validator_rejects_orphaning_compensation():
    s, v = SQLiteStore(), Validator(fsm_registry())
    await commit(v, s, batch("b1", [cand("R1", "entE", "none", "A", "go")]))
    await commit(v, s, batch("b2", [cand("R2", "entF", "none", "A", "go", deps=["R1"])]))
    # Compensate R1 while R2 (different entity) still effectively depends on it.
    result = await v.validate_batch(
        batch("b3", [cand("C1", "entE", "A", "C", "cancel", compensates=["R1"])]), s
    )
    assert not result.ok
    assert "EFFECTIVE_DEPENDENT_ORPHANED" in [e.code for e in result.errors]


# --------------------------------------------------------------------------- IM-5
@pytest.mark.asyncio
async def test_im5_validator_rejects_chain_breaking_compensation():
    s, v = SQLiteStore(), Validator(fsm_registry())
    await commit(v, s, batch("b1", [cand("R1", "entE", "none", "A", "go")]))
    await commit(v, s, batch("b2", [cand("R2", "entE", "A", "B", "go2")]))
    # Compensate R2 with a record whose state_before no longer holds once R2 is removed.
    result = await v.validate_batch(
        batch("b3", [cand("C1", "entE", "B", "A", "cancelback", compensates=["R2"])]), s
    )
    assert not result.ok
    assert "EFFECTIVE_CHAIN_BROKEN" in [e.code for e in result.errors]


# --------------------------------------------------------------------------- target checks
@pytest.mark.asyncio
async def test_compensation_target_must_exist():
    s, v = SQLiteStore(), Validator(fsm_registry())
    await commit(v, s, batch("b1", [cand("R1", "entE", "none", "A", "go")]))
    result = await v.validate_batch(
        batch("b2", [cand("C1", "entE", "A", "C", "cancel", compensates=["ghost"])]), s
    )
    assert not result.ok
    assert "COMPENSATION_TARGET_MISSING" in [e.code for e in result.errors]


# --------------------------------------------------------------- false-positive guard
@pytest.mark.asyncio
async def test_legitimate_tail_collapse_compensation_still_passes():
    s, v = SQLiteStore(), Validator(fsm_registry())
    await commit(v, s, batch("b1", [cand("R1", "entH", "none", "A", "go")]))
    b2 = batch("b2", [cand("C1", "entH", "A", "C", "cancel", compensates=["R1"])])
    result = await v.validate_batch(b2, s)
    assert result.ok, [e.code for e in result.errors]
    await commit(v, s, b2)
    view = await s.get_state_view(T, "entH", "F")
    assert view.state == "C" and view.effective_records == ["C1"]
