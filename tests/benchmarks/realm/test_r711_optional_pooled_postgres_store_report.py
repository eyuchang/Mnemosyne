from __future__ import annotations

from pathlib import Path


REPORT = Path("benchmarks/realm/reports/r711_optional_pooled_postgres_store_report.md")


def test_r711_optional_pooled_postgres_store_report_exists():
    assert REPORT.exists()
    assert REPORT.read_text(encoding="utf-8").strip()


def test_r711_optional_pooled_postgres_store_report_records_runtime_path():
    text = REPORT.read_text(encoding="utf-8")

    assert "# R7.11 Optional Pooled PostgresStore Runtime Path Report" in text
    assert "Optional `connection_provider` support in `PostgresStore`." in text
    assert "Pool-compatible managed connection handling." in text
    assert "Fake-pool tests proving that pooled connections are borrowed and returned." in text
    assert "Rollback handling for pooled-provider failures." in text
    assert "The store does not close the pooled connection itself." in text


def test_r711_optional_pooled_postgres_store_report_records_validation_boundary():
    text = REPORT.read_text(encoding="utf-8")

    assert "Default suite after R7.11 Commit 2: 385 passed, 29 skipped." in text
    assert "tests/core/test_postgres_live_pooled_runtime_path.py" in text
    assert "1 passed" in text

    assert "Optional pooled `PostgresStore` runtime path." in text
    assert "Existing non-pooled `PostgresStore` path preserved." in text
    assert "Default CI remains PostgreSQL-free." in text
    assert "Default CI remains pool-dependency-free." in text

    assert "Production deployment." in text
    assert "Pool performance benchmarking." in text
    assert "High-concurrency pool saturation testing." in text
    assert "After R7.11, R7 should be considered complete." in text
