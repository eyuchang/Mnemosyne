# R4.7 Recovery Proposal Packages

R4.7 introduces recovery proposal packages.

A recovery proposal package is an inert product object that can describe a possible domain repair without admitting that repair into CTL.

## Core invariant

A proposal package may contain proposed domain candidates, but those candidates are not committed truth.

Only a separately admitted domain CTL record can mutate domain state.

In short:

    package describes repair
    commitment proposal records package reference
    domain repair remains inert
    later domain admission may apply repair

## Package model

The main model is:

    RecoveryProposalPackage

Defined in:

    mnemosyne/core/recovery/packages.py

A package contains:

    package_id
    commitment_id
    proposal_ref
    proposal_scope
    proposed_domain_candidates
    rationale
    validator_context
    created_from_record_id
    created_by

The proposed domain candidates are ordinary TransitionCandidate objects, but they are proposal material only.

They are not CTL records.

They are not effective state.

They are not domain truth.

## Package references in commitment events

Commitment proposal events may reference a package using:

    proposal_package_event_payload(...)
    proposal_package_reference_to_dict(...)
    proposal_package_reference_from_event_payload(...)

The commitment event stores only a package reference:

    package_id
    commitment_id
    proposal_ref
    proposal_scope
    candidate_rids
    candidate_count
    rationale
    created_from_record_id
    created_by

It does not store full proposed domain candidates.

This prevents commitment memory from becoming accidental domain admission.

## Package-backed proposal candidate

R4.7 adds:

    make_package_proposal_candidate(...)

Defined in:

    mnemosyne/core/recovery/package_candidates.py

This creates a commitment-FSM candidate:

    commitment_proposal_emitted

The candidate records that a package-backed proposal was emitted.

It does not commit package domain candidates.

## Admission boundary

The package-backed candidate enforces two boundaries:

    1. package scope must be inside the commitment dependency scope
    2. package contents must be domain candidates, not commitment-FSM candidates

If the package is out of scope, candidate creation fails.

If the package contains commitment-FSM candidates, candidate creation fails.

## Demo

The R4.7 demo is:

    examples/r47_recovery_proposal_package_demo.py

It shows:

    1. domain state starts stale
    2. commitment is registered and fired
    3. proposal package contains a domain repair candidate
    4. package-backed commitment proposal is admitted
    5. commitment status becomes proposed
    6. domain state remains stale
    7. package candidate is not in CTL
    8. later separate domain admission repairs the domain

## Tests

R4.7 adds tests for:

    package inertness
    package serialization
    scope containment
    domain-only package contents
    package references in commitment events
    package-backed proposal candidates
    admission boundary preservation
    demo end-to-end behavior

Expected full suite:

    171 passed, 24 skipped
