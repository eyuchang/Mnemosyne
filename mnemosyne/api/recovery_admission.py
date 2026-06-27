from __future__ import annotations

from typing import Any

from mnemosyne.api.commitments import CommitmentApiResult, admit_active_commitment
from mnemosyne.core.protocols.recovery_store import require_recovery_store


class ValidatedRecoveryAdmissionError(TypeError):
    """Raised when public recovery admission is attempted without validation."""


def require_recovery_validator(validator: Any | None) -> Any:
    """Fail closed unless a validator is explicitly supplied.

    R7.4 makes validator presence mandatory at the public recovery-admission
    boundary. Deeper validator capability checks can be hardened in later R7.4
    commits without weakening this boundary.
    """

    if validator is None:
        raise ValidatedRecoveryAdmissionError(
            "validated recovery admission requires an explicit validator"
        )
    return validator


async def admit_validated_active_commitment(
    *,
    store: Any,
    tenant_id: str,
    tx_group_id: str,
    commitment_id: str,
    admitted_record_ids: list[str],
    validator: Any,
    workflow_id: str | None = None,
    binding_id: str | None = None,
    batch_id: str | None = None,
    rid: str | None = None,
    op_id: str | None = None,
    dependency_rid: str | None = None,
) -> CommitmentApiResult:
    """Public validated recovery-admission boundary.

    This function is the R7.4 public mutation path for admitting active
    commitments after recovery. It fails closed unless:
    - the store satisfies the recovery-store boundary, and
    - an explicit validator is supplied.

    It delegates to the existing admission substrate after boundary checks.
    """

    store = require_recovery_store(store)
    validator = require_recovery_validator(validator)

    return await admit_active_commitment(
        store=store,
        tenant_id=tenant_id,
        tx_group_id=tx_group_id,
        commitment_id=commitment_id,
        admitted_record_ids=admitted_record_ids,
        workflow_id=workflow_id,
        binding_id=binding_id,
        validator=validator,
        batch_id=batch_id,
        rid=rid,
        op_id=op_id,
        dependency_rid=dependency_rid,
    )
