import inspect

from mnemosyne.core.protocols import Store
from mnemosyne.store.sqlite import SQLiteStore


# ---------------------------------------------------------------------------
# Test purpose
# ---------------------------------------------------------------------------
#
# This file verifies Stage 0.2 protocol/interface alignment.
#
# Why this matters:
#
#   SQLiteStore is our current local/test store.
#   PostgresStore will later be the production store.
#
# Both should satisfy the same formal Store protocol.
#
# The Store protocol is the durable boundary for:
#
#   - command logging;
#   - event logging;
#   - inbox dedupe;
#   - CTL commit;
#   - effective-record lookup;
#   - StateView projection;
#   - outbox enqueue.
#
# If we add a public store method to SQLiteStore, such as:
#
#   record_inbox_event(...)
#
# we should also add it to Store. Otherwise future stores can silently drift
# from the contract.
# ---------------------------------------------------------------------------


def test_sqlite_store_satisfies_runtime_store_protocol():
    """Verify SQLiteStore structurally satisfies the Store protocol.

    API under test:
        isinstance(SQLiteStore(), Store)

    This works because Store is decorated with @runtime_checkable.

    Important limitation:
        Runtime protocol checks verify method presence, not full type
        signatures. Static tools such as mypy are still needed for deeper
        signature checks.

    Value:
        This catches missing methods early. For example, if Store requires
        record_inbox_event(...) but SQLiteStore does not implement it, this
        test will fail.
    """
    store = SQLiteStore()

    assert isinstance(store, Store)


def test_sqlite_store_exposes_all_required_async_store_methods():
    """Verify SQLiteStore exposes the required async Store API methods.

    This test is intentionally explicit.

    Reason:
        The runtime Protocol check above is useful, but this list makes the
        store contract readable to humans reviewing the test.

    Required API groups:

        Command/event:
            append_command
            append_event
            has_event
            record_inbox_event

        CTL/read model:
            is_effective
            get_state_view
            get_latest_version
            get_record
            get_entity_history

        Commit/outbox:
            commit_batch
            enqueue_outbox
    """
    required_async_methods = [
        "append_command",
        "append_event",
        "has_event",
        "record_inbox_event",
        "is_effective",
        "get_state_view",
        "get_latest_version",
        "get_record",
        "get_entity_history",
        "commit_batch",
        "enqueue_outbox",
    ]

    for method_name in required_async_methods:
        method = getattr(SQLiteStore, method_name, None)

        assert method is not None, f"SQLiteStore is missing {method_name}(...)"
        assert inspect.iscoroutinefunction(method), (
            f"SQLiteStore.{method_name}(...) must be async"
        )


def test_store_protocol_exposes_record_inbox_event_contract():
    """Verify Store protocol includes the Phase 0.1 inbox API.

    Contract:
        record_inbox_event(...) is now part of the formal Store protocol.

    Why this matters:
        Inbox dedupe is no longer just a SQLite implementation detail.
        It is part of the durable store boundary that future stores must
        implement.
    """
    assert hasattr(Store, "record_inbox_event")