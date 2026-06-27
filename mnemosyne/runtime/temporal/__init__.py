# File: mnemosyne/runtime/temporal/__init__.py
#
# Purpose:
#   Public exports for the Temporal runtime adapter package.
#
# Note:
#   Importing this package must not require the temporalio SDK.

from mnemosyne.runtime.temporal.activities import (
    CommitBatchActivityResult,
    validate_and_commit_batch_activity,
)
from mnemosyne.runtime.temporal.client import (
    FakeTemporalClient,
    FakeTemporalWorkflow,
    TemporalClientLike,
)
from mnemosyne.runtime.temporal.dependency import (
    TEMPORAL_EXTRA_INSTALL_HINT,
    is_temporal_sdk_available,
    require_temporal_sdk,
)
from mnemosyne.runtime.temporal.driver import TemporalRuntimeDriver

__all__ = [
    "CommitBatchActivityResult",
    "FakeTemporalClient",
    "FakeTemporalWorkflow",
    "TEMPORAL_EXTRA_INSTALL_HINT",
    "TemporalClientLike",
    "TemporalRuntimeDriver",
    "is_temporal_sdk_available",
    "require_temporal_sdk",
    "validate_and_commit_batch_activity",
]
from mnemosyne.runtime.temporal.active_recovery import (
    ActiveRecoveryActivityResult,
    TemporalRecoveryProposalProvider,
    plan_validate_and_commit_active_recovery_activity,
)
