# R5.1 Product Reporting and CLI Surface

## Status

R5.1 adds product-facing report rendering, report export, and CLI support over the R5.0 audit API.

Current validation:

    210 passed, 24 skipped

## Purpose

R5.0 exposed the product API:

- commitments
- recovery
- proposal packages
- audit and lineage

R5.1 turns those API results into reusable product reports.

The reporting path is:

    mnemosyne.api.audit -> mnemosyne.api.reports -> Markdown / JSON / CLI

## Added modules

R5.1 adds:

    mnemosyne/api/reports.py
    mnemosyne/cli/product_reports.py
    mnemosyne/cli/__init__.py

## Product report rendering

The report renderer supports:

- active commitment audit rows
- unresolved commitment reports
- commitment lineage rows
- recovery lineage rows

Representative functions:

    render_active_commitment_audit_markdown(...)
    render_unresolved_commitments_markdown(...)
    render_commitment_lineage_markdown(...)
    render_recovery_lineage_markdown(...)
    write_json_report(...)
    write_markdown_report(...)
    to_jsonable(...)

## Product report CLI

R5.1 adds a deterministic CLI renderer:

    python -m mnemosyne.cli.product_reports

Supported report kinds:

    active-commitments
    unresolved
    commitment-lineage
    recovery-lineage

Supported output formats:

    markdown
    json

The CLI renders already-exported product audit JSON. It does not mutate store state.

## Product report export demo

R5.1 adds:

    examples/r51_product_report_export_demo.py

The demo exercises the full reporting path:

1. register a commitment
2. fire the commitment
3. emit a package-backed recovery proposal
4. audit active commitments
5. audit unresolved commitments
6. audit commitment lineage
7. audit recovery lineage
8. export JSON reports
9. export Markdown reports

Generated report files include:

    active_commitments.json
    active_commitments.md
    unresolved_commitments.json
    unresolved_commitments.md
    commitment_lineage.json
    commitment_lineage.md
    recovery_lineage.json
    recovery_lineage.md

## Tests

R5.1 adds tests for:

    tests/core/test_api_reports.py
    tests/core/test_cli_product_reports.py
    tests/core/test_r51_product_report_export_demo.py

Current full suite:

    210 passed, 24 skipped

## Architectural rule

R5.1 is read/report/export only.

It does not change the source-of-truth contract:

    CTL/store owns committed truth.
    StateView owns effective projected truth.
    Recovery may propose.
    Packages may describe.
    Reports may render.
    CLI may export.
    Only admitted CTL records become truth.

## Next recommended milestone

Proceed to:

    R6.0 disruptive planning benchmark layer

Recommended initial target:

    JSSP disruptive planning smoke tests

First scenario:

1. create a small 3x3 JSSP baseline schedule
2. admit baseline schedule records
3. register commitments for machine/order/due-date constraints
4. inject a machine-breakdown event
5. fire affected commitments
6. generate recovery proposal packages
7. audit unresolved commitments
8. audit recovery lineage
9. verify no domain schedule mutation occurs until separate domain admission
