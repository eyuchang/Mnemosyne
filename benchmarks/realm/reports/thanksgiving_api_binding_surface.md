# Thanksgiving API Binding Surface Report

## Summary

- Module count: 7
- Available modules: 7
- Public callables: 152

## Modules

### `mnemosyne.api.commitments`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `ActiveCommitmentIndex` | type | `(projection: 'CommitmentProjection') -> None` |
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CTLRecord` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', version: 'int', state_before: 'str', state_after: 'str', action_type: 'str', workflow_id: 'str | None', binding_id: 'str | None', triggers: 'list[str]', dependencies: 'list[str]', metadata: 'dict[str, Any]', extension: 'dict[str, Any]', app_id: 'str', app_version: 'str', schema_id: 'str', schema_version: 'str', fsm_version: 'str', timestamp: 'datetime', op_id: 'str | None' = None, policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, log_position: 'int | None' = None, local_log_position: 'int | None' = None) -> None` |
| `CommitBatch` | type | `(batch_id: 'str', tenant_id: 'str', workflow_id: 'str | None', tx_group_id: 'str', candidates: 'list[TransitionCandidate]', expected_versions: 'dict[tuple[str, str], int]' = <factory>, outbox_intents: 'list[OutboxIntent]' = <factory>, command_id: 'str | None' = None) -> None` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `CommitmentStatus` | EnumType | `(*values)` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `ValidationResult` | type | `(ok: 'bool', errors: 'list[ConstraintResult]' = <factory>, validator_id: 'str' = 'core.validator', validator_version: 'str' = '1.0') -> None` |
| `Validator` | type | `(fsm_registry: 'FSMRegistry', constraints: 'ConstraintRegistry | None' = None, schema_validator: 'SchemaValidator | None' = None, validator_id: 'str' = 'core.validator', validator_version: 'str' = '1.0') -> 'None'` |
| `active_commitment_index_from_store` | function | `(store, *, tenant_id: 'str', workflow_id: 'str | None' = None) -> 'ActiveCommitmentIndex'` |
| `admit_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', admitted_record_ids: 'list[str]', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `build_commitment_fsm_registry` | function | `() -> 'FSMRegistry'` |
| `commit_commitment_candidate` | function | `(*, store: 'Any', candidate: 'TransitionCandidate', validator: 'Validator | None' = None, batch_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
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
| `require_recovery_store` | function | `(store: 'T', *, required_methods: 'tuple[str, ...]' = ('get_record', 'get_entity_history', 'get_full_entity_history', 'get_state_view', 'get_by_op_id', 'commit_batch', 'append_recovery_event', 'list_recovery_events')) -> 'T'` |
| `uuid4` | function | `()` |

### `mnemosyne.api.recovery`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `ActiveRecoveryPlan` | type | `(candidates: 'list[TransitionCandidate]', loop_results: 'dict[str, RecoveryLoopResult]' = <factory>, skipped: 'dict[str, str]' = <factory>) -> None` |
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CTLRecord` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', version: 'int', state_before: 'str', state_after: 'str', action_type: 'str', workflow_id: 'str | None', binding_id: 'str | None', triggers: 'list[str]', dependencies: 'list[str]', metadata: 'dict[str, Any]', extension: 'dict[str, Any]', app_id: 'str', app_version: 'str', schema_id: 'str', schema_version: 'str', fsm_version: 'str', timestamp: 'datetime', op_id: 'str | None' = None, policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, log_position: 'int | None' = None, local_log_position: 'int | None' = None) -> None` |
| `LocalActiveRecoveryExecution` | type | `(plan: 'ActiveRecoveryPlan', records: 'list[CTLRecord]', committed: 'list[CTLRecord]', validation_results: 'list[ValidationResult]' = <factory>) -> None` |
| `LocalActiveRecoveryExecutor` | type | `(store: 'Any') -> 'None'` |
| `ProposalProvider` | _CallableGenericAlias | `(*args, **kwargs)` |
| `RecoveryApiExecution` | type | `(execution: 'LocalActiveRecoveryExecution') -> None` |
| `RecoveryContext` | type | `(commitment_id: 'str', depth: 'int' = 0, attempt_index: 'int' = 0, triggering_record_id: 'str | None' = None, triggering_error: 'str | None' = None, history: 'list[str]' = <factory>) -> None` |
| `RecoveryPolicy` | type | `(max_depth: 'int' = 2, max_attempts: 'int' = 3, require_scope_subset: 'bool' = True) -> None` |
| `ValidationResult` | type | `(ok: 'bool', errors: 'list[ConstraintResult]' = <factory>, validator_id: 'str' = 'core.validator', validator_version: 'str' = '1.0') -> None` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `default_commitment_validator` | function | `() -> 'Validator'` |
| `plan_active_recovery` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', proposal_provider: 'ProposalProvider', policy: 'RecoveryPolicy | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, contexts: 'dict[str, RecoveryContext] | None' = None) -> 'ActiveRecoveryPlan'` |
| `validate_and_commit_active_recovery` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', batch_id: 'str', proposal_provider: 'ProposalProvider', validator: 'Any | None' = None, policy: 'RecoveryPolicy | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, contexts: 'dict[str, RecoveryContext] | None' = None) -> 'RecoveryApiExecution'` |

