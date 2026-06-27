# REALM J1-J4 JSSP Suite Report

## Summary

- Readiness decision: `ready_for_executable_j1_j4_baselines`
- Static baseline cases: 2
- Dynamic contract cases: 2
- J2 deterministic recovery baseline: True
- J2 API-bound recovery: True
- J4 full recovery claimed: False
- Production-runtime recovery claimed: False
- Durable logs claimed: False

## Case Coverage

| Case | Mode | R6.8 status | Claim boundary |
|---|---|---|---|
| J1 | static | deterministic_static_baseline | feasible_not_proven_optimal |
| J2 | dynamic | deterministic_recovery_and_api_bound_commitment_recovery | benchmark_local_api_bound_recovery |
| J3 | static | deterministic_static_baseline | feasible_not_proven_optimal |
| J4 | dynamic | contract_only_requires_material_resource_recovery_extension | no_full_recovery_claim |

## Generated Artifacts

- readiness_report: `benchmarks/realm/reports/jssp_j1_j4_readiness.md`
- static_baselines_report: `benchmarks/realm/reports/jssp_static_baselines_report.md`
- dynamic_contracts_report: `benchmarks/realm/reports/jssp_dynamic_contracts_report.md`
- j2_recovery_baseline_report: `benchmarks/realm/reports/j2_jssp_machine_breakdown_recovery_report.md`
- j2_api_bound_recovery_report: `benchmarks/realm/reports/j2_jssp_api_bound_recovery_report.md`

## R6.8 Decision

- J1 and J3 have deterministic static executable baselines.
- J2 has both a deterministic recovery baseline and an API-bound recovery path.
- J2 now exercises active commitment memory, proposal emission, admission, finalization, and audit lineage.
- J4 is intentionally contract-only because material/resource recovery substrate is not implemented yet.
- R6.8 does not claim production-runtime durable recovery.

