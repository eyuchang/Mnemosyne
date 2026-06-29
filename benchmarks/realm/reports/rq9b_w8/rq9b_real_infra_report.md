# RQ9b Real Infrastructure Runtime-Cost Report

This run benchmarks real pytest infrastructure paths, not the RQ9 ATP oracle.

## Summary

| Condition | Passed/Runs | Unit Count/Run | End-to-End p50/p95 ms | Admission p50/p95 ms | Commit p50/p95 ms | Projection p50/p95 ms | Validation p50/p95 ms | Projection+Validation Overhead | Throughput units/min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| workflow_saga_semantic_comparator | 30/30 | 1 | 6347.136/6572.290 | 0.129/0.217 | NA/NA | 0.087/7.224 | 0.037/0.094 | 3.33% | 74.59 |
| atp_real_infrastructure | 30/30 | 20 | 12500.800/12646.592 | 0.102/37.686 | 5.154/13.313 | 0.030/3.667 | 0.001/0.097 | 9.62% | 768.35 |

## Workloads

### Semantic workflow/saga comparator

- `tests/experiments/test_rq9_state_of_practice_comparator.py::test_rq9_state_of_practice_comparator`

### ATP real infrastructure workload

- `tests/runtime/test_kernel_admission.py::test_accept_via_kernel_records_accepted_and_committed`
- `tests/runtime/test_kernel_admission.py::test_reject_before_commit_never_calls_kernel`
- `tests/runtime/test_kernel_admission.py::test_validator_rejection_records_rejected_without_committed_rids`
- `tests/runtime/test_kernel_admission.py::test_commit_failure_records_rejected_without_committed_truth`
- `tests/runtime/test_runtime_admission.py::test_admission_facade_accepts_submitted_proposal_with_commit_rids`
- `tests/runtime/test_runtime_admission.py::test_admission_facade_rejects_submitted_proposal`
- `tests/core/test_cross_entity_compensation_projection.py::test_cross_entity_compensation_refreshes_compensated_entity_projection`
- `tests/core/test_compensation_projection.py::test_compensation_preserves_ctl_history_but_updates_effective_projection`
- `tests/core/test_compensation_projection.py::test_supersession_preserves_ctl_history_but_updates_effective_projection`
- `tests/core/test_state_view_api.py::test_get_state_view_uses_only_effective_records_after_compensation`
- `tests/core/test_review_a_fixes.py::test_bl2_validator_rejects_orphaning_compensation`
- `tests/core/test_review_a_fixes.py::test_im5_validator_rejects_chain_breaking_compensation`
- `tests/core/test_review_a_fixes.py::test_compensation_target_must_exist`
- `tests/core/test_review_a_fixes.py::test_legitimate_tail_collapse_compensation_still_passes`
- `tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_commits_recovery_candidate_through_validator`
- `tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_sequentially_admits_retry_candidates`
- `tests/core/test_runtime_local_active_recovery_validation.py::test_validation_failure_commits_no_recovery_candidate`
- `tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_still_never_mutates_domain_state`
- `tests/core/test_temporal_activity_boundary.py::test_temporal_activity_boundary_validates_commits_and_returns_stateview`
- `tests/core/test_temporal_activity_boundary.py::test_temporal_runtime_orchestrates_but_activity_boundary_commits_truth`

## Interpretation guardrail

The semantic comparator workload preserves the RQ9 state-of-practice safety baseline. The ATP workload measures real repository infrastructure paths: admission, commit boundary, effective-state projection, validation, compensation, recovery, and Temporal boundary. If any pytest nodes fail, do not use the timing table until the failure is fixed.