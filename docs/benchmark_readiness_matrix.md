# Benchmark Readiness Matrix

## Summary

This document records which benchmark families are currently runnable in the default repository state.

Current default validation after R7.11:

- 388 passed, 29 skipped

## J-series readiness

The J-series is the currently runnable product benchmark family.

| Suite | Status | Notes |
|---|---|---|
| J1 | Runnable | Included in default test suite. |
| J2 | Runnable | Included in default test suite. |
| J3 | Runnable as part of J1-J4 readiness coverage | Covered by J1-J4 suite/readiness checks. |
| J4 | Runnable | Includes material recovery baseline coverage. |

Relevant test areas:

- tests/benchmarks/realm/test_jssp_j1_j4_readiness.py
- tests/benchmarks/realm/test_jssp_j1_j4_suite.py
- tests/benchmarks/realm/test_jssp_j2_api_bound_recovery.py
- tests/benchmarks/realm/test_jssp_j2_recovery_baseline.py
- tests/benchmarks/realm/test_jssp_j4_material_recovery_baseline.py

Conclusion:

- J1-J4 can be run now.

## P-series readiness

The P-series should not yet be described as fully runnable.

Current evidence shows P1-related test files, but they are dependency-gated or skipped in the default suite.

Observed P1 areas:

- tests/benchmarks/test_p1_solver_adapter.py
- tests/benchmarks/test_p1_solver_runner.py
- tests/benchmarks/test_realm_p1_campus_tour_fixture.py
- tests/benchmarks/test_realm_p1_campus_tour_solver.py

Current conclusion:

| Suite | Status | Notes |
|---|---|---|
| P1 | Partial / gated | Present, but not fully runnable by default. |
| P2 | Not certified | No default runnable suite certified yet. |
| P3 | Not certified | No default runnable suite certified yet. |
| P4 | Not certified | No default runnable suite certified yet. |
| P5 | Not certified | No default runnable suite certified yet. |
| P6 | Not certified | No default runnable suite certified yet. |
| P7 | Not certified | No default runnable suite certified yet. |
| P8 | Not certified | No default runnable suite certified yet. |
| P9 | Not certified | No default runnable suite certified yet. |
| P10 | Not certified | No default runnable suite certified yet. |

Conclusion:

- J1-J4: runnable now.
- P1-P10: not yet fully runnable or certified.

The next benchmark-readiness milestone should either certify P1 as fully runnable or define and implement the missing P2-P10 benchmark suites.
