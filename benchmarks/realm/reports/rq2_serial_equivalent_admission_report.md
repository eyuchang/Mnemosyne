# RQ2 Serial-Equivalent Generative Admission Report

Concurrent generated proposals are admitted only through a serialized transaction boundary.

| System | Proposals | Committed | Rejected | Invalid commits | Duplicate operation commits | Capacity underflow | Final capacity | Serial-equivalent |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| unserialized_generated_writes | 80 | 80 | 0 | 48 | 12 | 1 | -1632 | False |
| weak_lock_admission | 80 | 68 | 12 | 36 | 4 | 1 | -1620 | False |
| atp_mnemosyne | 80 | 32 | 48 | 0 | 0 | 0 | 0 | True |

## Claim boundary

This experiment tests serial-equivalent admission of concurrent generated proposals.
It does not claim that the proposer is intelligent, optimal, or improving.
The guarantee is relative to the declared admission constraints and storage transaction boundary.
