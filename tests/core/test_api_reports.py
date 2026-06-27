from __future__ import annotations

import json
from datetime import datetime, timezone

from mnemosyne.api.audit import (
    ActiveCommitmentAuditRow,
    CommitmentLineageRow,
    RecoveryLineageRow,
    UnresolvedCommitmentReport,
)
from mnemosyne.api.reports import (
    active_commitment_audit_rows_to_dicts,
    commitment_lineage_rows_to_dicts,
    recovery_lineage_rows_to_dicts,
    render_active_commitment_audit_markdown,
    render_commitment_lineage_markdown,
    render_recovery_lineage_markdown,
    render_unresolved_commitments_markdown,
    to_jsonable,
    unresolved_commitment_report_to_dict,
    write_json_report,
    write_markdown_report,
)


TS = datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc)


def audit_row() -> ActiveCommitmentAuditRow:
    return ActiveCommitmentAuditRow(
        commitment_id="c1",
        commitment_type="dependency_guard",
        status="proposed",
        is_unresolved=True,
        description="Report API commitment.",
        dependency_scope={"entity_id": "domain:entity:1"},
        workflow_id="workflow:r51-report",
        record_count=3,
        first_record_id="rid:register",
        last_record_id="rid:proposal",
        last_action_type="commitment_proposal_emitted",
        last_log_position=7,
    )


def lineage_row() -> CommitmentLineageRow:
    return CommitmentLineageRow(
        commitment_id="c1",
        record_id="rid:proposal",
        action_type="commitment_proposal_emitted",
        status_before="fired",
        status_after="proposed",
        payload={"proposal_ref": "proposal:r51"},
        workflow_id="workflow:r51-report",
        tx_group_id="tx:r51-report",
        log_position=7,
        local_log_position=7,
        timestamp=TS,
    )


def recovery_row() -> RecoveryLineageRow:
    return RecoveryLineageRow(
        commitment_id="c1",
        record_id="rid:proposal",
        action_type="commitment_proposal_emitted",
        status_before="fired",
        status_after="proposed",
        proposal_ref="proposal:r51",
        package_id="pkg:r51",
        admitted_record_ids=["rid:domain"],
        rejection_code=None,
        payload={"proposal_ref": "proposal:r51"},
        workflow_id="workflow:r51-report",
        tx_group_id="tx:r51-report",
        log_position=7,
        timestamp=TS,
    )


def test_report_to_jsonable_converts_dataclasses_and_datetime():
    data = to_jsonable(recovery_row())

    assert data["commitment_id"] == "c1"
    assert data["timestamp"] == "2026-06-26T12:00:00+00:00"
    assert data["admitted_record_ids"] == ["rid:domain"]


def test_report_dict_converters_are_json_serializable():
    audit = active_commitment_audit_rows_to_dicts([audit_row()])
    lineage = commitment_lineage_rows_to_dicts([lineage_row()])
    recovery = recovery_lineage_rows_to_dicts([recovery_row()])
    unresolved = unresolved_commitment_report_to_dict(
        UnresolvedCommitmentReport(
            tenant_id="tenant:r51-report",
            workflow_id="workflow:r51-report",
            rows=[audit_row()],
        )
    )

    encoded = json.dumps(
        {
            "audit": audit,
            "lineage": lineage,
            "recovery": recovery,
            "unresolved": unresolved,
        },
        sort_keys=True,
    )

    assert "proposal:r51" in encoded
    assert "tenant:r51-report" in encoded


def test_render_active_commitment_audit_markdown():
    markdown = render_active_commitment_audit_markdown(
        [audit_row()],
        title="R5.1 Active Commitment Audit",
    )

    assert "# R5.1 Active Commitment Audit" in markdown
    assert "total commitments: `1`" in markdown
    assert "unresolved commitments: `1`" in markdown
    assert "commitment_proposal_emitted" in markdown
    assert "Report API commitment." not in markdown


def test_render_unresolved_commitments_markdown():
    report = UnresolvedCommitmentReport(
        tenant_id="tenant:r51-report",
        workflow_id="workflow:r51-report",
        rows=[audit_row()],
    )

    markdown = render_unresolved_commitments_markdown(report)

    assert "# Unresolved Commitments" in markdown
    assert "unresolved count: `1`" in markdown
    assert "Report API commitment." in markdown


def test_render_lineage_markdown_reports():
    commitment_markdown = render_commitment_lineage_markdown([lineage_row()])
    recovery_markdown = render_recovery_lineage_markdown([recovery_row()])

    assert "Commitment Lineage" in commitment_markdown
    assert "commitment_proposal_emitted" in commitment_markdown
    assert "2026-06-26T12:00:00+00:00" in commitment_markdown

    assert "Recovery Lineage" in recovery_markdown
    assert "proposal:r51" in recovery_markdown
    assert "pkg:r51" in recovery_markdown
    assert "rid:domain" in recovery_markdown


def test_write_json_and_markdown_reports(tmp_path):
    json_path = tmp_path / "reports" / "audit.json"
    markdown_path = tmp_path / "reports" / "audit.md"

    write_json_report(json_path, [audit_row()])
    write_markdown_report(
        markdown_path,
        render_active_commitment_audit_markdown([audit_row()]),
    )

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    rendered = markdown_path.read_text(encoding="utf-8")

    assert loaded[0]["commitment_id"] == "c1"
    assert "# Active Commitment Audit" in rendered
