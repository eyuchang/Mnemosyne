from __future__ import annotations

from collections import defaultdict, deque

from mnemosyne.core.models import CTLRecord


def reverse_topological_compensation_order(records: list[CTLRecord]) -> list[CTLRecord]:
    """Return records in reverse topological order over dependency edges within the group."""
    by_rid = {r.rid: r for r in records}
    outgoing: dict[str, set[str]] = defaultdict(set)
    indeg: dict[str, int] = {r.rid: 0 for r in records}
    for r in records:
        for dep in r.dependencies:
            if dep in by_rid:
                outgoing[dep].add(r.rid)
                indeg[r.rid] += 1
    q = deque([rid for rid, d in indeg.items() if d == 0])
    topo: list[str] = []
    while q:
        rid = q.popleft()
        topo.append(rid)
        for nxt in outgoing[rid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)
    if len(topo) != len(records):
        raise ValueError("cycle in compensation dependency graph")
    return [by_rid[rid] for rid in reversed(topo)]
