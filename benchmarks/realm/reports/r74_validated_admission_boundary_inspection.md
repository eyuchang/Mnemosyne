# R7.4 Validated Recovery Admission Boundary Inspection

## Summary

- Inspected files: 43
- Mutation sites: 69
- Validation sites: 201
- Decision: `ready_for_validated_admission_boundary_hardening`

## Purpose

R7.4 hardens recovery admission so repair/domain mutation cannot bypass validated public APIs.

This inspection commit does not change mutation semantics. It identifies the admission and validation surfaces to harden next.

## Mutation Sites

### `mnemosyne/api/__init__.py`

- L13: `admit_active_commitment` — `admit_active_commitment,`
- L95: `admit_active_commitment` — `"admit_active_commitment",`

### `mnemosyne/api/commitments.py`

- L103: `commit_batch` — `committed = await store.commit_batch(batch, records)`
- L215: `admit_active_commitment` — `async def admit_active_commitment(`

### `mnemosyne/api/recovery_admission.py`

- L5: `admit_active_commitment` — `from mnemosyne.api.commitments import CommitmentApiResult, admit_active_commitment`
- L56: `admit_active_commitment` — `return await admit_active_commitment(`

### `mnemosyne/benchmarks/jssp_repair_admission.py`

- L56: `commit_batch` — `def selected_repair_commit_batch(`
- L93: `commit_batch` — `batch = selected_repair_commit_batch(`
- L121: `commit_batch` — `committed = await store.commit_batch(batch, records)`
- L132: `admit_repair` — `async def admit_repair_candidates_from_proposal_batch(`
- L173: `finalize` — `finalized: list[JSSPFinalizedRepairCommitment]`
- L177: `finalize` — `return all(item.ok for item in self.finalized)`
- L181: `finalize` — `return [item.commitment_id for item in self.finalized]`
- L187: `finalize` — `for item in self.finalized`
- L192: `finalize` — `async def finalize_commitments_for_repair_admission(`
- L203: `admit_active_commitment` — `from mnemosyne.api.commitments import admit_active_commitment`
- L206: `finalize` — `finalized: list[JSSPFinalizedRepairCommitment] = []`
- L220: `admit_active_commitment` — `result = await admit_active_commitment(`
- L231: `finalize` — `finalized.append(`
- L240: `finalize` — `return JSSPRepairCommitmentFinalization(finalized=finalized)`
- L243: `admit_and_finalize` — `async def admit_and_finalize_repair_candidates_from_proposal_batch(`
- L243: `finalize` — `async def admit_and_finalize_repair_candidates_from_proposal_batch(`
- L249: `finalize` — `finalize_tx_group_id: str,`
- L255: `admit_repair` — `repair_admission = await admit_repair_candidates_from_proposal_batch(`
- L266: `finalize` — `finalization = await finalize_commitments_for_repair_admission(`
- L269: `finalize` — `tx_group_id=finalize_tx_group_id,`

### `mnemosyne/benchmarks/jssp_schedule_admission.py`

- L141: `commit_batch` — `def baseline_schedule_commit_batch(`
- L179: `commit_batch` — `batch = baseline_schedule_commit_batch(`
- L211: `commit_batch` — `committed = await store.commit_batch(batch, records)`

### `mnemosyne/core/recovery/replay.py`

- L12: `finalize` — `"commitment_finalized",`

### `tests/benchmarks/test_jssp_repair_admission.py`

