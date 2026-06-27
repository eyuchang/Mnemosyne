# File: mnemosyne/runtime/temporal/dependency.py
#
# Purpose:
#   Keep Temporal SDK dependency handling isolated inside
#   mnemosyne/runtime/temporal/.
#
# Why:
#   temporalio is an optional dependency. Core, store, CTL, StateView,
#   compensation, and app code must not import it directly.
#
# Contract:
#   - is_temporal_sdk_available() checks whether temporalio is installed.
#   - require_temporal_sdk() raises a clear error if temporalio is missing.

from __future__ import annotations

import importlib.util


TEMPORAL_EXTRA_INSTALL_HINT = 'Install Temporal support with: python -m pip install -e ".[temporal]"'


def is_temporal_sdk_available() -> bool:
    return importlib.util.find_spec("temporalio") is not None


def require_temporal_sdk() -> None:
    if not is_temporal_sdk_available():
        raise RuntimeError(
            "Temporal SDK is not installed. "
            "TemporalRuntimeDriver requires the optional 'temporal' extra. "
            f"{TEMPORAL_EXTRA_INSTALL_HINT}"
        )