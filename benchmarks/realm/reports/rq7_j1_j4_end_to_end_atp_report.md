# RQ7 J1-J4 End-to-End ATP Execution Report

J1-J4 cases are driven through the transaction boundary: case -> proposal package -> admission -> CTL -> StateView.

| System | Cases | Packages | Admitted | Rejected | Invalid commits | Completed cases | StateView mismatches | Repair radius |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct_workflow_baseline | 4 | 9 | 9 | 0 | 3 | 4 | 3 | 4 |
| atp_mnemosyne | 4 | 9 | 6 | 3 | 0 | 4 | 0 | 4 |

## Claim boundary

This experiment tests end-to-end execution through ATP for J1-J4 cases.
It does not certify the broader P1-P10 readiness suites.
It does not claim learning, regret reduction, or preemptive planning.
