# REALM J1-J4 JSSP Readiness Report

## Summary

- Case count: 4
- Available cases: 4
- Ready cases: 4
- Module count: 8
- Available modules: 8
- Readiness decision: `ready_for_executable_j1_j4_baselines`

## Case Files

| Case | Exists | Expected role | Ready for baseline | Path |
|---|---:|---|---:|---|
| J1 | True | static_schedule_feasibility | True | `benchmarks/realm/cases/j1_jssp_simple_static.json` |
| J2 | True | dynamic_disruption_recovery | True | `benchmarks/realm/cases/j2_jssp_simple_dynamic.json` |
| J3 | True | static_schedule_feasibility | True | `benchmarks/realm/cases/j3_jssp_complex_static.json` |
| J4 | True | dynamic_disruption_recovery | True | `benchmarks/realm/cases/j4_jssp_complex_dynamic.json` |

## Case Field Inspection

### J1

- Top-level keys: `['case_id', 'constraints', 'description', 'disruptions', 'entities', 'family', 'metrics', 'mode', 'name', 'objective', 'short_name', 'source_table', 'tier']`
- Inferred static: True
- Inferred dynamic: False
- Mentions JSSP: True
- Mentions disruption: True
- Mentions repair: False

### J2

- Top-level keys: `['case_id', 'constraints', 'description', 'disruptions', 'entities', 'extends', 'family', 'metrics', 'mode', 'name', 'objective', 'short_name', 'source_table', 'tier']`
- Inferred static: False
- Inferred dynamic: True
- Mentions JSSP: True
- Mentions disruption: True
- Mentions repair: False

### J3

- Top-level keys: `['case_id', 'constraints', 'description', 'disruptions', 'entities', 'family', 'metrics', 'mode', 'name', 'objective', 'short_name', 'source_table', 'tier']`
- Inferred static: True
- Inferred dynamic: False
- Mentions JSSP: True
- Mentions disruption: True
- Mentions repair: False

### J4

- Top-level keys: `['case_id', 'constraints', 'description', 'disruptions', 'entities', 'extends', 'family', 'metrics', 'mode', 'name', 'objective', 'short_name', 'source_table', 'tier']`
- Inferred static: False
- Inferred dynamic: True
- Mentions JSSP: True
- Mentions disruption: True
- Mentions repair: False

## JSSP Substrate Modules

### `mnemosyne.benchmarks.jssp_disruptions`

- Available: True
- Relevant public callables: 8

| Callable | Kind | Signature |
|---|---|---|
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPOperation` | type | `(job_id: 'str', operation_id: 'str', machine_id: 'str', duration: 'int', sequence_index: 'int') -> None` |
| `JSSPScheduleViolation` | type | `(violation_type: 'str', message: 'str', operation_keys: 'tuple[str, ...]') -> None` |
| `JSSPScheduledOperation` | type | `(operation: 'JSSPOperation', start: 'int', end: 'int') -> None` |
| `commitment_id_for_operation` | function | `(*, case_id: 'str', operation: 'JSSPScheduledOperation') -> 'str'` |
| `make_jssp_3x3_baseline_schedule` | function | `(*, case_id: 'str' = 'jssp-3x3-smoke') -> 'JSSPBaselineSchedule'` |
| `schedule_entity_id` | function | `(case_id: 'str', operation_key: 'str') -> 'str'` |
| `validate_baseline_schedule` | function | `(schedule: 'JSSPBaselineSchedule') -> 'list[JSSPScheduleViolation]'` |

### `mnemosyne.benchmarks.jssp_schedule_admission`

- Available: True
- Relevant public callables: 11

| Callable | Kind | Signature |
|---|---|---|
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPBaselineScheduleAdmission` | type | `(schedule: 'JSSPBaselineSchedule', batch: 'CommitBatch', schedule_violations: 'list[JSSPScheduleViolation]', validation: 'ValidationResult | None', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `JSSPScheduleViolation` | type | `(violation_type: 'str', message: 'str', operation_keys: 'tuple[str, ...]') -> None` |
| `JSSPScheduledOperation` | type | `(operation: 'JSSPOperation', start: 'int', end: 'int') -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `admit_baseline_schedule` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', schedule: 'JSSPBaselineSchedule', workflow_id: 'str | None' = None, tx_group_id: 'str | None' = None, batch_id: 'str | None' = None, binding_id: 'str | None' = None) -> 'JSSPBaselineScheduleAdmission'` |
| `baseline_schedule_candidates` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', binding_id: 'str | None' = None) -> 'list[TransitionCandidate]'` |
| `baseline_schedule_commit_batch` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', batch_id: 'str | None' = None, binding_id: 'str | None' = None) -> 'CommitBatch'` |
| `schedule_entity_id` | function | `(case_id: 'str', operation_key: 'str') -> 'str'` |
| `schedule_operation_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', case_id: 'str', scheduled_operation: 'JSSPScheduledOperation', binding_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None) -> 'TransitionCandidate'` |
| `validate_baseline_schedule` | function | `(schedule: 'JSSPBaselineSchedule') -> 'list[JSSPScheduleViolation]'` |

