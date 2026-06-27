from __future__ import annotations

import pytest

from mnemosyne.api import admit_validated_active_commitment
from mnemosyne.api.recovery_admission import (
    ValidatedRecoveryAdmissionError,
    require_recovery_validator,
)
from mnemosyne.core.protocols.recovery_store import RecoveryStoreCapabilityError
from mnemosyne.store.sqlite.store import SQLiteStore


class EmptyStore:
    pass


class DummyValidator:
    pass


def test_require_recovery_validator_fails_closed_when_missing():
    with pytest.raises(ValidatedRecoveryAdmissionError) as exc:
        require_recovery_validator(None)

    assert "explicit validator" in str(exc.value)


def test_require_recovery_validator_accepts_explicit_validator_object():
    validator = DummyValidator()

    assert require_recovery_validator(validator) is validator


@pytest.mark.asyncio
async def test_public_validated_admission_requires_validator():
    with pytest.raises(ValidatedRecoveryAdmissionError) as exc:
        await admit_validated_active_commitment(
            store=SQLiteStore(),
            tenant_id="tenant",
            tx_group_id="tx",
            commitment_id="commitment",
            admitted_record_ids=[],
            validator=None,
            workflow_id="workflow",
        )

    assert "validated recovery admission requires an explicit validator" in str(exc.value)


@pytest.mark.asyncio
async def test_public_validated_admission_requires_recovery_store_capability():
    with pytest.raises(RecoveryStoreCapabilityError) as exc:
        await admit_validated_active_commitment(
            store=EmptyStore(),
            tenant_id="tenant",
            tx_group_id="tx",
            commitment_id="commitment",
            admitted_record_ids=[],
            validator=DummyValidator(),
            workflow_id="workflow",
        )

    assert "RecoveryStore capability boundary" in str(exc.value)