- L19: `admit_repair` — `admit_repair_candidates_from_proposal_batch,`
- L22: `commit_batch` — `selected_repair_commit_batch,`
- L136: `commit_batch` — `async def test_selected_repair_commit_batch_is_domain_ctl_batch(store, validator):`
- L140: `commit_batch` — `batch = selected_repair_commit_batch(`
- L188: `admit_repair` — `repair_admission = await admit_repair_candidates_from_proposal_batch(`
- L243: `admit_and_finalize` — `admit_and_finalize_repair_candidates_from_proposal_batch,`
- L243: `finalize` — `admit_and_finalize_repair_candidates_from_proposal_batch,`
- L244: `finalize` — `finalize_commitments_for_repair_admission,`
- L256: `admit_repair` — `repair_admission = await admit_repair_candidates_from_proposal_batch(`
- L272: `repair admission` — `# Domain repair admission mutates schedule truth, but commitment finalization`
- L276: `finalize` — `finalization = await finalize_commitments_for_repair_admission(`
- L337: `admit_and_finalize` — `async def test_admit_and_finalize_repair_candidates_one_step_helper(store, validator):`
- L337: `finalize` — `async def test_admit_and_finalize_repair_candidates_one_step_helper(store, validator):`
- L340: `admit_and_finalize` — `admit_and_finalize_repair_candidates_from_proposal_batch,`
- L340: `finalize` — `admit_and_finalize_repair_candidates_from_proposal_batch,`
- L345: `admit_and_finalize` — `repair_admission, finalization = await admit_and_finalize_repair_candidates_from_proposal_batch(`
- L345: `finalize` — `repair_admission, finalization = await admit_and_finalize_repair_candidates_from_proposal_batch(`
- L350: `finalize` — `finalize_tx_group_id="tx:r61-jssp:commitment-finalization",`

### `tests/core/test_recovery_admission_boundary.py`

- L124: `commit_batch` — `await store.commit_batch(batch("batch:domain-initial", []), [initial_domain])`
- L153: `commit_batch` — `await store.commit_batch(`
- L183: `commit_batch` — `await store.commit_batch(`
- L238: `commit_batch` — `await store.commit_batch(`
- L281: `commit_batch` — `await store.commit_batch(`
- L330: `commit_batch` — `await store.commit_batch(`

### `tests/core/test_recovery_api_store_boundary.py`

- L10: `admit_active_commitment` — `from mnemosyne.api.commitments import admit_active_commitment`
- L55: `admit_active_commitment` — `async def test_admit_active_commitment_fails_closed_without_recovery_store():`
- L57: `admit_active_commitment` — `await admit_active_commitment(`
- L67: `commit_batch` — `assert "commit_batch" in str(exc.value)`

### `tests/core/test_recovery_proposal_package_candidates.py`

- L148: `commit_batch` — `await store.commit_batch(`
- L234: `commit_batch` — `await store.commit_batch(`
- L264: `commit_batch` — `committed = await store.commit_batch(candidate_batch, records)`

### `tests/core/test_recovery_service.py`

- L108: `commit_batch` — `await store.commit_batch(`
- L145: `commit_batch` — `await store.commit_batch(`
- L192: `commit_batch` — `await store.commit_batch(`
- L244: `commit_batch` — `await store.commit_batch(`

### `tests/core/test_recovery_store_capability_guard.py`

- L72: `commit_batch` — `assert "commit_batch" in str(exc.value)`

### `tests/core/test_recovery_store_persistence.py`

- L119: `commit_batch` — `await store.commit_batch(batch(candidates), records)`
- L196: `commit_batch` — `await store.commit_batch(batch(candidates), records)`

### `tests/core/test_recovery_store_protocol.py`

- L35: `commit_batch` — `assert RECOVERY_WRITE_METHODS == ("commit_batch",)`

## Validation Sites

### `mnemosyne/api/__init__.py`

- L15: `validator` — `default_commitment_validator,`
- L35: `validate` — `validate_recovery_proposal_package,`
- L45: `validate` — `admit_validated_active_commitment,`
- L46: `validator` — `require_recovery_validator,`
- L58: `validate` — `validate_and_commit_active_recovery,`
- L76: `validate` — `"admit_validated_active_commitment",`
- L77: `validator` — `"require_recovery_validator",`
- L102: `validator` — `"default_commitment_validator",`
- L127: `validate` — `"validate_and_commit_active_recovery",`
- L128: `validate` — `"validate_recovery_proposal_package",`

