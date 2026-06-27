from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]

from mnemosyne.api.recovery_admission import (  # noqa: E402
    ValidatedRecoveryAdmissionError,
    admit_validated_active_commitment,
    require_recovery_validator,
)
from mnemosyne.core.protocols.recovery_store import (  # noqa: E402
    RecoveryStoreCapabilityError,
)
from mnemosyne.store.sqlite.store import SQLiteStore  # noqa: E402


class EmptyStore:
    pass


class DummyValidator:
    pass


@dataclass(frozen=True)
class R74ValidatedAdmissionReportResult:
    output_root: Path
    files: dict[str, Path]
    missing_validator_rejected: bool
    missing_store_rejected: bool
    explicit_validator_accepted: bool


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def _check_missing_validator_rejected() -> dict[str, Any]:
    try:
        await admit_validated_active_commitment(
            store=SQLiteStore(),
            tenant_id="tenant-r74",
            tx_group_id="tx-r74",
            commitment_id="commitment-r74",
            admitted_record_ids=[],
            validator=None,
            workflow_id="workflow-r74",
        )
    except ValidatedRecoveryAdmissionError as exc:
        return {
            "ok": True,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "ok": False,
        "error_type": None,
        "message": "missing validator was not rejected",
    }


async def _check_missing_store_rejected() -> dict[str, Any]:
    try:
        await admit_validated_active_commitment(
            store=EmptyStore(),
            tenant_id="tenant-r74",
            tx_group_id="tx-r74",
            commitment_id="commitment-r74",
            admitted_record_ids=[],
            validator=DummyValidator(),
            workflow_id="workflow-r74",
        )
    except RecoveryStoreCapabilityError as exc:
        return {
            "ok": True,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "ok": False,
        "error_type": None,
        "message": "invalid recovery store was not rejected",
    }


def _check_explicit_validator_accepted() -> dict[str, Any]:
    validator = DummyValidator()
    accepted = require_recovery_validator(validator)

    return {
        "ok": accepted is validator,
        "validator_type": type(accepted).__name__,
    }


async def _build_report() -> dict[str, Any]:
    missing_validator = await _check_missing_validator_rejected()
    missing_store = await _check_missing_store_rejected()
    explicit_validator = _check_explicit_validator_accepted()

    return {
        "schema_version": "r74_validated_admission_report.v1",
        "summary": {
            "missing_validator_rejected": missing_validator["ok"],
            "missing_store_rejected": missing_store["ok"],
            "explicit_validator_accepted": explicit_validator["ok"],
            "public_boundary": "admit_validated_active_commitment",
            "decision": "validated_public_admission_boundary_established",
        },
        "checks": {
            "missing_validator": missing_validator,
            "missing_store": missing_store,
            "explicit_validator": explicit_validator,
        },
        "public_api": {
            "validated_entrypoint": "mnemosyne.api.recovery_admission.admit_validated_active_commitment",
            "validator_guard": "mnemosyne.api.recovery_admission.require_recovery_validator",
            "store_guard": "mnemosyne.core.protocols.recovery_store.require_recovery_store",
        },
        "claims": {
            "validated_public_admission_boundary_claimed": True,
            "missing_validator_fails_closed_claimed": True,
            "invalid_store_fails_closed_claimed": True,
            "low_level_substrate_removed_claimed": False,
            "postgres_claimed": False,
            "kubernetes_claimed": False,
            "temporal_claimed": False,
            "production_runtime_claimed": False,
        },
        "limitations": [
            "R7.4 establishes the validated public admission boundary.",
            "R7.4 does not remove every lower-level substrate helper.",
            "Callers should use admit_validated_active_commitment for public recovery admission.",
            "R7.4 does not claim PostgreSQL, Kubernetes, Temporal, or production-runtime execution.",
        ],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]

    lines: list[str] = []
    lines.append("# R7.4 Validated Recovery Admission Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Public boundary: `{summary['public_boundary']}`")
    lines.append(f"- Missing validator rejected: {summary['missing_validator_rejected']}")
    lines.append(f"- Missing store rejected: {summary['missing_store_rejected']}")
    lines.append(f"- Explicit validator accepted: {summary['explicit_validator_accepted']}")
    lines.append(f"- Decision: `{summary['decision']}`")
    lines.append("")
    lines.append("## Public API")
    lines.append("")
    for key, value in report["public_api"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Claims")
    lines.append("")
    for key, value in report["claims"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run_r74_validated_admission_report(
    output_root: str | Path | None = None,
) -> R74ValidatedAdmissionReportResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = asyncio.run(_build_report())

    files = {
        "report_json": root / "reports" / "r74_validated_admission_report.json",
        "report_markdown": root / "reports" / "r74_validated_admission_report.md",
    }

    _write_json(files["report_json"], report)
    files["report_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["report_markdown"].write_text(_render_markdown(report) + "\n", encoding="utf-8")

    return R74ValidatedAdmissionReportResult(
        output_root=root,
        files=files,
        missing_validator_rejected=report["summary"]["missing_validator_rejected"],
        missing_store_rejected=report["summary"]["missing_store_rejected"],
        explicit_validator_accepted=report["summary"]["explicit_validator_accepted"],
    )


def main() -> None:
    result = run_r74_validated_admission_report()
    print("R7.4 validated recovery admission report")
    print(f"output_root: {result.output_root}")
    print(f"missing_validator_rejected: {result.missing_validator_rejected}")
    print(f"missing_store_rejected: {result.missing_store_rejected}")
    print(f"explicit_validator_accepted: {result.explicit_validator_accepted}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
