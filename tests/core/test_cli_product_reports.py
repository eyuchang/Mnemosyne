from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mnemosyne.cli.product_reports import render_report


def audit_rows():
    return [
        {
            "commitment_id": "c1",
            "commitment_type": "dependency_guard",
            "status": "proposed",
            "is_unresolved": True,
            "description": "CLI report commitment.",
            "dependency_scope": {"entity_id": "domain:entity:1"},
            "workflow_id": "workflow:r51-cli",
            "record_count": 3,
            "first_record_id": "rid:register",
            "last_record_id": "rid:proposal",
            "last_action_type": "commitment_proposal_emitted",
            "last_log_position": 7,
        }
    ]


def recovery_rows():
    return [
        {
            "commitment_id": "c1",
            "record_id": "rid:proposal",
            "action_type": "commitment_proposal_emitted",
            "status_before": "fired",
            "status_after": "proposed",
            "proposal_ref": "proposal:r51-cli",
            "package_id": "pkg:r51-cli",
            "admitted_record_ids": ["rid:domain"],
            "rejection_code": None,
            "payload": {"proposal_ref": "proposal:r51-cli"},
            "workflow_id": "workflow:r51-cli",
            "tx_group_id": "tx:r51-cli",
            "log_position": 7,
        }
    ]


def test_render_active_commitments_report_from_json_rows():
    rendered = render_report(
        kind="active-commitments",
        data=audit_rows(),
        output_format="markdown",
        title="CLI Active Commitment Audit",
    )

    assert "# CLI Active Commitment Audit" in rendered
    assert "c1" in rendered
    assert "commitment_proposal_emitted" in rendered


def test_render_unresolved_report_from_json_object():
    rendered = render_report(
        kind="unresolved",
        data={
            "tenant_id": "tenant:r51-cli",
            "workflow_id": "workflow:r51-cli",
            "rows": audit_rows(),
        },
        output_format="markdown",
    )

    assert "# Unresolved Commitments" in rendered
    assert "unresolved count: `1`" in rendered
    assert "CLI report commitment." in rendered


def test_render_recovery_lineage_json_from_rows():
    rendered = render_report(
        kind="recovery-lineage",
        data=recovery_rows(),
        output_format="json",
    )

    payload = json.loads(rendered)

    assert payload[0]["commitment_id"] == "c1"
    assert payload[0]["proposal_ref"] == "proposal:r51-cli"
    assert payload[0]["package_id"] == "pkg:r51-cli"


def test_product_report_cli_writes_markdown(tmp_path: Path):
    input_path = tmp_path / "active.json"
    output_path = tmp_path / "active.md"

    input_path.write_text(
        json.dumps(audit_rows(), sort_keys=True),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mnemosyne.cli.product_reports",
            "active-commitments",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--title",
            "CLI Audit",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    rendered = output_path.read_text(encoding="utf-8")

    assert "# CLI Audit" in rendered
    assert "c1" in rendered
    assert "commitment_proposal_emitted" in rendered


def test_product_report_cli_writes_json(tmp_path: Path):
    input_path = tmp_path / "recovery.json"
    output_path = tmp_path / "recovery.normalized.json"

    input_path.write_text(
        json.dumps(recovery_rows(), sort_keys=True),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mnemosyne.cli.product_reports",
            "recovery-lineage",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload[0]["record_id"] == "rid:proposal"
    assert payload[0]["admitted_record_ids"] == ["rid:domain"]
