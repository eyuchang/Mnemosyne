from __future__ import annotations

import json
from pathlib import Path


def test_maple_lcrp_table_matches_summary_columns() -> None:
    table = Path("reports/paper/aaai_lcrp/table6_maple_lcrp_containment.tex").read_text()
    summary = json.loads(Path("results/paper/aaai_lcrp/maple_lcrp_containment_summary.json").read_text())

    assert "Setup" in table
    assert "$H$" in table
    assert "$J$" in table
    assert "\\begin{tabular}{lrrrrrrrrr}" in table

    lcrp = summary["methods"]["lcrp"]
    global_recompute = summary["methods"]["global_recompute"]

    lcrp_j = lcrp["avg_delta_makespan"] + lcrp["avg_operational_overhead_score"]
    global_j = global_recompute["avg_delta_makespan"] + global_recompute["avg_operational_overhead_score"]

    assert f"{lcrp_j:.2f}" in table
    assert f"{global_j:.2f}" in table
    assert summary["pass"] is True
