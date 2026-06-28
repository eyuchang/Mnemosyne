# RQ5 Effective-State and Compensation Safety Report

Compensation must not orphan effective dependents, break effective chains, or cause StateView to project ineffective history as current truth.

| System | Scenarios | Invalid compensations admitted | Orphaned dependents | Broken chains | StateView mismatches | Valid compensations committed |
|---|---:|---:|---:|---:|---:|---:|
| saga_without_dependency_closure | 7 | 5 | 2 | 5 | 7 | 2 |
| latest_record_projection | 7 | 5 | 2 | 5 | 7 | 2 |
| atp_mnemosyne | 7 | 0 | 0 | 0 | 0 | 2 |

## Claim boundary

This experiment tests effective-state projection and dependency-closed compensation.
It does not claim learning, regret reduction, or preemptive planning.
The guarantee is relative to the declared dependency graph and effective-record predicates.
