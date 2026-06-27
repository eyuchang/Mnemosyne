from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from mnemosyne.core.fsm import FSMRegistry
from mnemosyne.core.models import (
    CTLRecord,
    CommitBatch,
    ConstraintResult,
    RecordStatus,
    TransitionCandidate,
    ValidationCode,
    ValidationResult,
    now_utc,
)
from mnemosyne.core.protocols import SchemaValidator, Store
from mnemosyne.core.replay import replay_state_view
from typing import Union

ConstraintFn = Callable[[TransitionCandidate, Store], Union[ConstraintResult, Awaitable[ConstraintResult]]]
ConstraintKey = tuple[str, str]  # (fsm, action_type)


@dataclass
class ConstraintRegistry:
    _constraints: dict[ConstraintKey, list[ConstraintFn]] = field(default_factory=dict)

    def register(self, fsm: str, action_type: str, fn: ConstraintFn) -> None:
        self._constraints.setdefault((fsm, action_type), []).append(fn)

    def get(self, fsm: str, action_type: str) -> list[ConstraintFn]:
        return self._constraints.get((fsm, action_type), []) + self._constraints.get((fsm, "*"), [])


class NoopSchemaValidator:
    def validate(self, schema_id: str, schema_version: str, payload: dict[str, Any]) -> ValidationResult:
        return ValidationResult.pass_()


