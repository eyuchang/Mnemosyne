# File: tests/benchmarks/test_realm_smoke_boundary.py
#
# Purpose:
#   Verify the Stage 1.2 REALM smoke-test boundary.
#
# Policy:
#   This test is marked realm, so it is visible in the repository but skipped
#   by the default public test run unless explicitly selected.
#
# Run explicitly with:
#   python -m pytest -q -m realm

from __future__ import annotations

import pytest

from mnemosyne.benchmarks import (
    BenchmarkCase,
    BenchmarkStep,
    collect_realm_case_metrics,
    realm_case_to_commit_batches,
)


def make_realm_correction_case() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="realm-smoke-correction-001",
        tenant_id="tenant:realm-smoke",
        workflow_id="workflow:realm-smoke-correction-001",
        entity_id="itinerary:REALM001",
        binding_id="binding:REALM001",
        fsm="ItineraryFSM",
        app_id="travel",
        schema_id="travel.transition",
        steps=[
            BenchmarkStep(
                step_id="hold_flight",
                state_before="draft",
                state_after="flight_held",
                action_type="hold_flight",
                attrs_after={
                    "flight": "UA100",
                    "destination": "Kyoto",
                },
                emit_outbox=True,
                outbox_provider="airline",
                outbox_effect_type="hold_flight",
            ),
            BenchmarkStep(
                step_id="cancel_flight",
                state_before="flight_held",
                state_after="cancelled",
                action_type="cancel",
                attrs_after={
                    "cancelled": True,
                    "reason": "benchmark_correction",
                },
                depends_on=["hold_flight"],
                compensates=["hold_flight"],
                emit_outbox=True,
                outbox_provider="airline",
                outbox_effect_type="cancel_flight",
            ),
        ],
    )


async def validate_and_commit(case_batch, store, validator) -> None:
    result = await validator.validate_batch(case_batch, store)

    assert result.ok, [error.code for error in result.errors]

    records = await validator.records_from_batch(case_batch, store)

    await store.commit_batch(case_batch, records)


@pytest.mark.realm
@pytest.mark.asyncio
async def test_realm_smoke_case_maps_to_ctl_stateview_and_metrics(store, validator):
    case = make_realm_correction_case()
    batches = realm_case_to_commit_batches(case)

    assert len(batches) == 2

    for batch in batches:
        await validate_and_commit(batch, store, validator)

    metrics = await collect_realm_case_metrics(store, case)

    assert metrics.case_id == "realm-smoke-correction-001"
    assert metrics.total_records == 2
    assert metrics.effective_records == 1
    assert metrics.ineffective_records == 1
    assert metrics.outbox_rows == 2
    assert metrics.final_state == "cancelled"
    assert metrics.state_version == 2

    assert not await store.is_effective(
        "tenant:realm-smoke",
        "realm-realm-smoke-correction-001-hold_flight",
    )
    assert await store.is_effective(
        "tenant:realm-smoke",
        "realm-realm-smoke-correction-001-cancel_flight",
    )