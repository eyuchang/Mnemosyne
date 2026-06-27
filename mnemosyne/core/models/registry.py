from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SchemaDef:
    schema_id: str
    schema_version: str
    schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyDef:
    policy_id: str
    policy_version: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SolverProfile:
    profile_id: str
    solver_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeStatus:
    workflow_id: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowHandle:
    workflow_id: str
    run_id: str
    status: str = "submitted"