### `mnemosyne.benchmarks.jssp_disruption_commitments`

- Available: True
- Relevant public callables: 13

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPCommitmentFireResult` | type | `(commitment_id: 'str', operation_key: 'str', disrupted_operation: 'DisruptedOperation', result: 'CommitmentApiResult') -> None` |
| `JSSPCommitmentRegistrationResult` | type | `(commitment_id: 'str', operation_key: 'str', result: 'CommitmentApiResult') -> None` |
| `JSSPDisruptionSignalResult` | type | `(disruption: 'MachineBreakdown', affected: 'list[DisruptedOperation]', fired: 'list[JSSPCommitmentFireResult]') -> None` |
| `active_commitment_for_scheduled_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', scheduled_operation: 'Any') -> 'ActiveCommitment'` |
| `active_commitment_statuses` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str', commitment_ids: 'list[str]') -> 'dict[str, str | None]'` |
| `commitment_id_for_operation` | function | `(*, case_id: 'str', operation: 'JSSPScheduledOperation') -> 'str'` |
| `fire_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'trigger_true', validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `get_active_commitment_status` | function | `(*, store: 'Any', tenant_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None) -> 'CommitmentStatus | None'` |
| `register_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment: 'ActiveCommitment', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `register_schedule_commitments` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'list[JSSPCommitmentRegistrationResult]'` |

### `mnemosyne.benchmarks.jssp_recovery_proposals`

- Available: True
- Relevant public callables: 15

| Callable | Kind | Signature |
|---|---|---|
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPDisruptionSignalResult` | type | `(disruption: 'MachineBreakdown', affected: 'list[DisruptedOperation]', fired: 'list[JSSPCommitmentFireResult]') -> None` |
| `JSSPRecoveryProposal` | type | `(operation_key: 'str', commitment_id: 'str', proposal_ref: 'str', package_id: 'str', proposal_scope: 'dict[str, Any]', package: 'Any', result: 'ProposalPackageApiResult') -> None` |
| `JSSPRecoveryProposalBatch` | type | `(schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', proposals: 'list[JSSPRecoveryProposal]') -> None` |
| `JSSPScheduledOperation` | type | `(operation: 'JSSPOperation', start: 'int', end: 'int') -> None` |
| `ProposalPackageApiResult` | type | `(package: 'RecoveryProposalPackage', candidate: 'TransitionCandidate', commitment_result: 'CommitmentApiResult') -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `active_commitment_for_scheduled_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', scheduled_operation: 'Any') -> 'ActiveCommitment'` |
| `create_recovery_proposal_package` | function | `(*, package_id: 'str | None' = None, commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate] | None' = None, rationale: 'str | None' = None, validator_context: 'dict[str, Any] | None' = None, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> 'RecoveryProposalPackage'` |
| `emit_package_backed_proposal` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, validator: 'Any | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'ProposalPackageApiResult'` |
| `emit_recovery_proposals_for_disruption` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption_signal: 'JSSPDisruptionSignalResult', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'JSSPRecoveryProposalBatch'` |
| `proposal_scope_for_disrupted_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation') -> 'dict[str, Any]'` |
| `recovery_package_for_disrupted_operation` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', created_from_record_id: 'str', candidate_start: 'int | None' = None, created_by: 'str' = 'jssp_recovery_proposal_adapter') -> 'Any'` |
| `repair_candidate_for_disrupted_operation` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', candidate_start: 'int | None' = None) -> 'TransitionCandidate'` |
| `repair_details_for_disrupted_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', candidate_start: 'int | None' = None) -> 'dict[str, Any]'` |

### `mnemosyne.benchmarks.jssp_repair_admission`

- Available: True
- Relevant public callables: 11

