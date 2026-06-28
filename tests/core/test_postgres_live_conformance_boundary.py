from __future__ import annotations

import os

import pytest

from mnemosyne.core.store_conformance import (
    RecoveryStoreConformanceCase,
    observe_recovery_store_conformance,
)
from mnemosyne.store.postgres import PostgresStore, PostgresStoreConfig


POSTGRES_CONFORMANCE_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"


def test_postgres_live_conformance_env_boundary_is_named():
    assert POSTGRES_CONFORMANCE_ENV == "MNEMOSYNE_POSTGRES_DATABASE_URL"


@pytest.mark.skipif(
    not os.environ.get(POSTGRES_CONFORMANCE_ENV),
    reason="live PostgreSQL conformance requires MNEMOSYNE_POSTGRES_DATABASE_URL",
)
@pytest.mark.asyncio
async def test_postgres_live_recovery_store_conformance_contract():
    store = PostgresStore(
        PostgresStoreConfig(database_url=os.environ[POSTGRES_CONFORMANCE_ENV])
    )

    observation = await observe_recovery_store_conformance(
        store,
        RecoveryStoreConformanceCase(
            store_name="PostgresStore",
            expects_restart_persistence=True,
        ),
    )

    assert observation.passed is True
    assert observation.details["store_type"] == "PostgresStore"
    assert observation.details["duplicate_result_event_id"] == "conformance-event-1"
    assert observation.details["event_ids"] == [
        "conformance-event-1",
        "conformance-event-2",
    ]
