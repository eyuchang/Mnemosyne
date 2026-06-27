# R5.0 Product API and Audit Surface

## Status

R5.0 adds the first product-facing API surface over the R4.5-R4.8 active commitment and recovery machinery.

Current validation:

    198 passed, 24 skipped

## Purpose

R4.5-R4.8 built the internal machinery:

- CTL-resident active commitments
- runtime active recovery
- recovery proposal packages
- Temporal-safe active recovery boundary

R5.0 exposes that machinery through stable application-facing APIs so product code does not need to import internal CTL, recovery, runtime, or package modules directly.

## Product API modules

R5.0 adds:

    mnemosyne/api/commitments.py
    mnemosyne/api/recovery.py
    mnemosyne/api/proposal_packages.py
    mnemosyne/api/audit.py

The public package export is:

    mnemosyne.api

## Commitment API

Representative functions:

    register_active_commitment(...)
    fire_active_commitment(...)
    discharge_active_commitment(...)
    admit_active_commitment(...)
    reject_active_commitment(...)
    load_active_commitments(...)
    list_live_active_commitments(...)
    list_live_active_commitment_ids(...)
    get_active_commitment_status(...)

Core invariant:

    The commitment API commits only commitment-FSM records.
    It does not create or commit domain repair records.

## Recovery API

Representative functions:

    plan_active_recovery(...)
    validate_and_commit_active_recovery(...)

Core invariant:

    The recovery API may update commitment state.
    It may not mutate domain state directly.
    Domain repair still requires a separate domain CTL admission path.

## Proposal package API

Representative functions:

    create_recovery_proposal_package(...)
    validate_recovery_proposal_package(...)
    make_package_backed_proposal_candidate(...)
    emit_package_backed_proposal(...)
    package_to_reference(...)
    package_to_dict(...)
    package_from_dict(...)
    package_event_payload(...)
    package_reference_from_event_payload(...)

Core invariant:

    A package-backed proposal commits only a commitment-FSM proposal record.
    The package's proposed domain candidates are not domain truth.

## Audit API

Representative functions:

    audit_active_commitments(...)
    list_unresolved_commitments(...)
    audit_commitment_lineage(...)
    audit_recovery_lineage(...)

Representative report rows:

    ActiveCommitmentAuditRow
    CommitmentLineageRow
    RecoveryLineageRow
    UnresolvedCommitmentReport

Core invariant:

    Audit APIs are read-only.
    They do not validate, commit, mutate CTL, mutate StateView, or execute recovery.

## Demo

R5.0 adds:

    examples/r50_product_api_audit_demo.py

The demo exercises:

1. product-facing commitment registration
2. product-facing commitment firing
3. product-facing active recovery execution
4. product-facing recovery proposal package emission
5. active commitment audit
6. unresolved commitment report
7. recovery lineage audit

The demo confirms that recovery and proposal package paths commit only commitment-FSM records and do not commit inert domain repair candidates.

## Tests

R5.0 adds product-facing tests for:

    tests/core/test_api_commitments.py
    tests/core/test_api_recovery.py
    tests/core/test_api_proposal_packages.py
    tests/core/test_api_audit.py
    tests/core/test_r50_product_api_audit_demo.py

Current full suite:

    198 passed, 24 skipped

## Architectural position

R5.0 does not replace the CTL/store source-of-truth contract.

The architecture remains:

    CommitBatch -> Validator -> Store -> CTL -> StateView

R5.0 adds a product-facing API layer above existing internal machinery.

The new boundary is:

    Application code -> mnemosyne.api -> Validator / Store / CTL / StateView

Product code should prefer the API layer instead of importing internal modules directly.

## Source-of-truth rule

R5.0 preserves the central Mnemosyne rule:

    CTL/store owns committed truth.
    StateView owns effective projected truth.
    Recovery may propose.
    Packages may describe.
    Solvers may certify.
    Temporal may orchestrate.
    Only admitted CTL records become truth.

## Next recommended milestone

Proceed to:

    R5.1 product reporting and CLI surface

Recommended next work:

1. Add CLI wrappers for product API operations.
2. Add Markdown/JSON audit report generation.
3. Add unresolved commitment report export.
4. Add recovery lineage report export.
5. Add product-level examples for application integration.
6. Add documentation for API stability and intended public imports.
