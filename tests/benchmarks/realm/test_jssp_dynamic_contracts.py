from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.scripts.inspect_jssp_dynamic_contracts import run_dynamic_contracts


def test_jssp_dynamic_contracts_separate_j2_and_j4_readiness(tmp_path: Path):
    result = run_dynamic_contracts(tmp_path)

    assert result.case_count == 2
    assert result.existing_substrate_ready_count == 1
    assert result.requires_extension_count == 1

    for path in result.files.values():
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    j2 = json.loads(result.files["j2_contract_json"].read_text(encoding="utf-8"))
    j4 = json.loads(result.files["j4_contract_json"].read_text(encoding="utf-8"))

    assert j2["case_id"] == "J2"
    assert j2["mode"] == "dynamic"
    assert j2["has_machine_breakdown"] is True
    assert j2["has_stochastic_delay"] is True
    assert j2["readiness"] == "ready_for_existing_machine_breakdown_recovery"
    assert j2["claims"]["full_recovery_claimed"] is False

    breakdowns = [
        event for event in j2["actionable_events"]
        if event["type"] == "machine_breakdown"
    ]
    assert breakdowns == [
        {
            "event_id": "j2-machine-breakdown-2",
            "existing_jssp_substrate": "supported",
            "machine": "MachineA",
            "maps_to": [
                "mnemosyne.benchmarks.jssp_disruptions",
                "mnemosyne.benchmarks.jssp_disruption_commitments",
                "mnemosyne.benchmarks.jssp_recovery_proposals",
                "mnemosyne.benchmarks.jssp_repair_admission",
            ],
            "type": "machine_breakdown",
            "unavailable_end": 6,
            "unavailable_start": 4,
        }
    ]

    assert j4["case_id"] == "J4"
    assert j4["mode"] == "dynamic"
    assert j4["has_material_unavailability"] is True
    assert j4["readiness"] == "requires_material_recovery_extension"
    assert j4["claims"]["full_recovery_claimed"] is False
    assert j4["extension_requirements"] == [
        "material_unavailability requires material/resource commitment and repair substrate"
    ]


def test_jssp_dynamic_contracts_report_is_human_readable(tmp_path: Path):
    result = run_dynamic_contracts(tmp_path)

    report = json.loads(result.files["report_json"].read_text(encoding="utf-8"))
    assert report["schema_version"] == "realm_jssp_dynamic_contracts_report.v1"
    assert report["summary"] == {
        "case_count": 2,
        "existing_substrate_ready_count": 1,
        "requires_extension_count": 1,
    }

    md = result.files["report_markdown"].read_text(encoding="utf-8")
    assert "# REALM JSSP Dynamic Disruption Contracts Report" in md
    assert "J2 can proceed to existing machine-breakdown recovery binding." in md
    assert "J4 must not be presented as fully recoverable yet." in md
    assert "material/resource recovery extension" in md


def test_committed_jssp_dynamic_contract_artifacts_are_current(tmp_path: Path):
    generated = run_dynamic_contracts(tmp_path)

    committed = {
        "j2_contract_json": Path("benchmarks/realm/evaluations/j2_jssp_dynamic_contract.json"),
        "j4_contract_json": Path("benchmarks/realm/evaluations/j4_jssp_dynamic_contract.json"),
        "report_json": Path("benchmarks/realm/reports/jssp_dynamic_contracts_report.json"),
        "report_markdown": Path("benchmarks/realm/reports/jssp_dynamic_contracts_report.md"),
    }

    for key, path in committed.items():
        assert path.exists()
        assert path.read_text(encoding="utf-8") == generated.files[key].read_text(
            encoding="utf-8"
        )
