# R6.8 REALM J1-J4 JSSP Readiness and API-Bound Recovery

R6.8 adds executable REALM-Bench coverage for J1-J4 while keeping the recovery claims precise.

## Coverage

- J1: deterministic static JSSP baseline.
- J2: deterministic dynamic recovery baseline plus API-bound recovery through active commitment memory, proposal emission, repair admission, commitment finalization, and audit lineage.
- J3: deterministic static JSSP baseline.
- J4: dynamic contract only. Full recovery is not claimed because material/resource recovery substrate is not implemented yet.

## Claim boundary

R6.8 claims benchmark-local, API-bound J2 recovery.

R6.8 does not claim:

- durable production-runtime recovery logs,
- distributed/restart-safe recovery execution,
- full J4 material/resource recovery,
- optimal JSSP schedules.

## Main artifacts

- `benchmarks/realm/reports/jssp_j1_j4_readiness.md`
- `benchmarks/realm/reports/jssp_static_baselines_report.md`
- `benchmarks/realm/reports/jssp_dynamic_contracts_report.md`
- `benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.md`
- `benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.md`
- `benchmarks/realm/reports/jssp_j1_j4_suite_report.md`

## Next boundary

R6.9 should add material/resource recovery substrate for J4 or explicitly defer it to R7/R8 if the team chooses to reserve resource-level recovery for the production-runtime recovery substrate.
