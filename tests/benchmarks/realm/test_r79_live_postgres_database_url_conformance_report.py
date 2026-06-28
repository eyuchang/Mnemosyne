from __future__ import annotations

from pathlib import Path


REPORT = Path("benchmarks/realm/reports/r79_live_postgres_database_url_conformance_report.md")


def test_r79_live_postgres_database_url_conformance_report_exists():
    assert REPORT.exists()
    assert REPORT.read_text(encoding="utf-8").strip()


def test_r79_live_postgres_database_url_conformance_report_records_live_and_default_paths():
    text = REPORT.read_text(encoding="utf-8")

    assert "# R7.9 Live PostgreSQL DATABASE_URL Conformance Report" in text
    assert "Live PostgreSQL server: yes" in text
    assert "Live DATABASE_URL test: passed" in text
    assert "Live append/list/replay/reopen path: passed" in text
    assert "Live duplicate idempotency path: passed" in text
    assert "Live sequence-conflict path: passed" in text
    assert "Live conformance contract path: passed" in text

    assert "Default CI PostgreSQL dependency: no" in text
    assert "Default CI live PostgreSQL tests: skipped" in text
    assert "Full suite: 372 passed, 26 skipped" in text


def test_r79_live_postgres_database_url_conformance_report_preserves_claim_boundary():
    text = REPORT.read_text(encoding="utf-8")

    assert "Real PostgreSQL DATABASE_URL conformance." in text
    assert "Default CI remains PostgreSQL-free." in text
    assert "Kubernetes." in text
    assert "Temporal." in text
    assert "Distributed storage." in text
    assert "Production-runtime recovery." in text
    assert "Connection pooling." in text
    assert "High-concurrency load testing." in text
