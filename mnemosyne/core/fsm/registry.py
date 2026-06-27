from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FSMEdge:
    state_before: str
    state_after: str
    action_type: str
    inducing_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class FSMDef:
    fsm_id: str
    fsm_version: str
    initial_state: str
    edges: tuple[FSMEdge, ...]


class FSMRegistry:
    def __init__(self) -> None:
        self._fsms: dict[str, FSMDef] = {}

    def register(self, fsm: FSMDef) -> None:
        key = self.key(fsm.fsm_id, fsm.fsm_version)
        if key in self._fsms:
            raise ValueError(f"FSM already registered: {key}")
        self._fsms[key] = fsm

    def has_fsm(self, fsm_id: str, fsm_version: str = "1.0") -> bool:
        return self.key(fsm_id, fsm_version) in self._fsms

    def initial_state(self, fsm_id: str, fsm_version: str = "1.0") -> str | None:
        fsm = self._fsms.get(self.key(fsm_id, fsm_version))
        return fsm.initial_state if fsm else None

    def legal(
        self,
        fsm_id: str,
        state_before: str,
        state_after: str,
        action_type: str,
        fsm_version: str = "1.0",
    ) -> bool:
        fsm = self._fsms.get(self.key(fsm_id, fsm_version))
        if not fsm:
            return False
        edge = FSMEdge(state_before, state_after, action_type)
        return any(
            e.state_before == edge.state_before
            and e.state_after == edge.state_after
            and e.action_type == edge.action_type
            for e in fsm.edges
        )

    def all(self) -> list[FSMDef]:
        return list(self._fsms.values())

    @staticmethod
    def key(fsm_id: str, fsm_version: str) -> str:
        return f"{fsm_id}@{fsm_version}"
