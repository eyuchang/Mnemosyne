# File: tests/core/test_temporal_import_isolation.py
#
# Purpose:
#   Enforce the Stage 1 rule that Temporal SDK imports must stay isolated
#   under mnemosyne/runtime/temporal/.
#
# Why:
#   Temporal orchestrates workflows, but it must not become domain truth.
#   Core, store, app, CTL, StateView, and compensation code should not import
#   temporalio directly.

import ast
from pathlib import Path


PROJECT_ROOT = Path("mnemosyne")
ALLOWED_TEMPORAL_IMPORT_PREFIX = Path("mnemosyne/runtime/temporal")


def python_files_under_mnemosyne() -> list[Path]:
    return sorted(PROJECT_ROOT.rglob("*.py"))


def imports_temporalio(path: Path) -> bool:
    tree = ast.parse(path.read_text(), filename=str(path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "temporalio" or alias.name.startswith("temporalio."):
                    return True

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "temporalio" or module.startswith("temporalio."):
                return True

    return False


def is_under_temporal_runtime_package(path: Path) -> bool:
    return path == ALLOWED_TEMPORAL_IMPORT_PREFIX or ALLOWED_TEMPORAL_IMPORT_PREFIX in path.parents


def test_temporalio_imports_are_isolated_to_temporal_runtime_package():
    violations = []

    for path in python_files_under_mnemosyne():
        if imports_temporalio(path) and not is_under_temporal_runtime_package(path):
            violations.append(str(path))

    assert violations == []