| Callable | Kind | Signature |
|---|---|---|
| `JSSPFinalizedRepairCommitment` | type | `(operation_key: 'str', commitment_id: 'str', admitted_record_ids: 'list[str]', result: 'Any') -> None` |
| `JSSPRecoveryProposalBatch` | type | `(schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', proposals: 'list[JSSPRecoveryProposal]') -> None` |
| `JSSPRepairCommitmentFinalization` | type | `(finalized: 'list[JSSPFinalizedRepairCommitment]') -> None` |
| `JSSPSelectedRepairAdmission` | type | `(selected_candidates: 'list[TransitionCandidate]', batch: 'CommitBatch', validation: 'ValidationResult | None', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `admit_and_finalize_repair_candidates_from_proposal_batch` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', repair_tx_group_id: 'str', finalize_tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', operation_keys: 'list[str] | None' = None, repair_batch_id: 'str | None' = None) -> 'tuple[JSSPSelectedRepairAdmission, JSSPRepairCommitmentFinalization]'` |
| `admit_repair_candidates_from_proposal_batch` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', operation_keys: 'list[str] | None' = None, batch_id: 'str | None' = None) -> 'JSSPSelectedRepairAdmission'` |
| `admit_selected_repair_candidates` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', selected_candidates: 'list[TransitionCandidate]', batch_id: 'str | None' = None) -> 'JSSPSelectedRepairAdmission'` |
| `finalize_commitments_for_repair_admission` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', repair_admission: 'JSSPSelectedRepairAdmission', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'JSSPRepairCommitmentFinalization'` |
| `repair_candidates_from_proposal_batch` | function | `(proposal_batch: 'JSSPRecoveryProposalBatch', *, operation_keys: 'list[str] | None' = None) -> 'list[TransitionCandidate]'` |
| `selected_repair_commit_batch` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', selected_candidates: 'list[TransitionCandidate]', batch_id: 'str | None' = None) -> 'CommitBatch'` |

### `mnemosyne.api.commitments`

