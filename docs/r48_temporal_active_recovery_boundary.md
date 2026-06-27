# R4.8 Temporal Active Recovery Boundary

R4.8 adds a Temporal-style activity boundary for active recovery.

The goal is not full Temporal orchestration yet. The goal is to prove the product boundary:

    Temporal workflow code orchestrates.
    Active recovery planning happens inside an activity boundary.
    Validation happens inside an activity boundary.
    CTL commit happens inside an activity boundary.
    Domain state is not mutated directly by recovery.

## Core invariant

Temporal active recovery may update commitment state, but it may not mutate domain state directly.

A fired or rejected active commitment can wake recovery. The recovery activity may emit and commit commitment-FSM records such as:

    commitment_proposal_emitted
    commitment_rejected

However, domain repair still requires separately admitted domain CTL records.

## Activity boundary

The R4.8 activity boundary is implemented in:

    mnemosyne/runtime/temporal/active_recovery.py

The main function is:

    plan_validate_and_commit_active_recovery_activity(...)

It is intentionally Temporal-SDK-free.

A future temporalio activity can call this function from inside a real Temporal activity implementation.

## Activity behavior

The activity performs:

    1. load active commitments from CTL/store
    2. plan bounded recovery for fired/rejected commitments
    3. validate commitment-FSM recovery candidates
    4. commit admitted commitment-FSM records
    5. return deterministic summary data to workflow orchestration

The returned result is:

    ActiveRecoveryActivityResult

It contains orchestration-safe summary data:

    batch_id
    tenant_id
    workflow_id
    committed_rids
    committed_fsms
    committed_action_types
    validation_ok
    skipped
    commitment_statuses

It does not return Store handles, CTL records, mutable candidates, or domain mutation authority.

## Runtime boundary

TemporalRuntimeDriver remains orchestration-only.

It can submit workflows, signal disruptions, and query workflow status through a Temporal client boundary.

It does not expose:

    commit_batch
    get_state_view

This preserves the source-of-truth rule:

    Temporal is orchestration.
    CTL/store is truth.

## Idempotency and replay safety

R4.8 proves the activity is safe under replay/retry pressure.

After a successful recovery activity:

    fired -> proposed

A second activity call does not duplicate the proposal.

Instead it returns:

    status_proposed_not_recoverable

This makes activity retries safe at the active-commitment level.

## Validation failure

If validation fails, the activity commits nothing.

The commitment remains in its previous state, such as:

    fired

Domain state remains unchanged.

## Demo

The R4.8 demo is:

    examples/r48_temporal_active_recovery_demo.py

It shows:

    1. TemporalRuntimeDriver submits a workflow
    2. Temporal runtime status becomes submitted
    3. domain state starts stale
    4. active recovery activity commits a commitment-FSM proposal record
    5. commitment status becomes proposed
    6. domain state remains stale
    7. second activity call is a no-op
    8. runtime driver still exposes no CTL mutation methods

## Tests

R4.8 adds tests for:

    Temporal active recovery activity boundary
    commitment-FSM-only recovery commits
    domain state non-mutation
    orchestration-only runtime driver behavior
    skipped live commitments
    retry/idempotency after successful proposal
    validation failure commits nothing
    workflow-safe activity summaries
    R4.8 demo end-to-end behavior

Expected full suite:

    179 passed, 24 skipped
