from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Dict, Iterable


@dataclass
class ServiceMetrics:
    """Tiny Prometheus-compatible metrics registry.

    R8 goal: make deployment behavior observable without adding a dependency.
    """

    counters: Dict[str, int] = field(default_factory=dict)
    latency_ms: Dict[str, list[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, name: str, by: int = 1) -> None:
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + by

    def observe_ms(self, name: str, value_ms: float) -> None:
        with self._lock:
            self.latency_ms.setdefault(name, []).append(float(value_ms))

    def time_ms(self, name: str):
        return _MetricTimer(self, name)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name in sorted(self.counters):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {self.counters[name]}")

            for name in sorted(self.latency_ms):
                values = list(self.latency_ms[name])
                if not values:
                    continue
                values.sort()
                count = len(values)
                total = sum(values)
                p50 = _percentile(values, 0.50)
                p95 = _percentile(values, 0.95)
                lines.append(f"# TYPE {name}_count gauge")
                lines.append(f"{name}_count {count}")
                lines.append(f"# TYPE {name}_sum gauge")
                lines.append(f"{name}_sum {total:.6f}")
                lines.append(f"# TYPE {name}_p50 gauge")
                lines.append(f"{name}_p50 {p50:.6f}")
                lines.append(f"# TYPE {name}_p95 gauge")
                lines.append(f"{name}_p95 {p95:.6f}")

        return "\n".join(lines) + "\n"


class _MetricTimer:
    def __init__(self, metrics: ServiceMetrics, name: str) -> None:
        self.metrics = metrics
        self.name = name
        self.start = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (time.perf_counter() - self.start) * 1000.0
        self.metrics.observe_ms(self.name, elapsed_ms)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1.0 - frac) + values[hi] * frac