- Available: True
- Relevant public callables: 23

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `ActiveCommitmentIndex` | type | `(projection: 'CommitmentProjection') -> None` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `CommitmentStatus` | EnumType | `(*values)` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `active_commitment_index_from_store` | function | `(store, *, tenant_id: 'str', workflow_id: 'str | None' = None) -> 'ActiveCommitmentIndex'` |
| `admit_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', admitted_record_ids: 'list[str]', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `build_commitment_fsm_registry` | function | `() -> 'FSMRegistry'` |
| `commit_commitment_candidate` | function | `(*, store: 'Any', candidate: 'TransitionCandidate', validator: 'Validator | None' = None, batch_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `default_commitment_validator` | function | `() -> 'Validator'` |
| `discharge_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'obligation_satisfied', validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `fire_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'trigger_true', validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `get_active_commitment_status` | function | `(*, store: 'Any', tenant_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None) -> 'CommitmentStatus | None'` |
| `list_live_active_commitment_ids` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'list[str]'` |
| `list_live_active_commitments` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'list[ActiveCommitment]'` |
| `load_active_commitments` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'ActiveCommitmentIndex'` |
| `make_commitment_admitted_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', admitted_record_ids: 'list[str]', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_commitment_rejected_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', rejection_code: 'str', rejection_evidence: 'dict | None' = None, state_before: 'str | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_discharge_commitment_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'obligation_satisfied', rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_fire_commitment_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'trigger_true', rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_register_commitment_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', commitment: 'ActiveCommitment', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None) -> 'TransitionCandidate'` |
| `register_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment: 'ActiveCommitment', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `reject_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', rejection_code: 'str', rejection_evidence: 'dict | None' = None, state_before: 'str | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |

### `mnemosyne.api.proposal_packages`

- Available: True
- Relevant public callables: 19

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `ProposalPackageApiResult` | type | `(package: 'RecoveryProposalPackage', candidate: 'TransitionCandidate', commitment_result: 'CommitmentApiResult') -> None` |
| `RecoveryProposalPackage` | type | `(package_id: 'str', commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate]' = <factory>, rationale: 'str | None' = None, validator_context: 'dict[str, Any]' = <factory>, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `commit_commitment_candidate` | function | `(*, store: 'Any', candidate: 'TransitionCandidate', validator: 'Validator | None' = None, batch_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `create_recovery_proposal_package` | function | `(*, package_id: 'str | None' = None, commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate] | None' = None, rationale: 'str | None' = None, validator_context: 'dict[str, Any] | None' = None, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> 'RecoveryProposalPackage'` |
| `default_commitment_validator` | function | `() -> 'Validator'` |
| `emit_package_backed_proposal` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, validator: 'Any | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'ProposalPackageApiResult'` |
| `make_package_backed_proposal_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_package_proposal_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', dependency_scope: 'dict | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `proposal_package_contains_only_domain_candidates` | function | `(package: 'RecoveryProposalPackage', *, commitment_fsm: 'str' = 'mnemosyne.commitment') -> 'bool'` |
| `proposal_package_event_payload` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_package_from_dict` | function | `(data: 'dict[str, Any]') -> 'RecoveryProposalPackage'` |
| `proposal_package_reference_from_event_payload` | function | `(payload: 'dict[str, Any]') -> 'dict[str, Any] | None'` |
| `proposal_package_reference_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_package_scope_is_within` | function | `(package: 'RecoveryProposalPackage', dependency_scope: 'dict[str, Any]') -> 'bool'` |
| `proposal_package_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `validate_recovery_proposal_package` | function | `(*, package: 'RecoveryProposalPackage', dependency_scope: 'dict[str, Any] | None' = None) -> 'None'` |

### `mnemosyne.api.audit`

- Available: True
- Relevant public callables: 14

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `ActiveCommitmentAuditRow` | type | `(commitment_id: 'str', commitment_type: 'str', status: 'str', is_unresolved: 'bool', description: 'str', dependency_scope: 'dict[str, Any]', workflow_id: 'str | None', record_count: 'int', first_record_id: 'str | None', last_record_id: 'str | None', last_action_type: 'str | None', last_log_position: 'int | None') -> None` |
| `CommitmentEventType` | EnumType | `(*values)` |
| `CommitmentLineageRow` | type | `(commitment_id: 'str', record_id: 'str', action_type: 'str', status_before: 'str', status_after: 'str', payload: 'dict[str, Any]' = <factory>, workflow_id: 'str | None' = None, tx_group_id: 'str | None' = None, log_position: 'int | None' = None, local_log_position: 'int | None' = None, timestamp: 'datetime | None' = None) -> None` |
| `CommitmentStatus` | EnumType | `(*values)` |
| `RecoveryLineageRow` | type | `(commitment_id: 'str', record_id: 'str', action_type: 'str', status_before: 'str', status_after: 'str', proposal_ref: 'str | None' = None, package_id: 'str | None' = None, admitted_record_ids: 'list[str]' = <factory>, rejection_code: 'str | None' = None, payload: 'dict[str, Any]' = <factory>, workflow_id: 'str | None' = None, tx_group_id: 'str | None' = None, log_position: 'int | None' = None, timestamp: 'datetime | None' = None) -> None` |
| `UnresolvedCommitmentReport` | type | `(tenant_id: 'str', workflow_id: 'str | None', rows: 'list[ActiveCommitmentAuditRow]') -> None` |
| `active_commitment_index_from_store` | function | `(store, *, tenant_id: 'str', workflow_id: 'str | None' = None) -> 'ActiveCommitmentIndex'` |
| `audit_active_commitments` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'list[ActiveCommitmentAuditRow]'` |
| `audit_commitment_lineage` | function | `(*, store: 'Any', tenant_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None) -> 'list[CommitmentLineageRow]'` |
| `audit_recovery_lineage` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None, commitment_id: 'str | None' = None) -> 'list[RecoveryLineageRow]'` |
| `commitment_entity_id` | function | `(commitment_id: 'str') -> 'str'` |
| `list_unresolved_commitments` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'UnresolvedCommitmentReport'` |
| `proposal_package_reference_from_event_payload` | function | `(payload: 'dict[str, Any]') -> 'dict[str, Any] | None'` |

## Recommended Next Steps

- Build J1/J3 static executable schedule baselines first.
- Build J2/J4 dynamic disruption baselines second.
- Bind J2/J4 recovery to Mnemosyne JSSP APIs only after the executable baselines are reproducible.
- Continue to describe R6.8 recovery as benchmark-local, not production-runtime durable recovery.

## Non-goals

- Do not claim durable production recovery in R6.8.
- Do not introduce distributed runtime dependencies in R6.8.
- Do not skip static J1/J3 baselines before dynamic J2/J4 recovery.

