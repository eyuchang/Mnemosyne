from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ProposalRequest:
    tenant: str
    workflow: str
    entity: str
    operation: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    conflict_scope: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_json(data: Mapping[str, Any]) -> "ProposalRequest":
        missing = [
            key
            for key in ("tenant", "workflow", "entity", "operation")
            if not data.get(key)
        ]
        if missing:
            raise ValueError(f"missing required proposal fields: {', '.join(missing)}")

        return ProposalRequest(
            tenant=str(data["tenant"]),
            workflow=str(data["workflow"]),
            entity=str(data["entity"]),
            operation=str(data["operation"]),
            payload=dict(data.get("payload") or {}),
            idempotency_key=(
                str(data["idempotency_key"]) if data.get("idempotency_key") else None
            ),
            conflict_scope=(
                str(data["conflict_scope"]) if data.get("conflict_scope") else None
            ),
            evidence=dict(data.get("evidence") or {}),
        )


@dataclass(frozen=True)
class ProposalDecision:
    accepted: bool
    decision: str
    reason: str
    committed_record_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "decision": self.decision,
            "reason": self.reason,
            "committed_record_id": self.committed_record_id,
        }
