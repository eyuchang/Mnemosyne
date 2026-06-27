# Thanksgiving Benchmark Suite Report

## Summary

- Suite id: `thanksgiving_p6_p9_suite`
- P6 feasible: True
- P9 feasible after repair: True
- Recovery wakeups: 2
- Recovery proposals: 1
- Admitted repairs: 1
- Optimality status: feasible_not_proven_optimal

## Generated reports

- P6/P9 executable benchmark report: `benchmarks/realm/reports/thanksgiving_p6_p9_report.md`
- P9 recovery trace report: `benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md`
- Thanksgiving suite index report: `benchmarks/realm/reports/thanksgiving_suite_report.md`

## Generated solution artifacts

- P6 static baseline: `benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json`
- P9 dynamic repair baseline: `benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json`

## Generated evaluation artifacts

- P6 static evaluation: `benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json`
- P9 dynamic evaluation: `benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json`
- P9 recovery trace: `benchmarks/realm/evaluations/p9_thanksgiving_recovery_trace.json`

## Generated recovery lifecycle artifacts

- P9 commitments: `benchmarks/realm/recovery/p9_thanksgiving_commitments.json`
- P9 wakeups: `benchmarks/realm/recovery/p9_thanksgiving_wakeups.json`
- P9 repair proposals: `benchmarks/realm/recovery/p9_thanksgiving_repair_proposals.json`
- P9 repair admissions: `benchmarks/realm/recovery/p9_thanksgiving_repair_admissions.json`
- P9 recovery lineage: `benchmarks/realm/recovery/p9_thanksgiving_recovery_lineage.json`

## What this suite demonstrates

- P6 has a deterministic feasible static baseline.
- P9 has a deterministic feasible repair baseline.
- The P9 repair is triggered at 10:00, when the delay notice arrives.
- The repair does not wait until James's original 13:00 arrival.
- The recovery trace exposes commitments, wakeups, repair proposal, admission, and lineage.

## Current limitations

- The suite uses deterministic feasible baselines.
- Optimality is not yet proven.
- The recovery trace models the Mnemosyne recovery pattern but does not yet call core CTL mutation APIs.

