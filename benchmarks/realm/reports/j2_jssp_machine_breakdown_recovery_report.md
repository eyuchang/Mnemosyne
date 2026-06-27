# REALM J2 JSSP Machine-Breakdown Recovery Baseline

## Summary

- Case: J2
- Machine unavailable: `MachineA`
- Unavailable window: 4 to 6
- Initial makespan: 11
- Repaired makespan: 14
- Affected operations: 2
- Feasible after repair: True
- Optimality status: feasible_not_proven_optimal

## Affected Operations

- `Job2:O1` on `MachineA`: 3 to 5
- `Job3:O2` on `MachineA`: 5 to 6

## Constraint Checks

- precedence_satisfaction: True
- machine_capacity_satisfaction: True
- machine_downtime_satisfaction: True
- affected_operations_detected: True
- repair_changes_makespan: True

## Repaired Schedule

| Operation | Machine | Start | End |
|---|---|---:|---:|
| `Job1:O1` | `MachineA` | 0 | 3 |
| `Job2:O1` | `MachineA` | 6 | 8 |
| `Job3:O1` | `MachineB` | 0 | 4 |
| `Job1:O2` | `MachineB` | 4 | 6 |
| `Job2:O2` | `MachineC` | 8 | 9 |
| `Job3:O2` | `MachineA` | 8 | 9 |
| `Job1:O3` | `MachineC` | 9 | 11 |
| `Job2:O3` | `MachineB` | 9 | 13 |
| `Job3:O3` | `MachineC` | 11 | 14 |

## Claims

- executable_recovery_baseline: True
- api_bound_recovery_claimed: False
- j4_full_recovery_claimed: False
- production_runtime_claimed: False
- durable_logs_claimed: False