### `mnemosyne.api.proposal_packages`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `ProposalPackageApiResult` | type | `(package: 'RecoveryProposalPackage', candidate: 'TransitionCandidate', commitment_result: 'CommitmentApiResult') -> None` |
| `RecoveryProposalPackage` | type | `(package_id: 'str', commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate]' = <factory>, rationale: 'str | None' = None, validator_context: 'dict[str, Any]' = <factory>, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `commit_commitment_candidate` | function | `(*, store: 'Any', candidate: 'TransitionCandidate', validator: 'Validator | None' = None, batch_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `create_recovery_proposal_package` | function | `(*, package_id: 'str | None' = None, commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate] | None' = None, rationale: 'str | None' = None, validator_context: 'dict[str, Any] | None' = None, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> 'RecoveryProposalPackage'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `default_commitment_validator` | function | `() -> 'Validator'` |
| `emit_package_backed_proposal` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, validator: 'Any | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'ProposalPackageApiResult'` |
| `make_package_backed_proposal_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `make_package_proposal_candidate` | function | `(*, tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', dependency_scope: 'dict | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'TransitionCandidate'` |
| `package_event_payload` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `package_from_dict` | function | `(data: 'dict[str, Any]') -> 'RecoveryProposalPackage'` |
| `package_reference_from_event_payload` | function | `(payload: 'dict[str, Any]') -> 'dict[str, Any] | None'` |
| `package_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `package_to_reference` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_package_contains_only_domain_candidates` | function | `(package: 'RecoveryProposalPackage', *, commitment_fsm: 'str' = 'mnemosyne.commitment') -> 'bool'` |
| `proposal_package_event_payload` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_package_from_dict` | function | `(data: 'dict[str, Any]') -> 'RecoveryProposalPackage'` |
| `proposal_package_reference_from_event_payload` | function | `(payload: 'dict[str, Any]') -> 'dict[str, Any] | None'` |
| `proposal_package_reference_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_package_scope_is_within` | function | `(package: 'RecoveryProposalPackage', dependency_scope: 'dict[str, Any]') -> 'bool'` |
| `proposal_package_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `uuid4` | function | `()` |
| `validate_recovery_proposal_package` | function | `(*, package: 'RecoveryProposalPackage', dependency_scope: 'dict[str, Any] | None' = None) -> 'None'` |

### `mnemosyne.api.audit`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `ActiveCommitmentAuditRow` | type | `(commitment_id: 'str', commitment_type: 'str', status: 'str', is_unresolved: 'bool', description: 'str', dependency_scope: 'dict[str, Any]', workflow_id: 'str | None', record_count: 'int', first_record_id: 'str | None', last_record_id: 'str | None', last_action_type: 'str | None', last_log_position: 'int | None') -> None` |
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CTLRecord` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', version: 'int', state_before: 'str', state_after: 'str', action_type: 'str', workflow_id: 'str | None', binding_id: 'str | None', triggers: 'list[str]', dependencies: 'list[str]', metadata: 'dict[str, Any]', extension: 'dict[str, Any]', app_id: 'str', app_version: 'str', schema_id: 'str', schema_version: 'str', fsm_version: 'str', timestamp: 'datetime', op_id: 'str | None' = None, policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, log_position: 'int | None' = None, local_log_position: 'int | None' = None) -> None` |
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
| `ctl_record_from_sqlite_row` | function | `(row) -> 'CTLRecord'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `datetime` | type | `<unavailable>` |
| `event_from_extension` | function | `(extension: 'dict[str, Any]') -> 'CommitmentEvent'` |
| `field` | function | `(*, default=<dataclasses._MISSING_TYPE object at 0xADDR>, default_factory=<dataclasses._MISSING_TYPE object at 0xADDR>, init=True, repr=True, hash=None, compare=True, metadata=None, kw_only=<dataclasses._MISSING_TYPE object at 0xADDR>, doc=None)` |
| `list_unresolved_commitments` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str | None' = None) -> 'UnresolvedCommitmentReport'` |
| `proposal_package_reference_from_event_payload` | function | `(payload: 'dict[str, Any]') -> 'dict[str, Any] | None'` |
| `require_recovery_store` | function | `(store: 'T', *, required_methods: 'tuple[str, ...]' = ('get_record', 'get_entity_history', 'get_full_entity_history', 'get_state_view', 'get_by_op_id', 'commit_batch', 'append_recovery_event', 'list_recovery_events')) -> 'T'` |

### `mnemosyne.benchmarks.jssp_disruption_commitments`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `ActiveCommitment` | type | `(commitment_id: 'str', commitment_type: 'str', description: 'str', creating_record_id: 'str | None' = None, creating_workflow_id: 'str | None' = None, dependency_scope: 'dict[str, Any]' = <factory>, trigger: 'dict[str, Any]' = <factory>, continuation_ref: 'str | None' = None, guard_ref: 'str | None' = None, validator_ref: 'str | None' = None, compensation_ref: 'str | None' = None, priority: 'int' = 0, expiry: 'str | None' = None, failure_signature: 'dict[str, Any] | None' = None, cross_episode_key: 'str | None' = None) -> None` |
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CommitmentApiResult` | type | `(batch: 'CommitBatch', candidate: 'TransitionCandidate', validation: 'ValidationResult', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `DisruptedOperation` | type | `(scheduled_operation: 'JSSPScheduledOperation', disruption: 'MachineBreakdown', reason: 'str') -> None` |
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPCommitmentFireResult` | type | `(commitment_id: 'str', operation_key: 'str', disrupted_operation: 'DisruptedOperation', result: 'CommitmentApiResult') -> None` |
| `JSSPCommitmentRegistrationResult` | type | `(commitment_id: 'str', operation_key: 'str', result: 'CommitmentApiResult') -> None` |
| `JSSPDisruptionSignalResult` | type | `(disruption: 'MachineBreakdown', affected: 'list[DisruptedOperation]', fired: 'list[JSSPCommitmentFireResult]') -> None` |
| `MachineBreakdown` | type | `(event_id: 'str', machine_id: 'str', unavailable_start: 'int', unavailable_end: 'int', reason: 'str' = 'machine_breakdown') -> None` |
| `active_commitment_for_scheduled_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', scheduled_operation: 'Any') -> 'ActiveCommitment'` |
| `active_commitment_statuses` | function | `(*, store: 'Any', tenant_id: 'str', workflow_id: 'str', commitment_ids: 'list[str]') -> 'dict[str, str | None]'` |
| `affected_operations` | function | `(schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown') -> 'list[DisruptedOperation]'` |
| `commitment_id_for_operation` | function | `(*, case_id: 'str', operation: 'JSSPScheduledOperation') -> 'str'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `dependency_scope_for_operation` | function | `(*, case_id: 'str', operation: 'JSSPScheduledOperation') -> 'dict[str, Any]'` |
| `fire_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, reason: 'str' = 'trigger_true', validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'CommitmentApiResult'` |
| `get_active_commitment_status` | function | `(*, store: 'Any', tenant_id: 'str', commitment_id: 'str', workflow_id: 'str | None' = None) -> 'CommitmentStatus | None'` |
| `register_active_commitment` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', commitment: 'ActiveCommitment', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, validator: 'Validator | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None) -> 'CommitmentApiResult'` |
| `register_schedule_commitments` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'list[JSSPCommitmentRegistrationResult]'` |
| `signal_machine_breakdown` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'JSSPDisruptionSignalResult'` |

### `mnemosyne.benchmarks.jssp_recovery_proposals`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `DisruptedOperation` | type | `(scheduled_operation: 'JSSPScheduledOperation', disruption: 'MachineBreakdown', reason: 'str') -> None` |
| `JSSPBaselineSchedule` | type | `(case_id: 'str', operations: 'tuple[JSSPScheduledOperation, ...]') -> None` |
| `JSSPDisruptionSignalResult` | type | `(disruption: 'MachineBreakdown', affected: 'list[DisruptedOperation]', fired: 'list[JSSPCommitmentFireResult]') -> None` |
| `JSSPRecoveryProposal` | type | `(operation_key: 'str', commitment_id: 'str', proposal_ref: 'str', package_id: 'str', proposal_scope: 'dict[str, Any]', package: 'Any', result: 'ProposalPackageApiResult') -> None` |
| `JSSPRecoveryProposalBatch` | type | `(schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', proposals: 'list[JSSPRecoveryProposal]') -> None` |
| `JSSPScheduledOperation` | type | `(operation: 'JSSPOperation', start: 'int', end: 'int') -> None` |
| `MachineBreakdown` | type | `(event_id: 'str', machine_id: 'str', unavailable_start: 'int', unavailable_end: 'int', reason: 'str' = 'machine_breakdown') -> None` |
| `ProposalPackageApiResult` | type | `(package: 'RecoveryProposalPackage', candidate: 'TransitionCandidate', commitment_result: 'CommitmentApiResult') -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `active_commitment_for_scheduled_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', scheduled_operation: 'Any') -> 'ActiveCommitment'` |
| `create_recovery_proposal_package` | function | `(*, package_id: 'str | None' = None, commitment_id: 'str', proposal_ref: 'str', proposal_scope: 'dict[str, Any]', proposed_domain_candidates: 'list[TransitionCandidate] | None' = None, rationale: 'str | None' = None, validator_context: 'dict[str, Any] | None' = None, created_from_record_id: 'str | None' = None, created_by: 'str | None' = None) -> 'RecoveryProposalPackage'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `dependency_scope_for_operation` | function | `(*, case_id: 'str', operation: 'JSSPScheduledOperation') -> 'dict[str, Any]'` |
| `emit_package_backed_proposal` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', package: 'RecoveryProposalPackage', commitment: 'ActiveCommitment | None' = None, dependency_scope: 'dict[str, Any] | None' = None, workflow_id: 'str | None' = None, binding_id: 'str | None' = None, state_before: 'str | None' = None, validator: 'Any | None' = None, batch_id: 'str | None' = None, rid: 'str | None' = None, op_id: 'str | None' = None, dependency_rid: 'str | None' = None) -> 'ProposalPackageApiResult'` |
| `emit_recovery_proposals_for_disruption` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption_signal: 'JSSPDisruptionSignalResult', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'JSSPRecoveryProposalBatch'` |
| `package_to_dict` | function | `(package: 'RecoveryProposalPackage') -> 'dict[str, Any]'` |
| `proposal_scope_for_disrupted_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation') -> 'dict[str, Any]'` |
| `recovery_package_for_disrupted_operation` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', created_from_record_id: 'str', candidate_start: 'int | None' = None, created_by: 'str' = 'jssp_recovery_proposal_adapter') -> 'Any'` |
| `repair_candidate_for_disrupted_operation` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', candidate_start: 'int | None' = None) -> 'TransitionCandidate'` |
| `repair_details_for_disrupted_operation` | function | `(*, schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', disrupted_operation: 'DisruptedOperation', candidate_start: 'int | None' = None) -> 'dict[str, Any]'` |

### `mnemosyne.benchmarks.jssp_repair_admission`

- Available: True

| Callable | Kind | Signature |
|---|---|---|
| `Any` | _AnyMeta | `(*args, **kwargs)` |
| `CTLRecord` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', version: 'int', state_before: 'str', state_after: 'str', action_type: 'str', workflow_id: 'str | None', binding_id: 'str | None', triggers: 'list[str]', dependencies: 'list[str]', metadata: 'dict[str, Any]', extension: 'dict[str, Any]', app_id: 'str', app_version: 'str', schema_id: 'str', schema_version: 'str', fsm_version: 'str', timestamp: 'datetime', op_id: 'str | None' = None, policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, log_position: 'int | None' = None, local_log_position: 'int | None' = None) -> None` |
| `CommitBatch` | type | `(batch_id: 'str', tenant_id: 'str', workflow_id: 'str | None', tx_group_id: 'str', candidates: 'list[TransitionCandidate]', expected_versions: 'dict[tuple[str, str], int]' = <factory>, outbox_intents: 'list[OutboxIntent]' = <factory>, command_id: 'str | None' = None) -> None` |
| `JSSPFinalizedRepairCommitment` | type | `(operation_key: 'str', commitment_id: 'str', admitted_record_ids: 'list[str]', result: 'Any') -> None` |
| `JSSPRecoveryProposalBatch` | type | `(schedule: 'JSSPBaselineSchedule', disruption: 'MachineBreakdown', proposals: 'list[JSSPRecoveryProposal]') -> None` |
| `JSSPRepairCommitmentFinalization` | type | `(finalized: 'list[JSSPFinalizedRepairCommitment]') -> None` |
| `JSSPSelectedRepairAdmission` | type | `(selected_candidates: 'list[TransitionCandidate]', batch: 'CommitBatch', validation: 'ValidationResult | None', records: 'list[CTLRecord]', committed: 'list[CTLRecord]') -> None` |
| `TransitionCandidate` | type | `(rid: 'str', tenant_id: 'str', tx_group_id: 'str', eid: 'str', fsm: 'str', state_before: 'str', state_after: 'str', action_type: 'str' = 'transition', workflow_id: 'str | None' = None, binding_id: 'str | None' = None, triggers: 'list[str]' = <factory>, dependencies: 'list[str]' = <factory>, extension: 'dict[str, Any]' = <factory>, metadata: 'dict[str, Any]' = <factory>, app_id: 'str' = 'core', app_version: 'str' = '1.0', schema_id: 'str' = 'core.transition', schema_version: 'str' = '1.0', fsm_version: 'str' = '1.0', policy_id: 'str | None' = None, policy_version: 'str | None' = None, validator_id: 'str | None' = None, validator_version: 'str | None' = None, op_id: 'str | None' = None) -> None` |
| `ValidationResult` | type | `(ok: 'bool', errors: 'list[ConstraintResult]' = <factory>, validator_id: 'str' = 'core.validator', validator_version: 'str' = '1.0') -> None` |
| `admit_and_finalize_repair_candidates_from_proposal_batch` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', repair_tx_group_id: 'str', finalize_tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', operation_keys: 'list[str] | None' = None, repair_batch_id: 'str | None' = None) -> 'tuple[JSSPSelectedRepairAdmission, JSSPRepairCommitmentFinalization]'` |
| `admit_repair_candidates_from_proposal_batch` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', operation_keys: 'list[str] | None' = None, batch_id: 'str | None' = None) -> 'JSSPSelectedRepairAdmission'` |
| `admit_selected_repair_candidates` | function | `(*, store: 'Any', validator: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', selected_candidates: 'list[TransitionCandidate]', batch_id: 'str | None' = None) -> 'JSSPSelectedRepairAdmission'` |
| `dataclass` | function | `(cls=None, /, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, match_args=True, kw_only=False, slots=False, weakref_slot=False)` |
| `finalize_commitments_for_repair_admission` | function | `(*, store: 'Any', tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', proposal_batch: 'JSSPRecoveryProposalBatch', repair_admission: 'JSSPSelectedRepairAdmission', rid_prefix: 'str | None' = None, batch_prefix: 'str | None' = None) -> 'JSSPRepairCommitmentFinalization'` |
| `repair_candidates_from_proposal_batch` | function | `(proposal_batch: 'JSSPRecoveryProposalBatch', *, operation_keys: 'list[str] | None' = None) -> 'list[TransitionCandidate]'` |
| `replace` | function | `(obj, /, **changes)` |
| `selected_repair_commit_batch` | function | `(*, tenant_id: 'str', tx_group_id: 'str', workflow_id: 'str', selected_candidates: 'list[TransitionCandidate]', batch_id: 'str | None' = None) -> 'CommitBatch'` |

## Next Step

Use this inspected surface to build the API-backed Thanksgiving recovery package.

