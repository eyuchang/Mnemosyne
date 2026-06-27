# File: mnemosyne/benchmarks/results.py
#
# Purpose:
#   Result models and serialization helpers for local benchmark runs.
#
# Stage:
#   Stage 1.6R-P1A-Verified extends results with oracle/trace details.
#
# Rule:
#   Benchmark results report what Mnemosyne observed and verified.
#   They do not become domain truth.

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from mnemosyne.benchmarks.models import BenchmarkMetrics


@dataclass(frozen=True)
class BenchmarkRunResult:
    case_id: str
    ok: bool
    committed_rids: list[str]
    metrics: BenchmarkMetrics | None = None
    error_codes: list[str] = field(default_factory=list)
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def benchmark_result_to_dict(result: BenchmarkRunResult) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "ok": result.ok,
        "committed_rids": list(result.committed_rids),
        "metrics": asdict(result.metrics) if result.metrics is not None else None,
        "error_codes": list(result.error_codes),
        "error_message": result.error_message,
        "details": dict(result.details),
    }


def benchmark_result_to_jsonl(result: BenchmarkRunResult) -> str:
    return json.dumps(benchmark_result_to_dict(result), sort_keys=True)