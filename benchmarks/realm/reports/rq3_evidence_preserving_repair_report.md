# RQ3 Evidence-Preserving Repair Report

A repair triggered by evidence must either resolve the underlying failure or preserve the evidence that justified the repair.

| System | Repair agents | Workloads per agent | Evidence-destroying repairs | Rejected evidence-destroying repairs | Valid repairs committed |
|---|---:|---:|---:|---:|---:|
| naive_repair | 4 | 8 | 20 | 0 | 4 |
| workflow_without_evidence_rule | 4 | 8 | 20 | 0 | 8 |
| atp_mnemosyne | 4 | 8 | 0 | 20 | 8 |

## Claim boundary

This experiment tests evidence-preserving repair safety.
It does not claim learning, regret reduction, or preemptive planning.
The guarantee is relative to the declared evidence and failure predicates.
