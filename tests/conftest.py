# File: tests/conftest.py
#
# Purpose:
#   Shared test fixtures plus optional marker policy.
#
# Policy:
#   The default public test suite stays fast, deterministic, and local.
#   Optional test groups remain visible in the repository but are skipped by
#   default unless explicitly selected with pytest -m.

from __future__ import annotations

import pytest

from mnemosyne.apps import AppRegistry
from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.apps.rideshare import RideshareApp
from mnemosyne.apps.travel import TravelApp
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore


OPTIONAL_MARKERS = {
    "integration",
    "long_horizon",
    "research",
    "external",
    "temporal",
    "realm",
}

@pytest.fixture
def app_registry():
    reg = AppRegistry()
    reg.register(RideshareApp())
    reg.register(TravelApp())
    reg.register(JSSPApp())
    return reg


@pytest.fixture
def store():
    return SQLiteStore()


@pytest.fixture
def validator(app_registry):
    return Validator(app_registry.build_fsm_registry(), app_registry.build_constraint_registry())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    mark_expression = config.option.markexpr

    if mark_expression:
        return

    skip_optional = pytest.mark.skip(
        reason=(
            "optional test group skipped by default; "
            "run explicitly with python -m pytest -q -m <marker>"
        )
    )

    for item in items:
        for marker_name in OPTIONAL_MARKERS:
            if item.get_closest_marker(marker_name) is not None:
                item.add_marker(skip_optional)
                break