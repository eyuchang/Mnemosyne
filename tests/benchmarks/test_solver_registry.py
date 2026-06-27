from __future__ import annotations

import pytest

from mnemosyne.benchmarks.p1_campus_tour_solver import P1CampusTourSolverAdapter
from mnemosyne.benchmarks.external_json_solver import ExternalJsonSolver
from mnemosyne.benchmarks.solver_registry import (
    SolverRegistry,
    default_solver_registry,
)


def test_solver_registry_registers_and_creates_solver():
    registry = SolverRegistry()

    registry.register(
        name="p1-bruteforce",
        description="test solver",
        factory=P1CampusTourSolverAdapter,
    )

    assert registry.names() == ["p1-bruteforce"]

    solver = registry.create("p1-bruteforce")

    assert isinstance(solver, P1CampusTourSolverAdapter)


def test_solver_registry_rejects_duplicate_names():
    registry = SolverRegistry()

    registry.register(
        name="p1-bruteforce",
        description="test solver",
        factory=P1CampusTourSolverAdapter,
    )

    with pytest.raises(ValueError):
        registry.register(
            name="p1-bruteforce",
            description="duplicate",
            factory=P1CampusTourSolverAdapter,
        )


def test_solver_registry_rejects_unknown_solver():
    registry = SolverRegistry()

    with pytest.raises(KeyError):
        registry.create("missing")


def test_default_solver_registry_contains_expected_solvers():
    registry = default_solver_registry()

    assert registry.names() == ["p1-bruteforce", "p1-external-json"]

    assert isinstance(
        registry.create("p1-bruteforce"),
        P1CampusTourSolverAdapter,
    )
    assert isinstance(
        registry.create("p1-external-json"),
        ExternalJsonSolver,
    )
