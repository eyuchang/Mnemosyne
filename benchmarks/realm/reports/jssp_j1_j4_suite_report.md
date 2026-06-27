# REALM J1-J4 JSSP Suite Report

## Summary

- Readiness decision: `ready_for_executable_j1_j4_baselines`
- Static baseline cases: 2
- Dynamic contract cases: 2
- J2 deterministic recovery baseline: True
- J2 API-bound recovery: True
- J4 material recovery baseline: True
- J4 API-bound recovery: False
- Production-runtime recovery claimed: False
- Durable logs claimed: False

## Case Coverage

| Case | Mode | R6 status | Claim boundary |
|---|---|---|---|
| J1 | static | deterministic_static_baseline | feasible_not_proven_optimal |
| J2 | dynamic | deterministic_recovery_and_api_bound_commitment_recovery | benchmark_local_api_bound_recovery |
| J3 | static | deterministic_static_baseline | feasible_not_proven_optimal |
| J4 | dynamic | deterministic_material_resource_recovery_baseline | benchmark_local_material_recovery_not_api_bound |

## Generated Artifacts

- readiness_report: `benchmarks/realm/reports/jssp_j1_j4_readiness.md`
- static_baselines_report: `benchmarks/realm/reports/jssp_static_baselines_report.md`
- dynamic_contracts_report: `benchmarks/realm/reports/jssp_dynamic_contracts_report.md`
- j2_recovery_baseline_report: `benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.md`
- j2_api_bound_recovery_report: `benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.md`
- j4_material_recovery_report: `benchmarks/realm/reports/j4_jssp_material_recovery_report.md`

## R6.9 Decision

- J1 and J3 have deterministic static executable baselines.
- J2 has deterministic recovery plus API-bound recovery through active commitment memory, proposal emission, repair admission, commitment finalization, and audit lineage.
- J4 now has deterministic benchmark-local material/resource recovery.
- J4 is not yet API-bound to active commitment memory.
- R6.9 completes the R6 REALM J1-J4 executable benchmark layer without claiming production-runtime durable recovery.

