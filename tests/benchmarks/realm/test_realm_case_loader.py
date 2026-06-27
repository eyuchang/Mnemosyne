from __future__ import annotations

import pytest

from benchmarks.realm.adapters.realm_case_loader import load_realm_bench_cases


def test_realm_case_loader_returns_all_cases_by_id():
    store = load_realm_bench_cases()

    assert store.case_ids == [
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

    assert store.by_id("P6")["short_name"] == "TD-static"
    assert store.by_id("P9")["short_name"] == "TD-dynamic"
    assert store.by_id("J2")["short_name"] == "JSSP-simple-dynamic"


def test_realm_case_loader_filters_by_family_and_mode():
    store = load_realm_bench_cases()

    planning = store.by_family("planning")
    jssp = store.by_family("jssp")
    dynamic = store.dynamic_cases()

    assert [case["case_id"] for case in planning] == [
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
    ]
    assert [case["case_id"] for case in jssp] == ["J1", "J2", "J3", "J4"]
    assert [case["case_id"] for case in dynamic] == ["P4", "P8", "P9", "J2", "J4"]


def test_realm_case_loader_exposes_thanksgiving_pair():
    store = load_realm_bench_cases()

    static_case, dynamic_case = store.thanksgiving_cases()

    assert static_case["case_id"] == "P6"
    assert dynamic_case["case_id"] == "P9"
    assert dynamic_case["extends"] == "P6"

    james_delay = dynamic_case["disruptions"][0]
    assert james_delay["type"] == "flight_delay"
    assert james_delay["person"] == "James"
    assert james_delay["notice_time_est"] == "10:00"
    assert james_delay["original_arrival_time"] == "13:00"
    assert james_delay["new_arrival_time"] == "16:00"


def test_realm_case_loader_raises_for_unknown_case():
    store = load_realm_bench_cases()

    with pytest.raises(KeyError):
        store.by_id("P99")
