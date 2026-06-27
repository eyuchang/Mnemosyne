# R6.6 Thanksgiving Recovery Substrate Trace

## Status

R6.6 connects the Thanksgiving P9 disruption benchmark to an explicit recovery-substrate trace.

Current validation:

    259 passed, 24 skipped

## Purpose

R6.5 introduced an executable Thanksgiving P6/P9 benchmark:

    problem
    solution
    disruption
    repair
    evaluation
    report

R6.6 adds the recovery lifecycle:

    disruption event
    active commitments
    commitment wakeups
    repair proposal
    repair admission
    audit lineage
    suite report

This makes the P9 disruption inspectable as a recovery process, not only as a final repaired schedule.

## Main commands

Run the P6/P9 executable benchmark:

    python benchmarks/realm/scripts/run_thanksgiving_benchmark.py

Run the P9 recovery trace:

    python benchmarks/realm/scripts/run_thanksgiving_recovery_trace.py

Run the full Thanksgiving suite:

    python benchmarks/realm/scripts/run_thanksgiving_suite.py

## Reports

R6.6 produces these researcher-facing reports:

    benchmarks/realm/reports/thanksgiving_suite_report.md
    benchmarks/realm/reports/thanksgiving_p6_p9_report.md
    benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md

The suite report is the best starting point.

Open it with:

    open -a TextEdit benchmarks/realm/reports/thanksgiving_suite_report.md

## Recovery artifacts

R6.6 exports the recovery lifecycle as separate JSON artifacts:

    benchmarks/realm/recovery/p9_thanksgiving_commitments.json
    benchmarks/realm/recovery/p9_thanksgiving_wakeups.json
    benchmarks/realm/recovery/p9_thanksgiving_repair_proposals.json
    benchmarks/realm/recovery/p9_thanksgiving_repair_admissions.json
    benchmarks/realm/recovery/p9_thanksgiving_recovery_lineage.json

These artifacts let researchers inspect each stage independently.

## P9 disruption

The P9 disruption is James's flight delay:

    notice time: 10:00
    original arrival: 13:00
    new arrival: 16:00
    delay: 180 minutes

The key benchmark requirement is that the system reacts at notice time, not at the original arrival time.

## Affected commitments

The disruption affects:

    p9-pickup-grandma-by-james
    p9-dinner-ready-by-1800

It does not affect:

    p9-cook-turkey-supervision
    p9-pickup-emily

## Wakeups

The trace produces two wakeups:

    p9-wakeup-grandma-pickup
    p9-wakeup-dinner-deadline

Both wake at:

    10:00

Both require repair.

## Repair proposal

The selected repair proposal is:

    p9-proposal-reassign-grandma-to-sarah

Change:

    Grandma pickup assignee: James -> Sarah

Expected result:

    all family home by 17:30
    dinner ready at 18:00

## Repair admission

The repair admission is:

    p9-admit-reassign-grandma-to-sarah

Admission boundary:

    domain_validated_repair

Status:

    admitted

Admission time:

    10:00

Validation checks:

    repair triggered at notice time
    pickup assignment repaired
    dinner deadline preserved

## Suite result

Current suite result:

    P6 feasible: True
    P9 feasible after repair: True
    wakeups: 2
    proposals: 1
    admitted repairs: 1
    optimality status: feasible_not_proven_optimal

## Limitations

R6.6 is still a deterministic benchmark trace.

It models the Mnemosyne recovery pattern but does not yet call the core CTL mutation APIs directly.

Later work can bind these artifacts to:

    active commitment store
    recovery proposal package APIs
    admission boundary APIs
    audit lineage APIs
    durable runtime execution
