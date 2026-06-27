# File: mnemosyne/benchmarks/models.py
#
# Purpose:
#   Shared benchmark adapter models.
#
# Rule:
#   Benchmark cases provide scenarios. They do not own domain truth.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkStep:
    step_id: str
    state_before: str
    state_after: str
    action_type: str
    attrs_after: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    compensates: list[str] = field(default_factory=list)
    emit_outbox: bool = False
    outbox_provider: str = "benchmark"
    outbox_effect_type: str = "benchmark_effect"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    tenant_id: str
    workflow_id: str
    entity_id: str
    binding_id: str
    fsm: str
    app_id: str
    schema_id: str
    steps: list[BenchmarkStep]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkMetrics:
    case_id: str
    tenant_id: str
    workflow_id: str
    entity_id: str
    total_records: int
    effective_records: int
    ineffective_records: int
    outbox_rows: int
    final_state: str | None
    state_version: int