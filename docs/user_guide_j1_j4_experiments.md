# Mnemosyne Product Runtime User Guide

## Running J1-J4 Experiments with SQLite or PostgreSQL

This guide explains how to clone the repo, start the required local services, run J1-J4 benchmark experiments, modify them, and find results.

## Current baseline

- R7.9 live PostgreSQL DATABASE_URL conformance.
- Default CI: 375 passed, 26 skipped.
- PostgreSQL is optional and env-gated.

## 1. GitHub entry point

Clone the repo:

    git clone git@github.com:eyuchang/mnemosyne-product.git
    cd mnemosyne-product

Use the latest stable tag:

    git checkout r7.9-live-postgres-database-url-conformance

Or use current main:

    git checkout main
    git pull origin main

For experiments, use a branch:

    git switch -c experiment/my-j1-j4-study

## 2. Python setup

    python -m venv .venv
    source .venv/bin/activate

    python -m pip install -U pip
    python -m pip install -e .

For PostgreSQL live testing:

    python -m pip install "psycopg[binary]"

## 3. Servers to start

Default mode requires no server.

    unset MNEMOSYNE_POSTGRES_DATABASE_URL
    python -m pytest tests/core tests/apps tests/benchmarks

PostgreSQL mode is optional. Start it only for live persistence validation:

    brew services start postgresql@16
    export PATH="$(brew --prefix postgresql@16)/bin:$PATH"

    createdb mnemosyne_r79 || true
    export MNEMOSYNE_POSTGRES_DATABASE_URL="postgresql://$(whoami)@localhost:5432/mnemosyne_r79"

    python -m pytest tests/core/test_postgres_live_database_url_conformance.py -q

Return to default mode:

    unset MNEMOSYNE_POSTGRES_DATABASE_URL

## 4. Store modes

SQLite is the default store. It requires no server.

PostgreSQL is activated only when:

    export MNEMOSYNE_POSTGRES_DATABASE_URL="postgresql://USER@HOST:PORT/DB"

Current PostgreSQL support covers:

- Recovery-event append.
- Duplicate idempotency.
- Sequence-conflict handling.
- List.
- Replay after list.
- Reopen persistence.

Not yet claimed:

- Full runtime state-store replacement.
- Connection pooling.
- High-concurrency stress testing.
- Kubernetes.
- Temporal.
- Production-runtime recovery.

## 5. Where J1-J4 live

Main benchmark and experiment locations:

- benchmarks/realm/
- tests/benchmarks/realm/
- tests/benchmarks/

Useful commands:

    python -m pytest tests/benchmarks/realm/test_jssp_j1_j4_readiness.py
    python -m pytest tests/benchmarks/realm/test_jssp_j1_j4_suite.py
    python -m pytest tests/benchmarks/realm/test_jssp_j2_api_bound_recovery.py
    python -m pytest tests/benchmarks/realm/test_jssp_j4_material_recovery_baseline.py

Run all REALM/JSSP benchmark tests:

    python -m pytest tests/benchmarks/realm

Run all benchmark tests:

    python -m pytest tests/benchmarks

Run everything:

    python -m pytest tests/core tests/apps tests/benchmarks

## 6. Where to put application or experiment code

Use this separation:

- mnemosyne/: product/runtime library code.
- benchmarks/: benchmark runners, experiment logic, report generators.
- tests/: validation tests.
- docs/: user-facing explanations and milestone notes.
- benchmarks/realm/reports/: generated or committed evidence reports.

For new J1-J4 experiment reports, use new filenames:

- benchmarks/realm/reports/my_j1_j4_experiment_report.md
- benchmarks/realm/reports/my_j1_j4_experiment_report.json
- tests/benchmarks/realm/test_my_j1_j4_experiment_report.py

## 7. Recommended experiment loop

    git checkout main
    git pull origin main
    git switch -c experiment/my-j1-j4-run

Run baseline:

    unset MNEMOSYNE_POSTGRES_DATABASE_URL
    python -m pytest tests/benchmarks/realm

Edit experiment files under:

- benchmarks/realm/
- tests/benchmarks/realm/

Run targeted tests:

    python -m pytest tests/benchmarks/realm/test_jssp_j1_j4_suite.py

Run full validation:

    python -m pytest tests/core tests/apps tests/benchmarks

Commit:

    git status --short
    git add <changed-files>
    git commit -m "Run J1-J4 experiment variant"

## 8. Where to find results

Human-readable reports:

- benchmarks/realm/reports/*.md

Machine-readable reports:

- benchmarks/realm/reports/*.json

Important current reports include:

- r79_live_postgres_database_url_conformance_report.md
- r78_postgres_live_adapter_report.md
- r77_postgres_adapter_skeleton_report.md
- r76_postgres_conformance_boundary_inspection.md

## 9. Troubleshooting

If createdb is missing:

    export PATH="$(brew --prefix postgresql@16)/bin:$PATH"

If PostgreSQL connection is refused:

    brew services start postgresql@16
    pg_isready -h localhost -p 5432

If live PostgreSQL tests run unintentionally:

    unset MNEMOSYNE_POSTGRES_DATABASE_URL

Default expected suite around R7.9:

    375 passed, 26 skipped

## 10. Mental model

Think of the repo in four layers:

1. mnemosyne/: product/runtime substrate.
2. benchmarks/realm/: experiment definitions and report scripts.
3. tests/: contracts and reproducibility gates.
4. benchmarks/realm/reports/: evidence produced by experiments and milestones.

For J1-J4 users:

- Start from GitHub.
- Use main or a milestone tag.
- Run default SQLite first.
- Edit benchmark cases under benchmarks/realm.
- Validate through tests/benchmarks/realm.
- Store results under benchmarks/realm/reports.
- Use PostgreSQL only when testing durable recovery-event persistence.
