from __future__ import annotations

import os

import pytest


POSTGRES_CONFORMANCE_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"


def test_postgres_live_conformance_is_opt_in_by_environment():
    assert POSTGRES_CONFORMANCE_ENV == "MNEMOSYNE_POSTGRES_DATABASE_URL"
    assert os.environ.get(POSTGRES_CONFORMANCE_ENV) is None


@pytest.mark.skipif(
    not os.environ.get(POSTGRES_CONFORMANCE_ENV),
    reason="live PostgreSQL conformance requires MNEMOSYNE_POSTGRES_DATABASE_URL",
)
@pytest.mark.asyncio
async def test_postgres_live_recovery_store_conformance_contract_placeholder():
    """Future live PostgreSQL conformance test.

    R7.6 intentionally defines the live-test boundary without implementing the
    PostgreSQL adapter. When MNEMOSYNE_POSTGRES_DATABASE_URL is supplied in a
    later milestone, this test should construct the PostgreSQL store and call
    observe_recovery_store_conformance with expects_restart_persistence=True.
    """

    pytest.fail(
        "PostgreSQL adapter is not implemented yet; R7.6 defines only the opt-in live-test boundary"
    )
