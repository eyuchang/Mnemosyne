from datetime import datetime, timezone

from mnemosyne.compensation import reverse_topological_compensation_order
from mnemosyne.core.models import CTLRecord


def rec(rid, deps):
    return CTLRecord(
        rid=rid,
        tenant_id="t",
        tx_group_id="g",
        eid=f"e:{rid}",
        fsm="F",
        version=1,
        state_before="a",
        state_after="b",
        action_type="x",
        workflow_id="wf",
        binding_id=None,
        triggers=[],
        dependencies=deps,
        metadata={},
        extension={},
        app_id="app",
        app_version="1",
        schema_id="s",
        schema_version="1",
        fsm_version="1",
        timestamp=datetime.now(timezone.utc),
    )


def test_reverse_topological_order():
    order = reverse_topological_compensation_order([rec("a", []), rec("b", ["a"]), rec("c", ["b"])])
    assert [r.rid for r in order] == ["c", "b", "a"]
