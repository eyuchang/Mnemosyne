# R2.7B Skeleton Family Report

## Summary

- total rows: `6`
- ok rows: `3`
- failed rows: `3`
- rows with committed records: `0`
- rejected before commit: `6`

### By classification

- committed_or_expected_success: `3`
- validation_or_runtime_rejection: `3`

### By error code

- EXPECTED_NEGATIVE_SKELETON: `3`

## Case 1: `p2_multi_group_tour_001`

- classification: `committed_or_expected_success`
- ok: `true`
- committed_rids: `[]`
- source_case_path: `benchmarks/realm/p2_skeleton/multi_group_tour_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

## Case 2: `p2_multi_group_tour_expected_negative_001`

- classification: `validation_or_runtime_rejection`
- ok: `false`
- committed_rids: `[]`
- error_codes: `EXPECTED_NEGATIVE_SKELETON`
- error_message: `expected-negative skeleton fixture`
- source_case_path: `benchmarks/realm/p2_skeleton/multi_group_tour_expected_negative_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

### Interpretation

This row represents a failed or rejected run. Inspect the error codes and details above.

## Case 3: `p3_urban_rideshare_001`

- classification: `committed_or_expected_success`
- ok: `true`
- committed_rids: `[]`
- source_case_path: `benchmarks/realm/p3_skeleton/urban_rideshare_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

## Case 4: `p3_urban_rideshare_expected_negative_001`

- classification: `validation_or_runtime_rejection`
- ok: `false`
- committed_rids: `[]`
- error_codes: `EXPECTED_NEGATIVE_SKELETON`
- error_message: `expected-negative skeleton fixture`
- source_case_path: `benchmarks/realm/p3_skeleton/urban_rideshare_expected_negative_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

### Interpretation

This row represents a failed or rejected run. Inspect the error codes and details above.

## Case 5: `p5_event_logistics_001`

- classification: `committed_or_expected_success`
- ok: `true`
- committed_rids: `[]`
- source_case_path: `benchmarks/realm/p5_skeleton/event_logistics_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

## Case 6: `p5_event_logistics_expected_negative_001`

- classification: `validation_or_runtime_rejection`
- ok: `false`
- committed_rids: `[]`
- error_codes: `EXPECTED_NEGATIVE_SKELETON`
- error_message: `expected-negative skeleton fixture`
- source_case_path: `benchmarks/realm/p5_skeleton/event_logistics_expected_negative_001.json`

### Observed outcome

- committed: `false`
- report_only: `true`

### Interpretation

This row represents a failed or rejected run. Inspect the error codes and details above.
