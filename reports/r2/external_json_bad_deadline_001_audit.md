# R2.6B External JSON Bad Deadline Audit

## Summary

- total rows: `1`
- ok rows: `0`
- failed rows: `1`
- rows with committed records: `0`
- rejected before commit: `1`

### By classification

- solver_failure: `1`

### By error code

- SOLVER_FAILED: `1`

## Case 1: `p1_external_bad_deadline_001`

- classification: `solver_failure`
- ok: `false`
- committed_rids: `[]`
- error_codes: `SOLVER_FAILED`
- error_message: `external JSON solution failed adapter checks`
- source_case_path: `benchmarks/realm/p1_external/campus_tour_external_bad_deadline_001.json`

### Observed outcome

- committed: `false`

### Solver certificate

- solver_id: `external_json_solver`
- solver_version: `0.1`
- solver_run_id: `run:external_json_solver:p1_external_bad_deadline_001`
- problem_family: `p1_campus_tour`
- problem_id: `p1_external_bad_deadline_001`
- feasible: `false`
- optimality_status: `external_claim`
- objective_name: `minimize_total_minutes`
- objective_value: `190`

Solver metrics:

- finish_time: `12:10`
- note: `R2.6B expected-negative external proposal fixture`
- route_length: `6`
- source: `fixture`
- total_minutes: `190`

Solver violations:

- `external solution finishes after deadline: finish_time=12:10, deadline=11:00`

### Interpretation

This row represents a failed or rejected run. Inspect the error codes and details above.
