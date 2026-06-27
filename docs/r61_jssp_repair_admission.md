# R6.1 JSSP Selected Repair Admission

## Status

R6.1 closes the JSSP disruptive-planning semantic loop introduced in R6.0.

Current validation:

    235 passed, 24 skipped

## Purpose

R6.0 proved that disruption does not directly mutate schedule truth. It showed:

    baseline schedule
    -> active commitments
    -> machine breakdown
    -> affected commitments fired
    -> concrete repair candidates packaged
    -> recovery lineage audited
    -> schedule StateView remains unchanged

R6.1 adds the next required step:

    selected repair candidate
    -> admitted through normal domain CTL
    -> selected schedule StateViews mutate
    -> corresponding commitments are finalized as admitted
    -> unresolved commitment count drops

## Added modules

R6.1 adds:

    mnemosyne/benchmarks/jssp_repair_admission.py

R6.1 also adds:

    examples/r61_jssp_repair_admission_demo.py

## Added tests

R6.1 adds:

    tests/benchmarks/test_jssp_repair_admission.py
    tests/benchmarks/test_r61_jssp_repair_admission_demo.py

## Core semantic loop

The full R6.1 path is:

    baseline JSSP schedule admitted
    -> 9 active operation commitments registered
    -> M1 machine breakdown from 5-9 signaled
    -> affected commitments fired
    -> package-backed repair candidates proposed
    -> selected repair candidates admitted through domain CTL
    -> selected schedule StateViews mutate
    -> repaired commitments finalized as admitted

## Before repair admission

The affected operation windows are:

    J3:O2    4-7
    J2:O3    7-11

At this point, the recovery packages contain concrete inert candidates:

    J3:O2    9-12
    J2:O3    12-16

But schedule StateView remains unchanged.

## After selected repair admission

After explicit domain CTL admission:

    J3:O2    9-12
    J2:O3    12-16

Only selected operation StateViews mutate.

Unselected operations remain unchanged.

## Commitment finalization

After domain repair admission, the matching active commitments are finalized:

    J3:O2 commitment -> admitted
    J2:O3 commitment -> admitted

Commitment report state becomes:

    7 live
    2 admitted

Unresolved commitment count becomes:

    7

## Recovery lineage

R6.1 recovery lineage contains both proposal and admission events:

    2 commitment_proposal_emitted rows
    2 commitment_admitted rows

Total:

    4 recovery-lineage rows

## Source-of-truth invariant

R6.1 preserves the central architecture invariant:

    Recovery may propose.
    Product or policy may select.
    Domain CTL must admit.
    Only admitted domain CTL records mutate schedule truth.
    Commitment finalization is a separate commitment-FSM transition.

## What R6.1 does not yet do

R6.1 does not perform global JSSP optimization.

It intentionally does not yet:

    recompute downstream job precedence
    optimize final makespan
    call an external solver
    enforce multi-machine global feasibility after repair
    deploy durable production infrastructure

Those belong to R7/R8 and later R6.x extensions.

## Next checkpoint

After R6.1 is merged and tagged, pause for code review before starting R7.0.

Recommended code review scope:

    R5.0 product API
    R5.1 reporting and CLI
    R6.0 disruptive planning
    R6.1 selected repair admission
    CTL / StateView source-of-truth invariants
    recovery package inertness
    test adequacy
