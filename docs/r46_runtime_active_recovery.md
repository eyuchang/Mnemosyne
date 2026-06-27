# R4.6 Runtime Active Recovery

R4.6 integrates R4.5 active commitment recovery into the local runtime layer.

R4.5 established the core machinery:

    CTL-resident active commitments
    replay-derived active commitment index
    bounded recovery planning
    commitment-FSM recovery candidates
    recovery admission boundary

R4.6 adds local runtime execution around that machinery.

## Core invariant

Runtime recovery may update commitment state, but it may not mutate domain state directly.

A fired or rejected active commitment can wake recovery. Recovery may emit commitment-FSM records such as:

    commitment_rejected
    commitment_proposal_emitted

However, domain state changes still require separately admitted domain CTL records.

## Local executor

The local runtime integration is implemented by:

    mnemosyne/runtime/local/active_recovery.py

The main type is:

    LocalActiveRecoveryExecutor

It supports two execution paths.

## Plan and commit

    plan_and_commit(...)

This path:

    1. builds an active commitment index from CTL
    2. finds fired or rejected commitments
    3. asks a proposal provider for recovery proposals
    4. emits commitment-FSM recovery candidates
    5. commits those candidates to CTL

This path commits only commitment-FSM records.

It does not create domain repair records.

## Plan, validate, and commit

    plan_validate_and_commit(...)

This path adds admission validation.

It:

    1. plans recovery candidates
    2. validates each candidate through Validator.validate_batch
    3. materializes CTL records through Validator.records_from_batch
    4. commits admitted records through the store
    5. stops fail-closed if validation fails

Candidates are admitted sequentially because the current batch validator rejects duplicate entity/FSM transitions inside one batch.

This preserves the CTL admission boundary while still allowing a recovery loop to emit multiple commitment-FSM records over time.

## Commitment FSM

R4.6 adds a first-class commitment FSM helper:

    mnemosyne/core/commitments/fsm.py

It defines legal lifecycle transitions for:

    none -> live
    live -> fired
    fired -> proposed
    rejected -> proposed
    fired -> rejected
    proposed -> rejected
    proposed -> admitted
    fired/proposed/rejected -> discharged
    live/fired/proposed/rejected -> expired

The helper functions are:

    commitment_fsm_def()
    register_commitment_fsm(...)
    build_commitment_fsm_registry()

## Demo

The validated runtime recovery demo is:

    examples/r46_validated_runtime_recovery_demo.py

It shows:

    fired commitment
        -> local runtime executor plans recovery
        -> validator admits commitment-FSM proposal record
        -> CTL commits proposal record
        -> commitment status becomes proposed
        -> domain state remains stale

The key result is that runtime recovery updates commitment memory only.

Domain repair remains admission-controlled separately.

## Tests

R4.6 adds tests for:

    local executor commits recovery candidates
    live commitments are skipped
    rejected commitments can retry within bounds
    proposed commitments are not duplicated
    validated execution commits through Validator
    validation failure commits nothing
    sequential retry candidates are admitted safely
    domain state is not mutated by runtime recovery
    R4.6 demo runs end-to-end

Expected full suite:

    157 passed, 24 skipped