class Validator:
    def __init__(
        self,
        fsm_registry: FSMRegistry,
        constraints: ConstraintRegistry | None = None,
        schema_validator: SchemaValidator | None = None,
        validator_id: str = "core.validator",
        validator_version: str = "1.0",
    ) -> None:
        self.fsm_registry = fsm_registry
        self.constraints = constraints or ConstraintRegistry()
        self.schema_validator = schema_validator or NoopSchemaValidator()
        self.validator_id = validator_id
        self.validator_version = validator_version

    async def validate_candidate(self, candidate: TransitionCandidate, store: Store) -> ValidationResult:
        errors: list[ConstraintResult] = []
        if not self.fsm_registry.has_fsm(candidate.fsm, candidate.fsm_version):
            errors.append(ConstraintResult.fail(ValidationCode.UNKNOWN_FSM.value, {"fsm": candidate.fsm}))
            return ValidationResult.fail(errors)

        current = await store.get_state_view(candidate.tenant_id, candidate.eid, candidate.fsm)
        if current.state is not None and current.state != candidate.state_before:
            errors.append(
                ConstraintResult.fail(
                    ValidationCode.STATE_MISMATCH.value,
                    {
                        "eid": candidate.eid,
                        "fsm": candidate.fsm,
                        "expected": current.state,
                        "candidate_before": candidate.state_before,
                    },
                )
            )
        if current.state is None:
            initial = self.fsm_registry.initial_state(candidate.fsm, candidate.fsm_version)
            if initial != candidate.state_before:
                errors.append(
                    ConstraintResult.fail(
                        ValidationCode.STATE_MISMATCH.value,
                        {"initial": initial, "candidate_before": candidate.state_before},
                    )
                )

        if not self.fsm_registry.legal(
            candidate.fsm,
            candidate.state_before,
            candidate.state_after,
            candidate.action_type,
            candidate.fsm_version,
        ):
            errors.append(
                ConstraintResult.fail(
                    ValidationCode.ILLEGAL_TRANSITION.value,
                    {
                        "fsm": candidate.fsm,
                        "from": candidate.state_before,
                        "to": candidate.state_after,
                        "action_type": candidate.action_type,
                    },
                )
            )

        bad_deps = [d for d in candidate.dependencies if not await store.is_effective(candidate.tenant_id, d)]
        if bad_deps:
            errors.append(
                ConstraintResult.fail(ValidationCode.DEPENDENCY_NOT_EFFECTIVE.value, {"dependencies": bad_deps})
            )

        missing_triggers = [t for t in candidate.triggers if not await store.has_event(candidate.tenant_id, t)]
        if missing_triggers:
            errors.append(ConstraintResult.fail(ValidationCode.TRIGGER_MISSING.value, {"triggers": missing_triggers}))

        schema_result = self.schema_validator.validate(candidate.schema_id, candidate.schema_version, candidate.extension)
        if not schema_result.ok:
            errors.extend(schema_result.errors)

        for fn in self.constraints.get(candidate.fsm, candidate.action_type):
            result = fn(candidate, store)
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[assignment]
            if not result.ok:  # type: ignore[union-attr]
                errors.append(result)  # type: ignore[arg-type]

        if errors:
            return ValidationResult.fail(errors)
        return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)

    async def validate_batch(self, batch: CommitBatch, store: Store) -> ValidationResult:
        errors: list[ConstraintResult] = []
        seen_keys: set[tuple[str, str]] = set()
        simulated_versions: dict[tuple[str, str], int] = {}
        for candidate in batch.candidates:
            if candidate.tenant_id != batch.tenant_id:
                errors.append(ConstraintResult.fail("TENANT_MISMATCH", {"rid": candidate.rid}))
            if candidate.tx_group_id != batch.tx_group_id:
                errors.append(ConstraintResult.fail("TX_GROUP_MISMATCH", {"rid": candidate.rid}))
            key = (candidate.eid, candidate.fsm)
            if key in seen_keys:
                errors.append(ConstraintResult.fail("DUPLICATE_ENTITY_IN_BATCH", {"key": key}))
            seen_keys.add(key)
            result = await self.validate_candidate(candidate, store)
            errors.extend(result.errors)
            latest = await store.get_latest_version(candidate.tenant_id, candidate.eid, candidate.fsm)
            expected_before = batch.expected_versions.get(key, latest)
            if expected_before != latest:
                errors.append(
                    ConstraintResult.fail(
                        "EXPECTED_VERSION_MISMATCH",
                        {"key": key, "expected": expected_before, "actual": latest},
                    )
                )
            simulated_versions[key] = latest + 1
        errors.extend(await self._check_effectiveness(batch, store))
        if errors:
            return ValidationResult.fail(errors)
        return ValidationResult(ok=True, validator_id=self.validator_id, validator_version=self.validator_version)

    async def _check_effectiveness(self, batch: CommitBatch, store: Store) -> list[ConstraintResult]:
        """Fail-closed compensation consistency (BL-2 / IM-5).

        Rejects, with clear codes, any batch that would leave the effective set inconsistent:
          - COMPENSATION_TARGET_MISSING / _NOT_EFFECTIVE: the compensated record must exist and
            currently be effective;
          - EFFECTIVE_DEPENDENT_ORPHANED: an effective record depends on a record this batch
            removes, and the dependent is not itself removed/replaced here;
          - EFFECTIVE_CHAIN_BROKEN: removing a record would break an entity's effective state
            chain (e.g. mid-chain compensation).
        """
        errors: list[ConstraintResult] = []
        tenant = batch.tenant_id
        added = {c.rid for c in batch.candidates}
        removed: set[str] = set()
        for c in batch.candidates:
            removed.update(c.metadata.get("compensates", []))
            removed.update(c.metadata.get("supersedes", []))
        if not removed:
            return errors

        for old in removed:
            rec = await store.get_record(tenant, old)
            if rec is None:
                errors.append(ConstraintResult.fail("COMPENSATION_TARGET_MISSING", {"rid": old}))
            elif not await store.is_effective(tenant, old):
                errors.append(ConstraintResult.fail("COMPENSATION_TARGET_NOT_EFFECTIVE", {"rid": old}))

        for old in removed:
            for dep in await store.get_effective_dependents(tenant, old):
                if dep.rid not in removed and dep.rid not in added:
                    errors.append(
                        ConstraintResult.fail(
                            "EFFECTIVE_DEPENDENT_ORPHANED",
                            {"dependent": dep.rid, "dependency": old},
                        )
                    )

        provisional = await self.records_from_batch(batch, store)
        prov_by_entity: dict[tuple[str, str], list[CTLRecord]] = {}
        for r in provisional:
            prov_by_entity.setdefault((r.eid, r.fsm), []).append(r)
        entities: set[tuple[str, str]] = set(prov_by_entity.keys())
        for old in removed:
            rec = await store.get_record(tenant, old)
            if rec is not None:
                entities.add((rec.eid, rec.fsm))
        for eid, fsm in entities:
            current = await store.get_entity_history(tenant, eid, fsm)  # effective, version order
            post = [r for r in current if r.rid not in removed]
            post += prov_by_entity.get((eid, fsm), [])
            post.sort(key=lambda r: (r.version, r.log_position or 0))
            try:
                replay_state_view(tenant, eid, fsm, post)
            except ValueError as exc:
                errors.append(
                    ConstraintResult.fail(
                        "EFFECTIVE_CHAIN_BROKEN", {"eid": eid, "fsm": fsm, "detail": str(exc)}
                    )
                )
        return errors

    async def records_from_batch(self, batch: CommitBatch, store: Store) -> list[CTLRecord]:
        records: list[CTLRecord] = []
        for candidate in batch.candidates:
            latest = await store.get_latest_version(candidate.tenant_id, candidate.eid, candidate.fsm)
            metadata = dict(candidate.metadata)
            metadata.setdefault("verdict", "accepted")
            metadata.setdefault("status", RecordStatus.ACTIVE.value)
            metadata.setdefault("compensates", [])
            metadata.setdefault("supersedes", [])
            record = CTLRecord(
                rid=candidate.rid,
                op_id=candidate.op_id or candidate.rid,
                tenant_id=candidate.tenant_id,
                tx_group_id=candidate.tx_group_id,
                eid=candidate.eid,
                fsm=candidate.fsm,
                version=latest + 1,
                state_before=candidate.state_before,
                state_after=candidate.state_after,
                action_type=candidate.action_type,
                workflow_id=candidate.workflow_id or batch.workflow_id,
                binding_id=candidate.binding_id,
                triggers=list(candidate.triggers),
                dependencies=list(candidate.dependencies),
                metadata=metadata,
                extension=dict(candidate.extension),
                app_id=candidate.app_id,
                app_version=candidate.app_version,
                schema_id=candidate.schema_id,
                schema_version=candidate.schema_version,
                fsm_version=candidate.fsm_version,
                policy_id=candidate.policy_id,
                policy_version=candidate.policy_version,
                validator_id=self.validator_id,
                validator_version=self.validator_version,
                timestamp=now_utc(),
            )
            records.append(record)
        return records
