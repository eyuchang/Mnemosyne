from __future__ import annotations

import json
from pathlib import Path

from benchmarks.realm.adapters.realm_case_loader import REALM_CASE_FIXTURE

CASE_PATH = REALM_CASE_FIXTURE


def _fixture() -> dict:
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def _cases() -> dict[str, dict]:
    data = _fixture()
    return {case["case_id"]: case for case in data["cases"]}


def test_realm_bench_cases_fixture_has_all_paper_cases():
    data = _fixture()
    cases = data["cases"]

    assert data["schema_version"] == "realm_bench_cases.v1"
    assert len(cases) == 14
    assert [case["case_id"] for case in cases] == [
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "P10",
        "J1",
        "J2",
        "J3",
        "J4",
    ]


def test_realm_bench_thanksgiving_cases_are_available_for_static_and_dynamic_tests():
    cases = _cases()

    p6 = cases["P6"]
    p9 = cases["P9"]

    assert p6["short_name"] == "TD-static"
    assert p6["mode"] == "static"
    assert "cooking_supervision" in p6["metrics"]
    assert any(member["name"] == "James" for member in p6["entities"]["family_members"])
    assert any(member["name"] == "Emily" for member in p6["entities"]["family_members"])
    assert any(member["name"] == "Grandma" for member in p6["entities"]["family_members"])

    assert p9["short_name"] == "TD-dynamic"
    assert p9["mode"] == "dynamic"
    assert p9["extends"] == "P6"
    assert p9["disruptions"] == [
        {
            "type": "flight_delay",
            "person": "James",
            "original_arrival_time": "13:00",
            "new_arrival_time": "16:00",
            "notice_time_est": "10:00",
            "description": "James learns at 10 AM EST that his 1 PM BOS arrival is delayed to 4 PM.",
        }
    ]


def test_realm_bench_dynamic_cases_have_disruptions():
    cases = _cases()

    for case_id in ["P4", "P8", "P9", "J2", "J4"]:
        case = cases[case_id]
        assert case["mode"] == "dynamic"
        assert case["disruptions"], case_id


def test_realm_bench_jssp_cases_have_machine_operation_specs():
    cases = _cases()

    assert cases["J1"]["family"] == "jssp"
    assert cases["J2"]["extends"] == "J1"
    assert cases["J3"]["family"] == "jssp"
    assert cases["J4"]["extends"] == "J3"

    assert len(cases["J1"]["entities"]["jobs"]) == 3
    assert len(cases["J1"]["entities"]["machines"]) == 3
    assert len(cases["J3"]["entities"]["jobs"]) == 6
    assert len(cases["J3"]["entities"]["machines"]) == 4

    assert cases["J2"]["disruptions"]
    assert cases["J4"]["disruptions"]



def test_realm_bench_cases_are_available_as_per_case_files():
    data = _fixture()
    case_dir = CASE_PATH.parent

    expected_files = [
        "p1_ct_static.json",
        "p2_mct_static.json",
        "p3_urs_static.json",
        "p4_urs_dynamic.json",
        "p5_wr_static.json",
        "p6_td_static.json",
        "p7_dl_static.json",
        "p8_wr_dynamic.json",
        "p9_td_dynamic.json",
        "p10_gsc_static_dynamic.json",
        "j1_jssp_simple_static.json",
        "j2_jssp_simple_dynamic.json",
        "j3_jssp_complex_static.json",
        "j4_jssp_complex_dynamic.json",
    ]

    available_files = {path.name for path in case_dir.glob("*.json")}
    required_files = {"realm_bench_cases.json", *expected_files}

    # The public cases directory may contain auxiliary smoke or example JSON
    # files. The canonical REALM-Bench requirement is that all 14 extracted
    # case files are present and exactly match the aggregate fixture.
    assert required_files.issubset(available_files)

    by_id = {case["case_id"]: case for case in data["cases"]}
    for filename in expected_files:
        case = json.loads((case_dir / filename).read_text(encoding="utf-8"))
        assert case == by_id[case["case_id"]]