### `mnemosyne/api/audit.py`

- L7: `require_recovery_store` — `from mnemosyne.core.protocols.recovery_store import RECOVERY_READ_METHODS, require_recovery_store`
- L190: `validate` — `This is read-only. It does not validate, commit, mutate CTL, or execute`
- L258: `require_recovery_store` — `store = require_recovery_store(store, required_methods=RECOVERY_READ_METHODS)`
- L297: `require_recovery_store` — `store = require_recovery_store(store, required_methods=RECOVERY_READ_METHODS)`
- L359: `require_recovery_store` — `store = require_recovery_store(store, required_methods=RECOVERY_READ_METHODS)`

### `mnemosyne/api/commitments.py`

- L7: `require_recovery_store` — `from mnemosyne.core.protocols.recovery_store import require_recovery_store`
- L20: `ValidationResult` — `from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult`
- L34: `ValidationResult` — `validation: ValidationResult`
- L59: `validator` — `def default_commitment_validator() -> Validator:`
- L60: `validator` — `"""Build the default validator for commitment-FSM API calls."""`
- L73: `validator` — `validator: Validator | None = None,`
- L82: `validator` — `validator = validator or default_commitment_validator()`
- L92: `validator` — `validation = await validator.validate_batch(batch, store)`
- L92: `validate` — `validation = await validator.validate_batch(batch, store)`
- L102: `validator` — `records = await validator.records_from_batch(batch, store)`
- L122: `validator` — `validator: Validator | None = None,`
- L140: `validator` — `validator=validator,`
- L154: `validator` — `validator: Validator | None = None,`
- L175: `validator` — `validator=validator,`
- L189: `validator` — `validator: Validator | None = None,`
- L210: `validator` — `validator=validator,`
- L224: `validator` — `validator: Validator | None = None,`
- L231: `require_recovery_store` — `store = require_recovery_store(store)`
- L247: `validator` — `validator=validator,`
- L263: `validator` — `validator: Validator | None = None,`
- L286: `validator` — `validator=validator,`

### `mnemosyne/api/proposal_packages.py`

- L7: `validator` — `from mnemosyne.api.commitments import CommitmentApiResult, commit_commitment_candidate, default_commitment_validator`
- L54: `validator` — `validator_context: dict[str, Any] | None = None,`
- L71: `validator` — `validator_context=dict(validator_context or {}),`
- L77: `validate` — `def validate_recovery_proposal_package(`
- L160: `validator` — `validator: Any | None = None,`
- L189: `validator` — `validator=validator or default_commitment_validator(),`

### `mnemosyne/api/recovery.py`

- L6: `validator` — `from mnemosyne.api.commitments import default_commitment_validator`
- L7: `ValidationResult` — `from mnemosyne.core.models import CTLRecord, ValidationResult`
- L40: `ValidationResult` — `def validation_results(self) -> list[ValidationResult]:`
- L100: `validate` — `async def validate_and_commit_active_recovery(`
- L107: `validator` — `validator: Any | None = None,`
- L113: `validate` — `"""Plan, validate, and commit active recovery through the product API.`
- L120: `validate` — `execution = await executor.plan_validate_and_commit(`
- L125: `validator` — `validator=validator or default_commitment_validator(),`

### `mnemosyne/api/recovery_admission.py`

