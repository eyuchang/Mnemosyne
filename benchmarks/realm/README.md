# REALM-Bench Assets

This directory contains reusable REALM-Bench assets for Mnemosyne.

## Layout

    cases/
        Canonical JSON problem definitions for P1-P10 and J1-J4.

    adapters/
        Python loaders and typed adapters for benchmark cases.

    reports/
        Human-readable and machine-readable benchmark reports.

    solutions/
        Baseline and reference solutions.

    evaluations/
        Evaluation outputs and constraint-checking summaries.

    scripts/
        Report-generation and benchmark utility scripts.

## Current status

R6.4 starts by moving REALM-Bench assets out of the test-only tree and into a public benchmark directory.

The tests under `tests/benchmarks/realm/` verify that these assets load and remain deterministic.


## How to use

Inspect the full case catalog:

    benchmarks/realm/reports/realm_case_catalog_report.md

Load cases programmatically:

    from benchmarks.realm.adapters.realm_case_loader import load_realm_bench_cases

    store = load_realm_bench_cases()
    p6 = store.by_id("P6")
    p9 = store.by_id("P9")

Load typed Thanksgiving scenarios:

    from benchmarks.realm.adapters.thanksgiving_cases import (
        thanksgiving_static_scenario,
        thanksgiving_dynamic_scenario,
    )

    static = thanksgiving_static_scenario()
    dynamic = thanksgiving_dynamic_scenario()

## Researcher-facing contract

Cases are stored in:

    benchmarks/realm/cases/

Reports are stored in:

    benchmarks/realm/reports/

Solutions are stored in:

    benchmarks/realm/solutions/

Evaluations are stored in:

    benchmarks/realm/evaluations/

Tests are stored in:

    tests/benchmarks/realm/

The cases and reports are committed artifacts.
Tests verify that the committed artifacts remain loadable and deterministic.


## Executable Thanksgiving benchmark

R6.5 adds an executable deterministic Thanksgiving benchmark for:

    P6 Thanksgiving Dinner Planning / TD-static
    P9 Thanksgiving with Disruptions / TD-dynamic

Run:

    python benchmarks/realm/scripts/run_thanksgiving_benchmark.py

This generates:

    benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json
    benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json

    benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json
    benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json

    benchmarks/realm/reports/thanksgiving_p6_p9_report.json
    benchmarks/realm/reports/thanksgiving_p6_p9_report.md

Open the report:

    open benchmarks/realm/reports/thanksgiving_p6_p9_report.md

Current result:

    P6 feasible: True
    P9 feasible after repair: True
    P6 optimality: feasible_not_proven_optimal
    P9 optimality: feasible_not_proven_optimal

P9 disruption:

    James's flight delay is known at 10:00.
    Original arrival: 13:00
    New arrival: 16:00
    Delay: 180 minutes

Repair:

    Grandma pickup is reassigned from James to Sarah.
    The repair is triggered at 10:00, not at James's original 13:00 arrival time.
    Dinner remains feasible by 18:00.


## Thanksgiving recovery substrate trace

R6.6 adds a recovery-substrate trace for the Thanksgiving P9 disruption case.

Run the recovery trace only:

    python benchmarks/realm/scripts/run_thanksgiving_recovery_trace.py

Run the full Thanksgiving suite:

    python benchmarks/realm/scripts/run_thanksgiving_suite.py

Generated recovery trace report:

    benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md

Generated suite report:

    benchmarks/realm/reports/thanksgiving_suite_report.md

Generated recovery artifacts:

    benchmarks/realm/recovery/p9_thanksgiving_commitments.json
    benchmarks/realm/recovery/p9_thanksgiving_wakeups.json
    benchmarks/realm/recovery/p9_thanksgiving_repair_proposals.json
    benchmarks/realm/recovery/p9_thanksgiving_repair_admissions.json
    benchmarks/realm/recovery/p9_thanksgiving_recovery_lineage.json

R6.6 shows the P9 lifecycle:

    disruption
    affected commitments
    commitment wakeups
    repair proposal
    repair admission
    audit lineage

Current result:

    P6 feasible: True
    P9 feasible after repair: True
    wakeups: 2
    proposals: 1
    admitted repairs: 1

Important limitation:

    R6.6 models the Mnemosyne recovery pattern as deterministic benchmark artifacts.
    It does not yet call core CTL mutation APIs directly.


## Thanksgiving API-bound recovery

R6.7 adds an API-bound execution path for the Thanksgiving P9 recovery case.

Run the API-bound recovery only:

    python benchmarks/realm/scripts/run_thanksgiving_api_bound_recovery.py

Run the full Thanksgiving suite:

    python benchmarks/realm/scripts/run_thanksgiving_suite.py

Generated API-bound recovery report:

    benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.md

Generated API-bound artifact:

    benchmarks/realm/api_bound/p9_thanksgiving_api_bound_recovery.json

R6.7 exercises the real Mnemosyne APIs:

    register_active_commitment
    fire_active_commitment
    create_recovery_proposal_package
    emit_package_backed_proposal
    admit_active_commitment
    audit_active_commitments
    audit_commitment_lineage
    audit_recovery_lineage
    list_unresolved_commitments

Current result:

    registered commitments: 4
    fired commitments: 2
    proposal packages: 1
    admitted repairs: 1
    P9 feasible after repair: True

Limitation:

    R6.7 uses a local SQLiteStore and deterministic repair plan.
    Durable production runtime binding remains future work.
