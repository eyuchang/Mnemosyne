# R2.5 Stale-World Repair Audit

## Summary

- total rows: `1`
- ok rows: `1`
- failed rows: `0`
- rows with committed records: `1`
- rejected before commit: `0`

### By classification

- committed_or_expected_success: `1`

### By error code

- none

## Case 1: `local-p1-compatible-campus-tour-solver-001`

- classification: `committed_or_expected_success`
- ok: `true`
- committed_rids: `["realm-local-p1-compatible-campus-tour-solver-001-visit_dorm", "realm-local-p1-compatible-campus-tour-solver-001-visit_auditorium", "realm-local-p1-compatible-campus-tour-solver-001-visit_lab", "realm-local-p1-compatible-campus-tour-solver-001-visit_library", "realm-local-p1-compatible-campus-tour-solver-001-return_to_student_center"]`
- source_case_path: `benchmarks/realm/p1_solver/campus_tour_solver_001.json`

### Observed outcome

- committed: `true`
- committed_rids: `["realm-local-p1-compatible-campus-tour-solver-001-visit_dorm", "realm-local-p1-compatible-campus-tour-solver-001-visit_auditorium", "realm-local-p1-compatible-campus-tour-solver-001-visit_lab", "realm-local-p1-compatible-campus-tour-solver-001-visit_library", "realm-local-p1-compatible-campus-tour-solver-001-return_to_student_center"]`
- prevalidation_ok: `true`
