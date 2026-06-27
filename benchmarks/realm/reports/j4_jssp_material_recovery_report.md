# REALM J4 Material Recovery Baseline

## Summary

- Case: J4
- Operation count: 20
- Initial makespan: 29
- Repaired makespan: 34
- Affected material-operation pairs: 6
- Feasible after repair: True
- Optimality status: feasible_not_proven_optimal

## Material Unavailability Realization

J4 names material-unavailability examples but does not define outage windows or a per-operation bill of materials; R6.9 makes this benchmark-local realization explicit.

- `C-X` unavailable from 4 to 8
- `F` unavailable from 6 to 10

## Affected Operations

- `J1:O2` requires `C-X` and initially ran 3 to 5
- `J2:O2` requires `C-X` and initially ran 5 to 6
- `J3:O2` requires `C-X` and initially ran 6 to 8
- `J1:O3` requires `C-X` and initially ran 5 to 9
- `J1:O3` requires `F` and initially ran 5 to 9
- `J2:O3` requires `F` and initially ran 9 to 14

## Constraint Checks

- case_file_loaded: True
- operation_templates_expanded: True
- material_policy_defined: True
- material_events_realized: True
- affected_operations_detected: True
- precedence_satisfaction: True
- machine_capacity_satisfaction: True
- material_availability_satisfaction: True
- repair_does_not_reduce_makespan: True

## Claims

- j4_material_recovery_claimed: True
- material_resource_substrate_claimed: True
- benchmark_local_recovery_claimed: True
- api_bound_recovery_claimed: False
- active_commitment_memory_claimed: False
- production_runtime_claimed: False
- durable_logs_claimed: False
- global_optimality_claimed: False

## Limitations

- This is a deterministic benchmark-local material recovery substrate.
- The J4 case provides material examples but no outage windows or bill-of-materials mapping; R6.9 makes those assumptions explicit.
- This commit does not bind material recovery to active commitment memory.
- This commit does not claim production-runtime durable recovery.

