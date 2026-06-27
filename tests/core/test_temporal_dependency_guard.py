# File: tests/core/test_temporal_dependency_guard.py
#
# Purpose:
#   Verify that Temporal remains an optional dependency.
#
# Why:
#   The standard test suite must stay local and fast. Installing or importing
#   mnemosyne.runtime.temporal should not require a Temporal server or even the
#   temporalio package.
#
# This test supports both environments:
#   - temporalio not installed
#   - temporalio installed through .[temporal]

import pytest

from mnemosyne.runtime.temporal import (
    TEMPORAL_EXTRA_INSTALL_HINT,
    is_temporal_sdk_available,
    require_temporal_sdk,
)


def test_temporal_sdk_availability_returns_boolean():
    assert isinstance(is_temporal_sdk_available(), bool)


def test_temporal_install_hint_mentions_optional_extra():
    assert ".[temporal]" in TEMPORAL_EXTRA_INSTALL_HINT
    assert "python -m pip install" in TEMPORAL_EXTRA_INSTALL_HINT


def test_require_temporal_sdk_is_clean_when_available_or_helpful_when_missing():
    if is_temporal_sdk_available():
        assert require_temporal_sdk() is None
    else:
        with pytest.raises(RuntimeError, match="Temporal SDK is not installed"):
            require_temporal_sdk()