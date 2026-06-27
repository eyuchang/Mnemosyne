from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.realm.scripts.run_thanksgiving_benchmark import run_benchmark
from benchmarks.realm.scripts.run_thanksgiving_recovery_trace import run_recovery_trace

REALM_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ThanksgivingSuiteResult:
    output_root: Path
    files: dict[str, Path]
    p6_feasible: bool
    p9_feasible: bool
    wakeup_count: int
    proposal_count: int
    admitted_repair_count: int


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# Thanksgiving Benchmark Suite Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Suite id: `{report['suite_id']}`")
    lines.append(f"- P6 feasible: {report['summary']['p6_feasible']}")
    lines.append(f"- P9 feasible after repair: {report['summary']['p9_feasible_after_repair']}")
    lines.append(f"- Recovery wakeups: {report['summary']['wakeup_count']}")
    lines.append(f"- Recovery proposals: {report['summary']['proposal_count']}")
    lines.append(f"- Admitted repairs: {report['summary']['admitted_repair_count']}")
    lines.append(f"- Optimality status: {report['summary']['optimality_status']}")
    lines.append("")

    lines.append("## Generated reports")
    lines.append("")
    for item in report["generated_reports"]:
        lines.append(f"- {item['name']}: `{item['path']}`")
    lines.append("")

    lines.append("## Generated solution artifacts")
    lines.append("")
    for item in report["generated_solutions"]:
        lines.append(f"- {item['name']}: `{item['path']}`")
    lines.append("")

    lines.append("## Generated evaluation artifacts")
    lines.append("")
    for item in report["generated_evaluations"]:
        lines.append(f"- {item['name']}: `{item['path']}`")
    lines.append("")

    lines.append("## Generated recovery lifecycle artifacts")
    lines.append("")
    for item in report["generated_recovery_artifacts"]:
        lines.append(f"- {item['name']}: `{item['path']}`")
    lines.append("")

    lines.append("## What this suite demonstrates")
    lines.append("")
    lines.append("- P6 has a deterministic feasible static baseline.")
    lines.append("- P9 has a deterministic feasible repair baseline.")
    lines.append("- The P9 repair is triggered at 10:00, when the delay notice arrives.")
    lines.append("- The repair does not wait until James's original 13:00 arrival.")
    lines.append("- The recovery trace exposes commitments, wakeups, repair proposal, admission, and lineage.")
    lines.append("")

    lines.append("## Current limitations")
    lines.append("")
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")

    return "\n".join(lines)


def run_suite(output_root: str | Path | None = None) -> ThanksgivingSuiteResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT

    benchmark = run_benchmark(root)
    recovery = run_recovery_trace(root)

    suite_report = {
        "schema_version": "thanksgiving_suite_report.v1",
        "suite_id": "thanksgiving_p6_p9_suite",
        "summary": {
            "p6_feasible": benchmark.p6_feasible,
            "p9_feasible_after_repair": benchmark.p9_feasible,
            "wakeup_count": recovery.wakeup_count,
            "proposal_count": recovery.proposal_count,
            "admitted_repair_count": recovery.admitted_repair_count,
            "optimality_status": "feasible_not_proven_optimal",
        },
        "generated_reports": [
            {
                "name": "P6/P9 executable benchmark report",
                "path": "benchmarks/realm/reports/thanksgiving_p6_p9_report.md",
            },
            {
                "name": "P9 recovery trace report",
                "path": "benchmarks/realm/reports/thanksgiving_p9_recovery_trace_report.md",
            },
            {
                "name": "Thanksgiving suite index report",
                "path": "benchmarks/realm/reports/thanksgiving_suite_report.md",
            },
        ],
        "generated_solutions": [
            {
                "name": "P6 static baseline",
                "path": "benchmarks/realm/solutions/p6_thanksgiving_static_baseline.json",
            },
            {
                "name": "P9 dynamic repair baseline",
                "path": "benchmarks/realm/solutions/p9_thanksgiving_dynamic_repair_baseline.json",
            },
        ],
        "generated_evaluations": [
            {
                "name": "P6 static evaluation",
                "path": "benchmarks/realm/evaluations/p6_thanksgiving_static_eval.json",
            },
            {
                "name": "P9 dynamic evaluation",
                "path": "benchmarks/realm/evaluations/p9_thanksgiving_dynamic_eval.json",
            },
            {
                "name": "P9 recovery trace",
                "path": "benchmarks/realm/evaluations/p9_thanksgiving_recovery_trace.json",
            },
        ],
        "generated_recovery_artifacts": [
            {
                "name": "P9 commitments",
                "path": "benchmarks/realm/recovery/p9_thanksgiving_commitments.json",
            },
            {
                "name": "P9 wakeups",
                "path": "benchmarks/realm/recovery/p9_thanksgiving_wakeups.json",
            },
            {
                "name": "P9 repair proposals",
                "path": "benchmarks/realm/recovery/p9_thanksgiving_repair_proposals.json",
            },
            {
                "name": "P9 repair admissions",
                "path": "benchmarks/realm/recovery/p9_thanksgiving_repair_admissions.json",
            },
            {
                "name": "P9 recovery lineage",
                "path": "benchmarks/realm/recovery/p9_thanksgiving_recovery_lineage.json",
            },
        ],
        "limitations": [
            "The suite uses deterministic feasible baselines.",
            "Optimality is not yet proven.",
            "The recovery trace models the Mnemosyne recovery pattern but does not yet call core CTL mutation APIs.",
        ],
    }

    files = {
        "suite_json": root / "reports" / "thanksgiving_suite_report.json",
        "suite_markdown": root / "reports" / "thanksgiving_suite_report.md",
    }

    _write_json(files["suite_json"], suite_report)
    files["suite_markdown"].parent.mkdir(parents=True, exist_ok=True)
    files["suite_markdown"].write_text(
        _render_markdown(suite_report) + "\n",
        encoding="utf-8",
    )

    return ThanksgivingSuiteResult(
        output_root=root,
        files=files,
        p6_feasible=benchmark.p6_feasible,
        p9_feasible=benchmark.p9_feasible,
        wakeup_count=recovery.wakeup_count,
        proposal_count=recovery.proposal_count,
        admitted_repair_count=recovery.admitted_repair_count,
    )


def main() -> None:
    result = run_suite()
    print("R6.6 Thanksgiving benchmark suite")
    print(f"output_root: {result.output_root}")
    print(f"p6_feasible: {result.p6_feasible}")
    print(f"p9_feasible_after_repair: {result.p9_feasible}")
    print(f"wakeups: {result.wakeup_count}")
    print(f"proposals: {result.proposal_count}")
    print(f"admitted_repairs: {result.admitted_repair_count}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
