from __future__ import annotations

import inspect

from mnemosyne.store.postgres.store import PostgresStore


def test_schema_init_commits_before_schema_initialized_flag_is_set():
    source = inspect.getsource(PostgresStore._initialize_schema_once)

    assert "self._commit(connection)" in source
    assert "self._schema_initialized = True" in source
    assert source.index("self._commit(connection)") < source.index(
        "self._schema_initialized = True"
    )


def test_pooled_connection_provider_branch_does_not_close_provider_owned_connection():
    source = inspect.getsource(PostgresStore._managed_connection)

    provider_branch = source.split(
        "if self._connection_provider is not None:", 1
    )[1].split("connection = self._connect()", 1)[0]

    assert "self._rollback" in provider_branch
    assert "self._close" not in provider_branch
