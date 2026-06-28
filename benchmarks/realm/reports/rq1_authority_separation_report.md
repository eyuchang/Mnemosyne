# RQ1 Authority Separation Report

Generated proposers may be wrong, weak, or adversarial. The ATP boundary should preserve committed-state correctness relative to constraint set C.

| System | Proposers | Workloads per proposer | Invalid commits | Rejected invalid proposals | Valid commits |
|---|---:|---:|---:|---:|---:|
| raw_append | 5 | 8 | 35 | 0 | 5 |
| self_validation | 5 | 8 | 35 | 0 | 5 |
| atp_mnemosyne | 5 | 8 | 0 | 35 | 5 |

## Claim boundary

This experiment tests authority separation, not learning, regret reduction, or preemptive planning.
The guarantee is relative to the declared constraint set C.
