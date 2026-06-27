from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_thanksgiving_api_binding_surface import (
    run_surface_report,
)


def test_thanksgiving_api_binding_surface_report_exports_available_modules(
    tmp_path: Path,
):
    result = run_surface_report(tmp_path)

    assert result.module_count == 7
    assert result.available_module_count >= 4
    assert result.callable_count > 0

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    report = json.loads(result.files["json"].read_text(encoding="utf-8"))

    modules = {item["module"]: item for item in report["modules"]}

    for module_name in [
        "mnemosyne.api.commitments",
        "mnemosyne.api.recovery",
        "mnemosyne.api.proposal_packages",
        "mnemosyne.api.audit",
    ]:
        assert module_name in modules
        assert modules[module_name]["available"] is True
        assert modules[module_name]["public_callables"]

    md = result.files["markdown"].read_text(encoding="utf-8")
    assert "# Thanksgiving API Binding Surface Report" in md
    assert "mnemosyne.api.commitments" in md
    assert "mnemosyne.api.recovery" in md
    assert "mnemosyne.api.proposal_packages" in md
    assert "mnemosyne.api.audit" in md


def test_committed_thanksgiving_api_binding_surface_report_is_current(
    tmp_path: Path,
):
    generated = run_surface_report(tmp_path)

    committed = {
        "json": Path("benchmarks/realm/reports/thanksgiving_api_binding_surface.json"),
        "markdown": Path("benchmarks/realm/reports/thanksgiving_api_binding_surface.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
