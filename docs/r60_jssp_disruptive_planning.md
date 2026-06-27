# R6.0 JSSP Disruptive Planning Benchmark Layer

## Status

R6.0 adds the first disruptive-planning benchmark path for JSSP.

Current validation:

    228 passed, 24 skipped

## Purpose

R6.0 proves that Mnemosyne can represent a planning disruption without directly mutating the plan.

The core path is:

    baseline schedule
    -> admitted CTL schedule records
    -> active commitments
    -> machine breakdown
    -> affected commitments fired
    -> concrete repair candidates packaged
    -> recovery lineage audited
    -> schedule StateView remains unchanged

## Added modules

R6.0 adds:

    mnemosyne/benchmarks/jssp_disruptions.py
    mnemosyne/benchmarks/jssp_schedule_admission.py
    mnemosyne/benchmarks/jssp_disruption_commitments.py
    mnemosyne/benchmarks/jssp_recovery_proposals.py

R6.0 also adds:

    examples/r60_jssp_disruptive_planning_demo.py

## Added tests

R6.0 adds:

    tests/benchmarks/test_jssp_disruptions.py
    tests/benchmarks/test_jssp_schedule_admission.py
    tests/benchmarks/test_jssp_disruption_commitments.py
    tests/benchmarks/test_jssp_recovery_proposals.py
    tests/benchmarks/test_r60_jssp_disruptive_planning_demo.py

## Baseline JSSP case

The first benchmark fixture is a deterministic 3x3 JSSP smoke case.

Jobs:

    J1: M1/3 -> M2/2 -> M3/2
    J2: M2/2 -> M3/1 -> M1/4
    J3: M3/4 -> M1/3 -> M2/1

Baseline makespan:

    11

The admitted baseline contains 9 scheduled operations.

## Disruption

The first disruption fixture is:

    machine: M1
    unavailable: 5-9

Affected scheduled operations:

    J3:O2    original window 4-7
    J2:O3    original window 7-11

## Commitments

R6.0 registers one active commitment per scheduled operation.

Commitment type:

    jssp_machine_availability_guard

The disruption fires only the affected commitments.

After disruption and proposal emission:

    7 commitments remain live
    2 commitments become proposed

## Recovery proposals

R6.0 emits package-backed recovery proposals for the affected operations.

Each package carries a concrete proposed domain candidate:

    action_type: reschedule
    fsm: JobOpFSM
    state_before: scheduled
    state_after: scheduled

The proposed repair candidates are inert.

They are carried inside the recovery package as `proposed_domain_candidates`, but they are not admitted into CTL by the recovery proposal path.

## Core invariant

R6.0 preserves the main source-of-truth boundary:

    A disruption does not directly rewrite the plan.
    A disruption wakes commitments.
    Recovery proposes repair.
    Audit explains lineage.
    Only a separately admitted domain CTL record may mutate schedule truth.

## Report export

The R6 demo exports:

    active_commitments.json
    active_commitments.md
    unresolved_commitments.json
    unresolved_commitments.md
    recovery_lineage.json
    recovery_lineage.md

Expected report semantics:

    active audit:
        7 live
        2 proposed

    unresolved report:
        9 non-terminal commitments

    recovery lineage:
        2 recovery packages

    schedule StateView:
        unchanged

## What R6.0 does not yet do

R6.0 does not yet solve the full JSSP repair problem.

It intentionally does not:

    globally recompute the schedule
    enforce downstream job-precedence repair
    optimize makespan after disruption
    admit repair candidates automatically
    run an external solver

Those belong to later R6.x / R8 milestones.

## Next recommended milestone

Proceed to R6.1 or R7.0 depending on priority.

Recommended R6.1:

    admit selected JSSP repair candidates through separate domain CTL
    verify StateView mutates only after explicit repair admission
    audit before/after schedule truth

Recommended R7.0:

    production runtime hardening
    PostgresStore
    migration scripts
    durable worker boundaries
    observability hooks
