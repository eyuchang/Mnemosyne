from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mnemosyne.api.audit import (
    ActiveCommitmentAuditRow,
    CommitmentLineageRow,
    RecoveryLineageRow,
    UnresolvedCommitmentReport,
)
from mnemosyne.api.reports import (
    render_active_commitment_audit_markdown,
    render_commitment_lineage_markdown,
    render_recovery_lineage_markdown,
    render_unresolved_commitments_markdown,
    to_jsonable,
    write_json_report,
    write_markdown_report,
)


ReportKind = str


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _audit_row_from_dict(data: dict[str, Any]) -> ActiveCommitmentAuditRow:
    return ActiveCommitmentAuditRow(
        commitment_id=str(data["commitment_id"]),
        commitment_type=str(data["commitment_type"]),
        status=str(data["status"]),
        is_unresolved=bool(data["is_unresolved"]),
        description=str(data.get("description", "")),
        dependency_scope=dict(data.get("dependency_scope", {})),
        workflow_id=data.get("workflow_id"),
        record_count=int(data.get("record_count", 0)),
        first_record_id=data.get("first_record_id"),
        last_record_id=data.get("last_record_id"),
        last_action_type=data.get("last_action_type"),
        last_log_position=data.get("last_log_position"),
    )


def _commitment_lineage_row_from_dict(data: dict[str, Any]) -> CommitmentLineageRow:
    return CommitmentLineageRow(
        commitment_id=str(data["commitment_id"]),
        record_id=str(data["record_id"]),
        action_type=str(data["action_type"]),
        status_before=str(data["status_before"]),
        status_after=str(data["status_after"]),
        payload=dict(data.get("payload", {})),
        workflow_id=data.get("workflow_id"),
        tx_group_id=data.get("tx_group_id"),
        log_position=data.get("log_position"),
        local_log_position=data.get("local_log_position"),
        timestamp=None,
    )


def _recovery_lineage_row_from_dict(data: dict[str, Any]) -> RecoveryLineageRow:
    admitted = data.get("admitted_record_ids", [])
    if not isinstance(admitted, list):
        admitted = [admitted]

    return RecoveryLineageRow(
        commitment_id=str(data["commitment_id"]),
        record_id=str(data["record_id"]),
        action_type=str(data["action_type"]),
        status_before=str(data["status_before"]),
        status_after=str(data["status_after"]),
        proposal_ref=data.get("proposal_ref"),
        package_id=data.get("package_id"),
        admitted_record_ids=[str(item) for item in admitted],
        rejection_code=data.get("rejection_code"),
        payload=dict(data.get("payload", {})),
        workflow_id=data.get("workflow_id"),
        tx_group_id=data.get("tx_group_id"),
        log_position=data.get("log_position"),
        timestamp=None,
    )


def _rows_payload(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        return data
    raise ValueError("expected a list of rows or an object with a rows field")


def render_report(
    *,
    kind: ReportKind,
    data: Any,
    output_format: str,
    title: str | None = None,
) -> str:
    if kind == "active-commitments":
        rows = [_audit_row_from_dict(row) for row in _rows_payload(data)]
        if output_format == "json":
            return json.dumps(to_jsonable(rows), indent=2, sort_keys=True) + "\n"
        return render_active_commitment_audit_markdown(
            rows,
            title=title or "Active Commitment Audit",
        )

    if kind == "unresolved":
        if not isinstance(data, dict):
            raise ValueError("unresolved report input must be an object")

        rows = [_audit_row_from_dict(row) for row in data.get("rows", [])]
        report = UnresolvedCommitmentReport(
            tenant_id=str(data["tenant_id"]),
            workflow_id=data.get("workflow_id"),
            rows=rows,
        )
        if output_format == "json":
            return json.dumps(to_jsonable(report), indent=2, sort_keys=True) + "\n"
        return render_unresolved_commitments_markdown(
            report,
            title=title or "Unresolved Commitments",
        )

    if kind == "commitment-lineage":
        rows = [_commitment_lineage_row_from_dict(row) for row in _rows_payload(data)]
        if output_format == "json":
            return json.dumps(to_jsonable(rows), indent=2, sort_keys=True) + "\n"
        return render_commitment_lineage_markdown(
            rows,
            title=title or "Commitment Lineage",
        )

    if kind == "recovery-lineage":
        rows = [_recovery_lineage_row_from_dict(row) for row in _rows_payload(data)]
        if output_format == "json":
            return json.dumps(to_jsonable(rows), indent=2, sort_keys=True) + "\n"
        return render_recovery_lineage_markdown(
            rows,
            title=title or "Recovery Lineage",
        )

    raise ValueError(f"unknown report kind: {kind}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mnemosyne-product-report",
        description="Render Mnemosyne product audit reports.",
    )
    parser.add_argument(
        "kind",
        choices=[
            "active-commitments",
            "unresolved",
            "commitment-lineage",
            "recovery-lineage",
        ],
    )
    parser.add_argument("--input", required=True, help="Input JSON file.")
    parser.add_argument("--output", required=True, help="Output report path.")
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format.",
    )
    parser.add_argument("--title", default=None, help="Optional Markdown title.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    data = load_json(args.input)
    rendered = render_report(
        kind=args.kind,
        data=data,
        output_format=args.format,
        title=args.title,
    )

    if args.format == "json":
        write_json_report(args.output, json.loads(rendered))
    else:
        write_markdown_report(args.output, rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
