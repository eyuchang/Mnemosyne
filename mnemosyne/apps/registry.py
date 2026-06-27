from __future__ import annotations

from dataclasses import dataclass, field

from mnemosyne.core.fsm import FSMRegistry
from mnemosyne.core.protocols import MnemosyneApp
from mnemosyne.core.validation import ConstraintRegistry


@dataclass
class AppRegistry:
    apps: dict[str, MnemosyneApp] = field(default_factory=dict)

    def register(self, app: MnemosyneApp) -> None:
        key = self.key(app.app_id, app.app_version)
        if key in self.apps:
            raise ValueError(f"App already registered: {key}")
        self.apps[key] = app

    def get(self, app_id: str, app_version: str = "1.0") -> MnemosyneApp:
        return self.apps[self.key(app_id, app_version)]

    def build_fsm_registry(self) -> FSMRegistry:
        registry = FSMRegistry()
        for app in self.apps.values():
            for fsm in app.fsms():
                registry.register(fsm)
        return registry

    def build_constraint_registry(self) -> ConstraintRegistry:
        registry = ConstraintRegistry()
        for app in self.apps.values():
            for constraint in app.constraints():
                registry.register(constraint.fsm, constraint.action_type, constraint.fn)
        return registry

    @staticmethod
    def key(app_id: str, app_version: str) -> str:
        return f"{app_id}@{app_version}"
