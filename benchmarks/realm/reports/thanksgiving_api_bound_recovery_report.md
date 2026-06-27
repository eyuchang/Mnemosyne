# Thanksgiving P9 API-Bound Recovery Report

## Summary

- Case: P9
- Tenant: `realm-thanksgiving`
- Workflow: `p9-thanksgiving-api-bound`
- Registered commitments: 4
- Fired commitments: 2
- Proposal packages: 1
- Admitted repairs: 1
- Feasible after repair: True

## Disruption

- Person: James
- Notice time: 10:00
- Original arrival: 13:00
- New arrival: 16:00
- Delay minutes: 180

## Real Mnemosyne API Calls

- `SQLiteStore`
- `register_active_commitment`
- `fire_active_commitment`
- `create_recovery_proposal_package`
- `emit_package_backed_proposal`
- `admit_active_commitment`
- `get_active_commitment_status`
- `audit_active_commitments`
- `audit_commitment_lineage`
- `audit_recovery_lineage`
- `list_unresolved_commitments`

## Commitment Statuses

- `p9-cook-turkey-supervision`: live
- `p9-pickup-emily`: live
- `p9-pickup-grandma-by-james`: admitted
- `p9-dinner-ready-by-1800`: fired

## Proposal Package

- Package id: `p9-package-reassign-grandma-to-sarah`
- Commitment id: `p9-pickup-grandma-by-james`
- Proposal ref: `repair:grandma-pickup-james-to-sarah`
- Rationale: James now lands at 16:00; Grandma pickup is reassigned to Sarah.

## Audit Summary

- Active commitment audit rows: 4
- Grandma commitment lineage rows: 4
- Recovery lineage rows: 2
- Unresolved commitments: 3

## Result

- The affected Grandma pickup commitment is registered through the real commitment API.
- The disruption fires the commitment through the real commitment API.
- The repair package is emitted through the real proposal package API.
- The selected repair is admitted through the real commitment admission API.
- Audit rows are read back through the real audit API.

## Limitation

- This still uses a local SQLiteStore and a deterministic Thanksgiving repair plan.
- It binds the benchmark to real Mnemosyne APIs, but not yet to a durable production runtime.

