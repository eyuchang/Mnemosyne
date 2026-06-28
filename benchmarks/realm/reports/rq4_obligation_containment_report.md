# RQ4 Obligation Containment Report

An Active Commitment Record may wake and emit a proposal package, but it may not directly mutate committed domain truth.

| System | Continuations | Workloads per continuation | Unauthorized mutations | Proposal packages | Admitted repairs | Rejected repairs |
|---|---:|---:|---:|---:|---:|---:|
| trigger_direct_mutation | 4 | 6 | 12 | 0 | 0 | 0 |
| workflow_timer_direct_write | 4 | 6 | 16 | 0 | 0 | 0 |
| atp_mnemosyne | 4 | 6 | 0 | 12 | 4 | 20 |

## Claim boundary

This experiment tests obligation containment.
It does not claim learning, regret reduction, or preemptive planning.
The guarantee is relative to the declared ACR liveness, dependency-scope, and admission predicates.
