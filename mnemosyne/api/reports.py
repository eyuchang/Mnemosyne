from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from mnemosyne.api.audit import (
    ActiveCommitmentAuditRow,
    CommitmentLineageRow,
    RecoveryLineageRow,
    UnresolvedCommitmentReport,
)


def to_jsonable(value: Any) -> Any:
    """Convert product API report values to JSON-safe structures."""

    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    return value


def active_commitment_audit_rows_to_dicts(
    rows: list[ActiveCommitmentAuditRow],
) -> list[dict[str, Any]]:
    return [to_jsonable(row) for row in rows]


def commitment_lineage_rows_to_dicts(
    rows: list[CommitmentLineageRow],
) -> list[dict[str, Any]]:
    return [to_jsonable(row) for row in rows]


def recovery_lineage_rows_to_dicts(
    rows: list[RecoveryLineageRow],
) -> list[dict[str, Any]]:
    return [to_jsonable(row) for row in rows]


def unresolved_commitment_report_to_dict(
    report: UnresolvedCommitmentReport,
) -> dict[str, Any]:
    data = to_jsonable(report)
    data["count"] = report.count
    data["commitment_ids"] = report.commitment_ids
    return data


def _fmt(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(to_jsonable(value), sort_keys=True)

    return str(value)


def _cell(value: Any) -> str:
    return _fmt(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for row in rows:
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")

    return lines


def render_active_commitment_audit_markdown(
    rows: list[ActiveCommitmentAuditRow],
    *,
    title: str = "Active Commitment Audit",
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- total commitments: `{len(rows)}`",
        f"- unresolved commitments: `{sum(1 for row in rows if row.is_unresolved)}`",
        "",
    ]

    lines.extend(
        _table(
            [
                "commitment_id",
                "type",
                "status",
                "unresolved",
                "workflow_id",
                "records",
                "first_record",
                "last_record",
                "last_action",
            ],
            [
                [
                    row.commitment_id,
                    row.commitment_type,
                    row.status,
                    row.is_unresolved,
                    row.workflow_id,
                    row.record_count,
                    row.first_record_id,
                    row.last_record_id,
                    row.last_action_type,
                ]
                for row in rows
            ],
        )
    )

    lines.append("")
    return "\n".join(lines)


def render_unresolved_commitments_markdown(
    report: UnresolvedCommitmentReport,
    *,
    title: str = "Unresolved Commitments",
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- tenant_id: `{report.tenant_id}`",
        f"- workflow_id: `{report.workflow_id}`",
        f"- unresolved count: `{report.count}`",
        "",
    ]

    lines.extend(
        _table(
            [
                "commitment_id",
                "type",
                "status",
                "workflow_id",
                "records",
                "last_record",
                "last_action",
                "description",
            ],
            [
                [
                    row.commitment_id,
                    row.commitment_type,
                    row.status,
                    row.workflow_id,
                    row.record_count,
                    row.last_record_id,
                    row.last_action_type,
                    row.description,
                ]
                for row in report.rows
            ],
        )
    )

    lines.append("")
    return "\n".join(lines)


def render_commitment_lineage_markdown(
    rows: list[CommitmentLineageRow],
    *,
    title: str = "Commitment Lineage",
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- lineage records: `{len(rows)}`",
        "",
    ]

    lines.extend(
        _table(
            [
                "commitment_id",
                "record_id",
                "action_type",
                "status_before",
                "status_after",
                "workflow_id",
                "tx_group_id",
                "log_position",
                "timestamp",
            ],
            [
                [
                    row.commitment_id,
                    row.record_id,
                    row.action_type,
                    row.status_before,
                    row.status_after,
                    row.workflow_id,
                    row.tx_group_id,
                    row.log_position,
                    row.timestamp,
                ]
                for row in rows
            ],
        )
    )

    lines.append("")
    return "\n".join(lines)


def render_recovery_lineage_markdown(
    rows: list[RecoveryLineageRow],
    *,
    title: str = "Recovery Lineage",
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- recovery records: `{len(rows)}`",
        "",
    ]

    lines.extend(
        _table(
            [
                "commitment_id",
                "record_id",
                "action_type",
                "status_before",
                "status_after",
                "proposal_ref",
                "package_id",
                "admitted_records",
                "rejection_code",
                "log_position",
            ],
            [
                [
                    row.commitment_id,
                    row.record_id,
                    row.action_type,
                    row.status_before,
                    row.status_after,
                    row.proposal_ref,
                    row.package_id,
                    row.admitted_record_ids,
                    row.rejection_code,
                    row.log_position,
                ]
                for row in rows
            ],
        )
    )

    lines.append("")
    return "\n".join(lines)


def write_json_report(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(to_jsonable(data), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_markdown_report(path: str | Path, markdown: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path