- L6: `require_recovery_store` — `from mnemosyne.core.protocols.recovery_store import require_recovery_store`
- L13: `validator` — `def require_recovery_validator(validator: Any | None) -> Any:`
- L14: `validator` — `"""Fail closed unless a validator is explicitly supplied.`
- L16: `validator` — `R7.4 makes validator presence mandatory at the public recovery-admission`
- L17: `validator` — `boundary. Deeper validator capability checks can be hardened in later R7.4`
- L21: `validator` — `if validator is None:`
- L23: `validator` — `"validated recovery admission requires an explicit validator"`
- L23: `validate` — `"validated recovery admission requires an explicit validator"`
- L25: `validator` — `return validator`
- L28: `validate` — `async def admit_validated_active_commitment(`
- L35: `validator` — `validator: Any,`
- L43: `validate` — `"""Public validated recovery-admission boundary.`
- L48: `validator` — `- an explicit validator is supplied.`
- L53: `require_recovery_store` — `store = require_recovery_store(store)`
- L54: `validator` — `validator = require_recovery_validator(validator)`
- L64: `validator` — `validator=validator,`

### `mnemosyne/api/recovery_events.py`

- L6: `require_recovery_store` — `from mnemosyne.core.protocols.recovery_store import require_recovery_store`
- L26: `require_recovery_store` — `store = require_recovery_store(store)`
- L47: `require_recovery_store` — `store = require_recovery_store(store)`

### `mnemosyne/api/recovery_replay.py`

- L6: `require_recovery_store` — `from mnemosyne.core.protocols.recovery_store import require_recovery_store`
- L45: `require_recovery_store` — `store = require_recovery_store(store)`

### `mnemosyne/benchmarks/jssp_disruptions.py`

- L181: `validate` — `def validate_baseline_schedule(`

### `mnemosyne/benchmarks/jssp_recovery_proposals.py`

- L221: `validator` — `validator_id=None,`
- L222: `validator` — `validator_version=None,`
- L269: `validator` — `validator_context={`

### `mnemosyne/benchmarks/jssp_repair_admission.py`

- L7: `ValidationResult` — `from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult`
- L14: `ValidationResult` — `validation: ValidationResult | None`
- L86: `validator` — `validator: Any,`
- L110: `validator` — `validation = await validator.validate_batch(batch, store)`
- L110: `validate` — `validation = await validator.validate_batch(batch, store)`
- L120: `validator` — `records = await validator.records_from_batch(batch, store)`
- L135: `validator` — `validator: Any,`
- L150: `validator` — `validator=validator,`
- L246: `validator` — `validator: Any,`
- L257: `validator` — `validator=validator,`

### `mnemosyne/benchmarks/jssp_schedule_admission.py`

- L11: `validate` — `validate_baseline_schedule,`
- L13: `ValidationResult` — `from mnemosyne.core.models import CTLRecord, CommitBatch, TransitionCandidate, ValidationResult`
- L30: `ValidationResult` — `validation: ValidationResult | None`
- L107: `validator` — `validator_id=None,`
- L108: `validator` — `validator_version=None,`
- L168: `validator` — `validator: Any,`
- L188: `validate` — `schedule_violations = validate_baseline_schedule(schedule)`
- L199: `validator` — `validation = await validator.validate_batch(batch, store)`
- L199: `validate` — `validation = await validator.validate_batch(batch, store)`
- L210: `validator` — `records = await validator.records_from_batch(batch, store)`

### `mnemosyne/core/recovery/packages.py`

- L25: `validator` — `validator_context: dict[str, Any] = field(default_factory=dict)`
- L67: `validator` — `"validator_context": dict(package.validator_context),`
- L84: `validator` — `validator_context=dict(data.get("validator_context", {})),`

### `mnemosyne/core/validation/__init__.py`

- L1: `validator` — `from .validator import ConstraintFn, ConstraintKey, ConstraintRegistry, NoopSchemaValidator, Validator`

### `mnemosyne/core/validation/validator.py`

