# R4.5 Recovery Invariants

R4.5 recovery is bounded, CTL-resident, and admission-controlled.

## Invariant 1: Recovery cannot bypass admission

A recovery proposal is not committed truth.

    fired commitment
        -> recovery proposal candidate
        -> validation/admission
        -> committed domain CTL record

Only the admitted domain CTL record mutates domain state.

## Invariant 2: Fired commitments are wakeups, not mutations

A fired commitment may wake recovery logic.

It may produce commitment-FSM transitions such as:

    commitment_proposal_emitted
    commitment_rejected
    commitment_admitted
    commitment_discharged

These are not domain-FSM transitions.

## Invariant 3: CTL is authoritative

Active commitment state is reconstructed from CTL.

    CTL records
        -> extract commitment events
        -> replay
        -> ActiveCommitmentIndex

No external commitment database is authoritative.

## Invariant 4: Recursive recovery is bounded

Recovery policy enforces:

    max_depth
    max_attempts
    scope containment

The loop stops when an allowed proposal is emitted, max attempts is reached, max depth is exceeded, or no proposals remain.

## Invariant 5: Recovery scope is constrained

A recovery proposal must stay inside the commitment dependency scope.

For R4.5, proposal_scope keys must exist in dependency_scope, and proposal_scope values must equal dependency_scope values.

## Invariant 6: Rejected recovery remains live

A rejected recovery does not discharge the commitment.

    rejected => still live

This allows bounded retry.

## Invariant 7: Admitted or discharged commitments are not live

    admitted => not live
    discharged => not live
    expired => not live

## Test Coverage

Key tests include:

    test_active_commitments_projection.py
    test_active_commitments_ctl.py
    test_active_commitments_candidates.py
    test_active_commitments_store_persistence.py
    test_active_commitments_proposal_boundary.py
    test_active_commitments_index.py
    test_active_commitments_store_index.py
    test_recovery_policy.py
    test_recovery_orchestrator.py
    test_recovery_store_persistence.py
    test_recovery_admission_boundary.py
    test_recovery_loop.py
    test_recovery_service.py
    test_r45_active_commitment_demo.py
