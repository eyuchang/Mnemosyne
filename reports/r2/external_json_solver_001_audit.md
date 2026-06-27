# R2.6 External JSON Solver Audit

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

## Case 1: `p1_external_campus_tour_001`

- classification: `committed_or_expected_success`
- ok: `true`
- committed_rids: `["realm-p1_external_campus_tour_001-visit_dorm", "realm-p1_external_campus_tour_001-visit_auditorium", "realm-p1_external_campus_tour_001-visit_lab", "realm-p1_external_campus_tour_001-visit_library", "realm-p1_external_campus_tour_001-return_to_student_center"]`
- source_case_path: `benchmarks/realm/p1_external/campus_tour_external_001.json`

### Observed outcome

- committed: `true`
- committed_rids: `["realm-p1_external_campus_tour_001-visit_dorm", "realm-p1_external_campus_tour_001-visit_auditorium", "realm-p1_external_campus_tour_001-visit_lab", "realm-p1_external_campus_tour_001-visit_library", "realm-p1_external_campus_tour_001-return_to_student_center"]`
- prevalidation_ok: `true`
