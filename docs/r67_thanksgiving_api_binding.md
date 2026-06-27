# R6.7 Thanksgiving API-Bound Recovery

## Status

R6.7 binds the Thanksgiving P9 recovery benchmark to real Mnemosyne APIs.

Current validation:

    265 passed, 24 skipped

## Purpose

R6.6 modeled the Thanksgiving P9 recovery lifecycle as deterministic benchmark artifacts.

R6.7 adds an API-bound execution path that uses the real Mnemosyne API surface:

    register_active_commitment
    fire_active_commitment
    create_recovery_proposal_package
    emit_package_backed_proposal
    admit_active_commitment
    get_active_commitment_status
    audit_active_commitments
    audit_commitment_lineage
    audit_recovery_lineage
    list_unresolved_commitments

The API-bound runner still uses a local SQLiteStore, but the commitment, proposal, admission, and audit transitions now pass through Mnemosyne APIs.

## Main commands

Inspect the available API surface:

    python benchmarks/realm/scripts/inspect_thanksgiving_api_binding_surface.py

Run the API-bound P9 recovery:

    python benchmarks/realm/scripts/run_thanksgiving_api_bound_recovery.py

Run the full Thanksgiving suite:

    python benchmarks/realm/scripts/run_thanksgiving_suite.py

## Generated reports

API surface report:

    benchmarks/realm/reports/thanksgiving_api_binding_surface.md
    benchmarks/realm/reports/thanksgiving_api_binding_surface.json

API-bound recovery report:

    benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.md
    benchmarks/realm/reports/thanksgiving_api_bound_recovery_report.json

Suite report:

    benchmarks/realm/reports/thanksgiving_suite_report.md
    benchmarks/realm/reports/thanksgiving_suite_report.json

## Generated API-bound artifact

    benchmarks/realm/api_bound/p9_thanksgiving_api_bound_recovery.json

## API-bound lifecycle

The R6.7 API-bound runner performs this lifecycle:

    create SQLiteStore
    register four Thanksgiving commitments
    fire affected commitments at James delay notice time
    create recovery proposal package
    emit package-backed proposal
    admit selected Grandma pickup repair
    read commitment statuses
    read active commitment audit
    read commitment lineage
    read recovery lineage
    read unresolved commitments

## P9 disruption

The disruption remains the REALM-Bench Thanksgiving P9 dynamic case:

    James delay notice time: 10:00
    original arrival: 13:00
    new arrival: 16:00
    delay: 180 minutes

The recovery requirement is to react at 10:00, not at James's original 13:00 arrival time.

## API-bound result

Current result:

    registered commitments: 4
    fired commitments: 2
    proposal packages: 1
    admitted repairs: 1
    feasible after repair: True
    latest family home time: 17:30
    dinner ready time: 18:00
    optimality status: feasible_not_proven_optimal

Final commitment statuses:

    p9-cook-turkey-supervision: live
    p9-pickup-emily: live
    p9-pickup-grandma-by-james: admitted
    p9-dinner-ready-by-1800: fired

## What R6.7 proves

R6.7 proves that the Thanksgiving P9 recovery is no longer only a static JSON trace.

It now exercises Mnemosyne's actual commitment, proposal package, admission, and audit APIs.

## Remaining limitation

R6.7 still uses:

    local SQLiteStore
    deterministic Thanksgiving repair plan
    benchmark-local runner

It does not yet bind the case to a durable production runtime, distributed store, or asynchronous service execution environment.