- L15: `ValidationResult` — `ValidationResult,`
- L38: `validate` — `def validate(self, schema_id: str, schema_version: str, payload: dict[str, Any]) -> ValidationResult:`
- L38: `ValidationResult` — `def validate(self, schema_id: str, schema_version: str, payload: dict[str, Any]) -> ValidationResult:`
- L39: `ValidationResult` — `return ValidationResult.pass_()`
- L47: `validator` — `schema_validator: SchemaValidator | None = None,`
- L48: `validator` — `validator_id: str = "core.validator",`
- L49: `validator` — `validator_version: str = "1.0",`
- L53: `validator` — `self.schema_validator = schema_validator or NoopSchemaValidator()`
- L54: `validator` — `self.validator_id = validator_id`
- L55: `validator` — `self.validator_version = validator_version`
- L57: `validate` — `async def validate_candidate(self, candidate: TransitionCandidate, store: Store) -> ValidationResult:`
- L57: `ValidationResult` — `async def validate_candidate(self, candidate: TransitionCandidate, store: Store) -> ValidationResult:`
- L61: `ValidationResult` — `return ValidationResult.fail(errors)`
- L115: `validator` — `schema_result = self.schema_validator.validate(candidate.schema_id, candidate.schema_version, candidate.extension)`
- L115: `validate` — `schema_result = self.schema_validator.validate(candidate.schema_id, candidate.schema_version, candidate.extension)`
- L127: `ValidationResult` — `return ValidationResult.fail(errors)`
- L128: `validator` — `return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)`
- L128: `ValidationResult` — `return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)`
- L130: `validate` — `async def validate_batch(self, batch: CommitBatch, store: Store) -> ValidationResult:`
- L130: `ValidationResult` — `async def validate_batch(self, batch: CommitBatch, store: Store) -> ValidationResult:`
- L143: `validate` — `result = await self.validate_candidate(candidate, store)`
- L157: `ValidationResult` — `return ValidationResult.fail(errors)`
- L158: `validator` — `return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)`
- L158: `ValidationResult` — `return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)`
- L255: `validator` — `validator_id=self.validator_id,`
- L256: `validator` — `validator_version=self.validator_version,`

### `tests/benchmarks/test_jssp_repair_admission.py`

- L34: `validator` — `async def _seed_recovery_proposal_batch(store, validator):`
- L40: `validator` — `validator=validator,`
- L92: `validator` — `async def test_selects_all_repair_candidates_from_proposal_batch(store, validator):`
- L93: `validator` — `schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L119: `validator` — `async def test_selects_subset_of_repair_candidates_by_operation_key(store, validator):`
- L120: `validator` — `_, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L136: `validator` — `async def test_selected_repair_commit_batch_is_domain_ctl_batch(store, validator):`
- L137: `validator` — `_, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L161: `validator` — `validator,`
- L163: `validator` — `schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L190: `validator` — `validator=validator,`
- L239: `validator` — `validator,`
- L247: `validator` — `schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L258: `validator` — `validator=validator,`
- L337: `validator` — `async def test_admit_and_finalize_repair_candidates_one_step_helper(store, validator):`
- L343: `validator` — `_, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L347: `validator` — `validator=validator,`
- L381: `validator` — `validator,`
- L385: `validator` — `schedule, proposal_batch = await _seed_recovery_proposal_batch(store, validator)`
- L419: `validator` — `validator=validator,`
- L466: `validator` — `validator,`
- L470: `validator` — `schedule, _ = await _seed_recovery_proposal_batch(store, validator)`
- L492: `validator` — `validator=validator,`

### `tests/core/test_recovery_admission_boundary.py`

- L57: `validator` — `validator_id=candidate.validator_id,`
- L58: `validator` — `validator_version=candidate.validator_version,`
- L88: `validator` — `validator_id="test.validator",`
- L89: `validator` — `validator_version="1.0",`

### `tests/core/test_recovery_api_store_boundary.py`

- L11: `RecoveryStore` — `from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError`
- L20: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L27: `RecoveryStore` — `assert "RecoveryStore capability boundary" in str(exc.value)`
- L32: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L39: `RecoveryStore` — `assert "RecoveryStore capability boundary" in str(exc.value)`
- L44: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L51: `RecoveryStore` — `assert "RecoveryStore capability boundary" in str(exc.value)`
- L56: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L66: `RecoveryStore` — `assert "RecoveryStore capability boundary" in str(exc.value)`

