from __future__ import annotations

from pathlib import Path


REPORT = Path("benchmarks/realm/reports/r710_postgres_concurrency_pooling_boundary_report.md")


def test_r710_postgres_concurrency_pooling_boundary_report_exists():
    assert REPORT.exists()
    assert REPORT.read_text(encoding="utf-8").strip()


def test_r710_postgres_concurrency_pooling_boundary_report_records_concurrency_evidence():
    text = REPORT.read_text(encoding="utf-8")

    assert "# R7.10 PostgreSQL Concurrency and Connection-Pooling Boundary Report" in text
    assert "Concurrent duplicate idempotency gate: passed." in text
    assert "Concurrent duplicate writers return one canonical event: passed." in text
    assert "Concurrent sequence-conflict gate: passed." in text
    assert "PostgresRecoveryEventConflictError" in text
    assert "tests/core/test_postgres_live_concurrent_recovery_events.py" in text
    assert "2 passed" in text


def test_r710_postgres_concurrency_pooling_boundary_report_preserves_claim_boundary():
    text = REPORT.read_text(encoding="utf-8")

    assert "Pool configuration object." in text
    assert "Lazy optional `psycopg_pool` import." in text
    assert "Default CI does not require `psycopg_pool`." in text
    assert "Default CI does not require PostgreSQL service." in text

    assert "Production pool deployment." in text
    assert "Pool-backed `PostgresStore` runtime path." in text
    assert "High-concurrency load testing." in text
    assert "Kubernetes." in text
    assert "Temporal." in text
    assert "Production-runtime recovery." in text
