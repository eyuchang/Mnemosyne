# R4.5 Active Commitments

R4.5 adds CTL-resident active commitment memory to Mnemosyne.

An active commitment is a durable obligation recorded in the Committed Transition Log. It is not an external monitor, callback, side table, or hidden runtime flag. The CTL remains the source of truth.

## Core Idea

R4 enforced the admission boundary:

    proposal -> validation -> admitted CTL record

R4.5 adds active memory:

    commitment registered
        -> commitment fired
        -> recovery proposal emitted
        -> proposal admitted / rejected / discharged

A fired commitment may wake recovery logic, but it cannot mutate domain state directly.

## CTL Authority

The authoritative record is always the CTL.

    CTL = truth
    ActiveCommitmentIndex = replay-derived projection

The index may be rebuilt at any time from CTL records.

## Commitment Lifecycle

Normal path:

    live -> fired -> proposed -> admitted

Rejected path:

    live -> fired -> proposed -> rejected

Rejected commitments remain live so bounded recursive recovery may try again.

Terminal statuses:

    admitted
    discharged
    expired

These are no longer live.

## Important Invariant

A commitment transition only changes the commitment FSM:

    eid = commitment:<commitment_id>
    fsm = mnemosyne.commitment

It does not change the domain entity.

Domain state changes only through separately admitted domain CTL records.

## Demo

Run:

    python examples/r45_active_commitment_recovery_demo.py

The demo shows:

    domain starts stale
    commitment fires
    first recovery is rejected
    second recovery emits proposal
    domain remains stale after proposal
    domain changes only after admitted domain repair record
    commitment becomes admitted and no longer live
