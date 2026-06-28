# RQ8 Proposer Quality and Safety Invariant Report

Proposer quality changes usefulness and admission efficiency, but ATP keeps invalid commits at zero.

## System summary

| System | Attempts | Committed | Rejected | Invalid commits | Total utility |
|---|---:|---:|---:|---:|---:|
| direct_commit_baseline | 60 | 60 | 0 | 37 | 131 |
| atp_mnemosyne | 60 | 23 | 37 | 0 | 131 |

## Proposer summary under ATP

| Proposer | Attempts | Admitted | Rejected | Acceptance rate | Utility | First admission attempt | Invalid commits |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_intelligence | 10 | 1 | 9 | 0.10 | 1 | 8 | 0 |
| random_proposer | 10 | 2 | 8 | 0.20 | 4 | 5 | 0 |
| rule_based_proposer | 10 | 5 | 5 | 0.50 | 25 | 2 | 0 |
| solver_like_proposer | 10 | 8 | 2 | 0.80 | 64 | 1 | 0 |
| llm_like_proposer | 10 | 6 | 4 | 0.60 | 36 | 2 | 0 |
| adversarial_proposer | 10 | 1 | 9 | 0.10 | 1 | 10 | 0 |

## Claim boundary

This experiment studies proposer quality as usefulness, not learning.
It does not claim cross-episode improvement, regret reduction, or preemptive planning.
The safety invariant is relative to the declared constraint set C.
