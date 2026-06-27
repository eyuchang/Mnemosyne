# R6.4 REALM-Bench Repository Layout and Reports

## Status

R6.4 moves REALM-Bench from a test-only fixture into a researcher-facing benchmark asset tree.

Current validation:

    251 passed, 24 skipped

## Purpose

R6.4 makes the benchmark usable and inspectable by researchers.

R6.3 proved that REALM-Bench cases could be extracted into deterministic fixtures.

R6.4 turns those fixtures into a public repository structure:

    cases
    adapters
    reports
    solutions
    evaluations
    scripts
    tests

This lets future contributors inspect, edit, expand, solve, and evaluate cases without digging through pytest-only files.

## Public benchmark directory

The benchmark now lives under:

    benchmarks/realm/

Directory layout:

    benchmarks/realm/
        README.md

        cases/
            realm_bench_cases.json
            p1_ct_static.json
            p2_mct_static.json
            p3_urs_static.json
            p4_urs_dynamic.json
            p5_wr_static.json
            p6_td_static.json
            p7_dl_static.json
            p8_wr_dynamic.json
            p9_td_dynamic.json
            p10_gsc_static_dynamic.json
            j1_jssp_simple_static.json
            j2_jssp_simple_dynamic.json
            j3_jssp_complex_static.json
            j4_jssp_complex_dynamic.json

        adapters/
            realm_case_loader.py
            thanksgiving_cases.py

        reports/
            realm_case_catalog_report.md
            realm_case_catalog_report.json

        solutions/
            README.md

        evaluations/
            README.md

        scripts/
            generate_case_catalog_report.py

## Cases

The `cases/` directory stores the canonical problem definitions.

It contains:

    P1-P10
    J1-J4

Each case is available both inside the aggregate fixture:

    benchmarks/realm/cases/realm_bench_cases.json

and as an individual case file.

This makes the benchmark easy to inspect manually and easy to consume programmatically.

## Adapters

The `adapters/` directory contains reusable benchmark code.

Current adapters:

    realm_case_loader.py
    thanksgiving_cases.py

The loader supports:

    load_realm_bench_cases()
    by_id(case_id)
    by_family(family)
    by_mode(mode)
    dynamic_cases()
    thanksgiving_cases()

The Thanksgiving adapter materializes P6 and P9 into typed deterministic Python objects.

## Reports

The `reports/` directory contains committed human-readable and machine-readable reports.

Current reports:

    benchmarks/realm/reports/realm_case_catalog_report.md
    benchmarks/realm/reports/realm_case_catalog_report.json

The report summarizes:

    all 14 cases
    dynamic/disruption cases
    P6 Thanksgiving static case
    P9 Thanksgiving dynamic case
    James flight-delay disruption
    current readiness status
    missing executable solution/evaluation status

## Solutions

The `solutions/` directory is reserved for baseline and reference solutions.

Each solution should state whether it is:

    optimal
    feasible but not proven optimal
    heuristic
    expected repair plan
    LLM-generated
    human-authored

Executable solution artifacts begin after R6.4.

## Evaluations

The `evaluations/` directory is reserved for evaluation artifacts.

Each evaluation should report:

    problem id
    solution id
    constraint satisfaction
    objective value if available
    optimality status
    disruption handling result
    known limitations

Executable evaluation artifacts begin after R6.4.

## Tests

Tests live under:

    tests/benchmarks/realm/

They verify that:

    all canonical case files are present
    the aggregate fixture loads
    per-case files match the aggregate fixture
    dynamic cases expose disruptions
    Thanksgiving P6/P9 adapters work
    committed reports are reproducible

## Current limitation

R6.4 is still a repository organization and reporting milestone.

It does not yet solve the benchmark cases.

It does not yet evaluate solution optimality.

It does not yet execute the Thanksgiving recovery workflow.

Those begin in the next milestone.

## Next milestone

R6.5 should add an executable Thanksgiving benchmark:

    P6 static baseline solution
    P9 James-delay disruption
    repair proposal
    evaluation JSON
    human-readable problem-solution-evaluation report

The expected researcher-facing report will be:

    benchmarks/realm/reports/thanksgiving_p6_p9_report.md
