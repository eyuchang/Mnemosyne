# File: mnemosyne/benchmarks/solver_registry.py
#
# Purpose:
#   Registry for benchmark solver adapters.
#
# Stage:
#   R2.1 — selectable solver backend.
#
# Design rule:
#   Solver selection is pluggable.
#   Solver output is still only a certified proposal.
#   Mnemosyne remains the commit authority.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mnemosyne.benchmarks.solver import BenchmarkSolver
from mnemosyne.benchmarks.external_json_solver import ExternalJsonSolver


SolverFactory = Callable[[], BenchmarkSolver]


@dataclass(frozen=True)
class SolverRegistryEntry:
    name: str
    description: str
    factory: SolverFactory


class SolverRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, SolverRegistryEntry] = {}

    def register(
        self,
        *,
        name: str,
        description: str,
        factory: SolverFactory,
    ) -> None:
        if not name:
            raise ValueError("solver name must be non-empty")

        if name in self._entries:
            raise ValueError(f"solver already registered: {name}")

        self._entries[name] = SolverRegistryEntry(
            name=name,
            description=description,
            factory=factory,
        )

    def names(self) -> list[str]:
        return sorted(self._entries)

    def entries(self) -> list[SolverRegistryEntry]:
        return [
            self._entries[name]
            for name in self.names()
        ]

    def create(self, name: str) -> BenchmarkSolver:
        try:
            entry = self._entries[name]
        except KeyError as exc:
            available = ", ".join(self.names()) or "<none>"
            raise KeyError(f"unknown solver: {name}; available solvers: {available}") from exc

        return entry.factory()


def default_solver_registry() -> SolverRegistry:
    from mnemosyne.benchmarks.p1_campus_tour_solver import P1CampusTourSolverAdapter

    registry = SolverRegistry()

    registry.register(
        name="p1-bruteforce",
        description="Local deterministic brute-force solver for P1-compatible Campus Tour cases.",
        factory=P1CampusTourSolverAdapter,
    )

    registry.register(
        name="p1-external-json",
        description="External JSON adapter for P1-compatible externally supplied plans.",
        factory=ExternalJsonSolver,
    )

    return registry
