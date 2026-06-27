import importlib.util
from pathlib import Path

import pytest

try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:  # pragma: no cover - py<3.11 fallback
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

from mnemosyne.runtime.temporal import TemporalRuntimeDriver

pytestmark = pytest.mark.skipif(tomllib is None, reason="needs tomllib (py>=3.11) or tomli")


def test_temporal_dependency_is_optional_extra_in_pyproject():
    pyproject_path = Path("pyproject.toml")
    data = tomllib.loads(pyproject_path.read_text())

    optional_dependencies = data["project"]["optional-dependencies"]

    assert "temporal" in optional_dependencies
    assert "temporalio>=1.29,<2.0" in optional_dependencies["temporal"]


def test_standard_import_path_does_not_require_temporalio():
    driver = TemporalRuntimeDriver(namespace="default", task_queue="mnemosyne-stage1")

    assert driver.namespace == "default"
    assert driver.task_queue == "mnemosyne-stage1"


def test_temporalio_import_status_is_observed_but_not_required():
    temporalio_spec = importlib.util.find_spec("temporalio")

    assert temporalio_spec is None or temporalio_spec.name == "temporalio"