# R7.4 Validated Recovery Admission Boundary

R7.4 hardens the public recovery-admission boundary.

## Added public boundary

- `admit_validated_active_commitment`
- `require_recovery_validator`
- `ValidatedRecoveryAdmissionError`

## Boundary rule

Public recovery admission must fail closed unless:

1. the store satisfies the recovery-store capability boundary, and
2. an explicit validator is supplied.

## Claim boundary

This commit adds the public validated admission boundary.

It does not yet remove or privatize every lower-level substrate helper.

R7.4 does not claim:

- PostgreSQL support,
- Kubernetes deployment,
- Temporal execution,
- production-runtime recovery execution.