### `tests/core/test_recovery_event_api.py`

- L11: `RecoveryStore` — `from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError`
- L107: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError):`
- L113: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError):`

### `tests/core/test_recovery_proposal_package_candidates.py`

- L68: `validator` — `validator_id=None,`
- L69: `validator` — `validator_version=None,`
- L98: `validator` — `validator_id="test.validator",`
- L99: `validator` — `validator_version="1.0",`
- L124: `validator` — `validator_context={"source": "runtime"},`
- L257: `validator` — `validator = Validator(build_commitment_fsm_registry())`
- L259: `validator` — `validation = await validator.validate_batch(candidate_batch, store)`
- L259: `validate` — `validation = await validator.validate_batch(candidate_batch, store)`
- L263: `validator` — `records = await validator.records_from_batch(candidate_batch, store)`

### `tests/core/test_recovery_proposal_package_events.py`

- L43: `validator` — `validator_id=None,`
- L44: `validator` — `validator_version=None,`
- L59: `validator` — `validator_context={"source": "runtime"},`

### `tests/core/test_recovery_proposal_packages.py`

- L37: `validator` — `validator_id=None,`
- L38: `validator` — `validator_version=None,`
- L66: `validator` — `validator_id=None,`
- L67: `validator` — `validator_version=None,`
- L79: `validator` — `validator_context={"source": "runtime"},`
- L111: `validator` — `assert restored.validator_context == pkg.validator_context`

### `tests/core/test_recovery_replay_api.py`

- L10: `RecoveryStore` — `from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError`
- L145: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError):`

### `tests/core/test_recovery_service.py`

- L54: `validator` — `validator_id=candidate.validator_id,`
- L55: `validator` — `validator_version=candidate.validator_version,`

### `tests/core/test_recovery_store_capability_guard.py`

- L10: `RecoveryStore` — `RecoveryStoreCapabilityError,`
- L12: `require_recovery_store` — `require_recovery_store,`
- L21: `RecoveryStore` — `class ReadOnlyRecoveryStore:`
- L42: `require_recovery_store` — `assert require_recovery_store(store) is store`
- L50: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L51: `require_recovery_store` — `require_recovery_store(store)`
- L54: `RecoveryStore` — `assert "RecoveryStore capability boundary" in message`
- L60: `RecoveryStore` — `store = ReadOnlyRecoveryStore()`
- L67: `require_recovery_store` — `assert require_recovery_store(store, required_methods=RECOVERY_READ_METHODS) is store`
- L69: `RecoveryStore` — `with pytest.raises(RecoveryStoreCapabilityError) as exc:`
- L70: `require_recovery_store` — `require_recovery_store(store)`

### `tests/core/test_recovery_store_persistence.py`

- L53: `validator` — `validator_id=candidate.validator_id,`
- L54: `validator` — `validator_version=candidate.validator_version,`

### `tests/core/test_recovery_store_protocol.py`

- L12: `RecoveryStore` — `RecoveryStore,`
- L24: `RecoveryStore` — `assert isinstance(store, RecoveryStore)`

## Recommended R7.4 Hardening Targets

- Identify public recovery admission APIs that mutate committed state.
- Ensure mutation APIs require a validator or validated admission context.
- Fail closed when validator capability is missing.
- Keep low-level commit helpers available only as internal substrate helpers.
- Add tests proving invalid repairs cannot be admitted through the public boundary.
- Add tests proving recovery replay/event-log APIs remain read-only and do not mutate domain truth.

## Claim Boundary

- inspection_only: True
- validated_admission_hardening_claimed: False
- mutation_bypass_prevented_claimed: False
- postgres_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

