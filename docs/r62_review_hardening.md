# R6.2 Review Hardening

## Status

R6.2 is a review-hardening checkpoint after R6.1.

It does not start R7.0 infrastructure work.

Current validation:

    237 passed, 24 skipped

## Purpose

R6.1 closed the selected-repair semantic loop:

    disruption
    -> active commitments fired
    -> recovery proposals emitted
    -> selected repair candidates admitted through domain CTL
    -> selected StateViews mutate
    -> matching commitments finalized as admitted

An external code review found no critical invariant-breaking defects. The primary source-of-truth invariant holds structurally and in tests.

R6.2 records that review and adds missing negative coverage before production hardening begins.

## Primary invariant

The reviewed invariant remains:

    A disruption must not directly mutate domain truth.
    A disruption wakes commitments.
    Recovery proposes repair.
    Product or policy selects.
    Domain CTL admits.
    Only admitted domain CTL records mutate StateView.
    Commitment finalization is a separate commitment-FSM transition.

## External review result

Critical issues:

    none

Major design concerns:

    audit.py is currently coupled to the SQLite store.
    selected repair admission still trusts a caller-supplied validator.

Minor cleanup:

    R6.1 demo originally hardcoded the intermediate unresolved count.
    benchmark code still uses loose store and validator typing.
    commitment finalization uses a lazy import for admit_active_commitment.

## R6.2 changes

R6.2 adds fail-closed repair-admission tests:

    invalid repair candidate
    -> validation fails
    -> no records generated
    -> no records committed
    -> affected StateViews remain unchanged
    -> unresolved count remains 9

R6.2 also adds an empty-selection no-op test:

    empty repair candidate set
    -> no validation attempted
    -> no records generated
    -> no records committed
    -> StateViews remain unchanged
    -> unresolved count remains 9

R6.2 updates the R6.1 demo so it measures the full intermediate state directly:

    unresolved before repair: 9
    unresolved after domain repair: 9
    unresolved after commitment finalization: 7

## What R6.2 intentionally does not do

R6.2 does not implement:

    PostgresStore
    migrations
    production outbox/inbox durability
    worker retries
    production observability
    audit-store abstraction
    enforced server-side validated admission

Those are R7.0 production-hardening work.

## R7.0 blockers

R7.0 should start by addressing two review findings.

### R7.0 blocker 1: audit/report portability

Current issue:

    audit.py reaches into the concrete SQLite connection.

R7.0 target:

    move audit/report read paths behind store protocol methods
    run audit/report tests against the durable store backend

### R7.0 blocker 2: enforced validated admission

Current issue:

    commit_batch is a low-level commit primitive
    benchmark admission helpers depend on caller-supplied validators

R7.0 target:

    make validated admission the single public mutation path
    keep commit_batch internal or explicitly low-level
    add negative tests showing invalid domain transitions cannot reach projection

## R6.2 checkpoint statement

After R6.2:

    all active deterministic tests pass
    invalid repair admission fails closed
    empty repair admission is a no-op
    the demo measures 9 -> 9 -> 7 directly
    R7.0 blockers are documented before production hardening begins
