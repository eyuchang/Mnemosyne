from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mnemosyne.core.models import ConstraintResult, TransitionCandidate
from mnemosyne.core.protocols import Store


@dataclass(frozen=True)
class ConstraintDef:
    fsm: str
    action_type: str
    fn: Callable[[TransitionCandidate, Store], ConstraintResult]
