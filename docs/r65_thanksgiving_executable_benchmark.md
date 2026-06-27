# R6.5 Thanksgiving P6/P9 Executable Benchmark

## Status

R6.5 adds the first executable REALM-Bench benchmark report.

Current validation:

    253 passed, 24 skipped

## Purpose

R6.4 made REALM-Bench visible as a researcher-facing benchmark tree.

R6.5 begins executable benchmark reporting.

The first executable benchmark covers:

    P6 Thanksgiving Dinner Planning / TD-static
    P9 Thanksgiving with Disruptions / TD-dynamic

## Runner

Run:

    python benchmarks/realm/scripts/run_thanksgiving_benchmark.py

The runner generates solution, evaluation, and report artifacts.

## Generated solutions

    benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json
    benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json

The P6 solution is a deterministic feasible baseline.

The P9 solution is a deterministic repair baseline.

Both are marked:

    feasible_not_proven_optimal

## Generated evaluations

    benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json
    benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json

The evaluations check:

    cooking supervision
    pickup completion
    all family members home before dinner
    dinner ready by 18:00
    disruption noticed at 10:00
    repair does not wait until 13:00
    Grandma pickup is reassigned
    original static constraints remain active

## Generated report

    benchmarks/realm/reports/thanksgiving_p6_p9_report.md
    benchmarks/realm/reports/thanksgiving_p6_p9_report.json

The Markdown report shows:

    problem
    static solution
    disruption
    repair
    evaluation
    optimality status
    limitations

## P6 result

P6 is feasible.

Baseline plan:

    Sarah supervises turkey from 09:00 to 13:00.
    James lands at BOS at 13:00, rents a car, and picks up Grandma.
    Sarah picks up Emily.
    Michael arrives by car.
    Side dishes finish at 18:00.

Result:

    all family home by 15:30
    dinner ready at 18:00

## P9 result

P9 is feasible after repair.

Disruption:

    James original arrival: 13:00
    James new arrival: 16:00
    notice time: 10:00
    delay: 180 minutes

Repair:

    trigger time: 10:00
    Grandma pickup: James -> Sarah

Result:

    all family home by 17:30
    dinner ready at 18:00

## Important limitation

R6.5 is an executable deterministic benchmark baseline.

It does not yet prove optimality.

It does not yet run through Mnemosyne CTL admission, active commitments, or recovery lineage.

A later milestone can connect this benchmark to the runtime admission/recovery substrate.
