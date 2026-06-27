# R2 Rejection Audit Fixture Report

## Summary

- total rows: `2`
- ok rows: `0`
- failed rows: `2`
- rows with committed records: `0`
- rejected before commit: `2`

### By classification

- proposal_conflict_rejection: `1`
- stale_world_rejection: `1`

### By error code

- ENTITY_PROPOSAL_CONFLICT: `1`
- SOLVER_PROPOSAL_CONFLICT: `1`
- STALE_WORLD_FACT: `1`
- STALE_WORLD_RECONCILIATION: `1`

## Case 1: `r2-conflict-fixture`

- classification: `proposal_conflict_rejection`
- ok: `false`
- committed_rids: `[]`
- error_codes: `SOLVER_PROPOSAL_CONFLICT, ENTITY_PROPOSAL_CONFLICT`
- error_message: `solver proposal conflict detected before commit`
- source_case_path: `fixtures/r2/conflict.json`

### Observed outcome

- committed: `false`

### Solver certificate

- solver_id: `p1_campus_tour_bruteforce`
- solver_version: `0.1`
- feasible: `true`
- objective_name: `minimize_total_minutes`
- objective_value: `190`

### Plan proposal

- proposal_id: `proposal:r2-conflict`
- case_id: `r2-conflict-fixture`
- tenant_id: `tenant:test`
- workflow_id: `workflow:test`
- entity_id: `entity:shared`
- app_id: `campus_tour`
- schema_id: `campus_tour.transition`
- route: `S -> D -> A -> B -> L -> S`
- step_count: `0`

Proposal attributes:

- deadline: `17:00`
- total_minutes: `190`

### Proposal conflict analysis

- conflict_free: `false`

Conflicts:

- ENTITY_PROPOSAL_CONFLICT: scope=`tenant:tenant:test/entity:entity:shared`, left=`proposal:a`, right=`proposal:b`, message=`two different active proposals target the same entity`

### Interpretation

This proposal set was rejected before commit because active proposals conflicted.
No committed records should appear for this case.

## Case 2: `r2-stale-world-fixture`

- classification: `stale_world_rejection`
- ok: `false`
- committed_rids: `[]`
- error_codes: `STALE_WORLD_RECONCILIATION, STALE_WORLD_FACT`
- error_message: `world reconciliation failed before commit`
- source_case_path: `fixtures/r2/stale_world.json`

### Observed outcome

- committed: `false`

### Solver certificate

- solver_id: `p1_campus_tour_bruteforce`
- solver_version: `0.1`
- feasible: `true`

### Plan proposal

- proposal_id: `proposal:r2-stale`
- case_id: `r2-stale-world-fixture`
- tenant_id: `tenant:test`
- workflow_id: `workflow:test`
- entity_id: `entity:test`
- app_id: `campus_tour`
- schema_id: `campus_tour.transition`
- route: `S -> D -> A -> B -> L -> S`
- step_count: `0`

Proposal attributes:

- deadline: `17:00`

World assumptions:

- `{"key": "deadline", "source": "p1_campus_tour_solver", "value": "17:00"}`

### World reconciliation

- world_reconciled: `false`

Issues:

- STALE_WORLD_FACT: entity=`entity:test`, key=`deadline`, expected=`17:00`, observed=`11:00`, message=`observed world fact differs from proposal assumption`

### Interpretation

This proposal was rejected before commit because its world assumptions disagreed with observed facts.
No committed records should appear for this case.
