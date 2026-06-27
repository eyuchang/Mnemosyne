from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.aaai_lcrp.run_lcrp_containment import main


def test_lcrp_containment_outputs():
    assert main() == 0

    raw_csv = Path("results/paper/aaai_lcrp/lcrp_containment_raw.csv")
    summary_json = Path("results/paper/aaai_lcrp/lcrp_containment_summary.json")
    report_md = Path("reports/paper/aaai_lcrp/LCRP_CONTAINMENT_SUMMARY.md")
    table_tex = Path("reports/paper/aaai_lcrp/table6_lcrp_containment.tex")

    assert raw_csv.exists()
    assert summary_json.exists()
    assert report_md.exists()
    assert table_tex.exists()

    rows = list(csv.DictReader(raw_csv.open()))
    assert len(rows) == 6
    assert {row["method"] for row in rows} == {"lcrp", "global_recompute"}
    assert all(row["feasible"] == "True" for row in rows)

    summary = json.loads(summary_json.read_text())
    assert summary["pass"] is True
    assert summary["n_rows"] == 6
    assert set(summary["methods"]) == {"lcrp", "global_recompute"}
