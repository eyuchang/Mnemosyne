# Artifact Evaluation: Agentic Transaction Processing / Mnemosyne

This repository contains the executable artifact for the ATP/Mnemosyne evaluation.

The artifact validates the paper's central claim:

> Generated actions, repairs, wakeups, compensations, and storage attempts remain non-authoritative until admitted through the transaction boundary. Relative to the declared constraint set C, committed-state correctness is decoupled from proposer intelligence.

## Evaluation scope

The completed artifact covers RQ1 through RQ8:

| RQ | Experiment | Test file |
|---|---|---|
| RQ1 | Authority Separation | `tests/experiments/test_rq1_authority_separation.py` |
| RQ2 | Serial-Equivalent Admission | `tests/experiments/test_rq2_serial_equivalent_admission.py` |
| RQ3 | Evidence-Preserving Repair | `tests/experiments/test_rq3_evidence_preserving_repair.py` |
| RQ4 | Obligation Containment | `tests/experiments/test_rq4_obligation_containment.py` |
| RQ5 | Effective-State Compensation | `tests/experiments/test_rq5_effective_state_compensation.py` |
| RQ6 | Storage-Substrate Correctness | `tests/experiments/test_rq6_storage_substrate_correctness.py` |
| RQ7 | J1-J4 End-to-End ATP Execution | `tests/experiments/test_rq7_j1_j4_end_to_end_atp.py` |
| RQ8 | Proposer Quality Safety Invariant | `tests/experiments/test_rq8_proposer_quality_safety_invariant.py` |

## Default validation command

Run the following from the repository root:

```bash
python -m pytest \
  tests/experiments/test_rq1_authority_separation.py \
  tests/experiments/test_rq2_serial_equivalent_admission.py \
  tests/experiments/test_rq3_evidence_preserving_repair.py \
  tests/experiments/test_rq4_obligation_containment.py \
  tests/experiments/test_rq5_effective_state_compensation.py \
  tests/experiments/test_rq6_storage_substrate_correctness.py \
  tests/experiments/test_rq7_j1_j4_end_to_end_atp.py \
  tests/experiments/test_rq8_proposer_quality_safety_invariant.py \
  -q
