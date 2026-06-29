#!/usr/bin/env python3
"""
RQ9b real infrastructure benchmark.

This benchmark does NOT use the RQ9 oracle as the ATP implementation.
It runs real Mnemosyne infrastructure paths discovered from the repository:

  - kernel admission
  - runtime admission facade
  - validator rejection before commit
  - StateView / effective-state projection
  - compensation projection
  - dependency / orphaning validator checks
  - validated active recovery
  - Temporal activity boundary

It also runs the RQ9 state-of-practice comparator test to preserve the RQ9
safety baseline, but labels it as semantic comparator, not ATP runtime.

Outputs:
  benchmarks/realm/reports/rq9b_real_infra_summary.csv
  benchmarks/realm/reports/rq9b_real_infra_summary.json
  benchmarks/realm/reports/rq9b_real_infra_report.md
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import os
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any


# Real infrastructure pytest workloads selected from discovery output.
# These should exist in your repo according to the discovery run.
DEFAULT_SEMANTIC_COMPARATOR_NODES = [
    "tests/experiments/test_rq9_state_of_practice_comparator.py::test_rq9_state_of_practice_comparator",
]

DEFAULT_ATP_INFRA_NODES = [
    # Kernel/runtime admission and commit boundary.
    "tests/runtime/test_kernel_admission.py::test_accept_via_kernel_records_accepted_and_committed",
    "tests/runtime/test_kernel_admission.py::test_reject_before_commit_never_calls_kernel",
    "tests/runtime/test_kernel_admission.py::test_validator_rejection_records_rejected_without_committed_rids",
    "tests/runtime/test_kernel_admission.py::test_commit_failure_records_rejected_without_committed_truth",
    "tests/runtime/test_runtime_admission.py::test_admission_facade_accepts_submitted_proposal_with_commit_rids",
    "tests/runtime/test_runtime_admission.py::test_admission_facade_rejects_submitted_proposal",

    # Projection / effective StateView / compensation.
    "tests/core/test_cross_entity_compensation_projection.py::test_cross_entity_compensation_refreshes_compensated_entity_projection",
    "tests/core/test_compensation_projection.py::test_compensation_preserves_ctl_history_but_updates_effective_projection",
    "tests/core/test_compensation_projection.py::test_supersession_preserves_ctl_history_but_updates_effective_projection",
    "tests/core/test_state_view_api.py::test_get_state_view_uses_only_effective_records_after_compensation",

    # Validator / orphaning / dependency-closure checks.
    "tests/core/test_review_a_fixes.py::test_bl2_validator_rejects_orphaning_compensation",
    "tests/core/test_review_a_fixes.py::test_im5_validator_rejects_chain_breaking_compensation",
    "tests/core/test_review_a_fixes.py::test_compensation_target_must_exist",
    "tests/core/test_review_a_fixes.py::test_legitimate_tail_collapse_compensation_still_passes",

    # Runtime recovery and validation paths.
    "tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_commits_recovery_candidate_through_validator",
    "tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_sequentially_admits_retry_candidates",
    "tests/core/test_runtime_local_active_recovery_validation.py::test_validation_failure_commits_no_recovery_candidate",
    "tests/core/test_runtime_local_active_recovery_validation.py::test_validated_executor_still_never_mutates_domain_state",

    # Temporal/activity boundary.
    "tests/core/test_temporal_activity_boundary.py::test_temporal_activity_boundary_validates_commits_and_returns_stateview",
    "tests/core/test_temporal_activity_boundary.py::test_temporal_runtime_orchestrates_but_activity_boundary_commits_truth",
]


SITE_CUSTOMIZE = r'''
import atexit
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

ENABLED = os.environ.get("RQ9B_TRACE") == "1"
TRACE_FILE = os.environ.get("RQ9B_TRACE_FILE")
CONDITION = os.environ.get("RQ9B_CONDITION", "unknown")
RUN_ID = os.environ.get("RQ9B_RUN_ID", "unknown")
REPO_ROOT = Path(os.environ.get("RQ9B_REPO_ROOT", os.getcwd())).resolve()

REGEX = {
    "admission": r"(admit|admission|admissible|authorize|proposal|kernel)",
    "commit": r"(^|[._])(commit|committer|finalize|apply|accepted)($|[._])",
    "projection": r"(project|projection|effective|stateview|state_view|get_state_view|replay)",
    "validation": r"(validate|validation|validator|invariant|check|reject|guard)",
    "compensation": r"(compensat|rollback|repair|recover|recovery|orphan|supersession)",
    "runtime": r"(runtime|workflow|temporal|activity|executor|session|driver)",
}
COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in REGEX.items()}

EVENTS = []
STACK = {}
LOCK = threading.Lock()
MAX_EVENTS = int(os.environ.get("RQ9B_MAX_TRACE_EVENTS", "500000"))

def _inside_repo(filename):
    try:
        p = Path(filename).resolve()
        return str(p).startswith(str(REPO_ROOT))
    except Exception:
        return False

def _category(module, func, filename):
    if not _inside_repo(filename):
        return None

    name = f"{module}.{func}.{filename}"
    hits = [cat for cat, rx in COMPILED.items() if rx.search(name)]
    if not hits:
        return None

    # Assign a primary category. Keep this stable and interpretable.
    priority = ["admission", "commit", "projection", "validation", "compensation", "runtime"]
    for p in priority:
        if p in hits:
            return p
    return hits[0]

def _profile(frame, event, arg):
    if not ENABLED or not TRACE_FILE:
        return
    if event not in ("call", "return", "exception"):
        return

    code = frame.f_code
    filename = code.co_filename
    func = code.co_name
    module = frame.f_globals.get("__name__", "")
    tid = threading.get_ident()
    key = (tid, id(frame))

    if event == "call":
        cat = _category(module, func, filename)
        if cat is None:
            return
        STACK[key] = (cat, time.perf_counter_ns(), module, func, filename, code.co_firstlineno)
        return

    item = STACK.pop(key, None)
    if item is None:
        return

    cat, start, module, func, filename, line = item
    duration_ns = time.perf_counter_ns() - start

    rec = {
        "condition": CONDITION,
        "run_id": RUN_ID,
        "category": cat,
        "duration_ns": duration_ns,
        "module": module,
        "function": func,
        "file": filename,
        "line": line,
        "thread": tid,
    }

    with LOCK:
        if len(EVENTS) < MAX_EVENTS:
            EVENTS.append(rec)

def _flush():
    if not TRACE_FILE:
        return
    try:
        Path(TRACE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            for rec in EVENTS:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception as e:
        sys.stderr.write(f"[rq9b trace flush failed] {e}\n")

if ENABLED and TRACE_FILE:
    sys.setprofile(_profile)
    threading.setprofile(_profile)
    atexit.register(_flush)
'''


def percentile(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def fmt(v: Any, digits: int = 3) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def make_trace_hook() -> Path:
    d = Path(tempfile.mkdtemp(prefix="rq9b_sitecustomize_"))
    (d / "sitecustomize.py").write_text(SITE_CUSTOMIZE, encoding="utf-8")
    return d


def run_pytest_once(
    *,
    condition: str,
    run_id: int,
    nodes: list[str],
    outdir: Path,
    repo_root: Path,
    hook_dir: Path,
    extra_args: list[str],
) -> dict[str, Any]:
    trace_file = outdir / "traces" / f"{condition}_run{run_id:04d}.jsonl"
    log_file = outdir / "logs" / f"{condition}_run{run_id:04d}.log"

    env = os.environ.copy()
    env["RQ9B_TRACE"] = "1"
    env["RQ9B_TRACE_FILE"] = str(trace_file)
    env["RQ9B_CONDITION"] = condition
    env["RQ9B_RUN_ID"] = str(run_id)
    env["RQ9B_REPO_ROOT"] = str(repo_root)

    old_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(hook_dir) + (os.pathsep + old_pp if old_pp else "")

    cmd = [sys.executable, "-m", "pytest", "-q"] + nodes + extra_args

    t0 = time.perf_counter()
    cp = subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    t1 = time.perf_counter()

    combined = cp.stdout + "\n" + cp.stderr
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(
        "$ " + " ".join(shlex.quote(x) for x in cmd) + "\n\n" + combined,
        encoding="utf-8",
    )

    return {
        "condition": condition,
        "run_id": run_id,
        "ok": cp.returncode == 0,
        "returncode": cp.returncode,
        "duration_ms": (t1 - t0) * 1000.0,
        "node_count": len(nodes),
        "log_file": str(log_file),
        "trace_file": str(trace_file),
    }


def read_trace_records(trace_dir: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted(trace_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def summarize_trace(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for r in records:
        key = (r["condition"], r["category"])
        grouped.setdefault(key, []).append(r["duration_ns"] / 1_000_000.0)

    summary = {}
    for key, xs in grouped.items():
        summary[key] = {
            "count": len(xs),
            "total_ms": sum(xs),
            "mean_ms": statistics.fmean(xs) if xs else None,
            "p50_ms": percentile(xs, 0.50),
            "p95_ms": percentile(xs, 0.95),
        }
    return summary


def condition_summary(
    *,
    condition: str,
    rows: list[dict[str, Any]],
    trace_summary: dict[tuple[str, str], dict[str, Any]],
    elapsed_s: float,
    unit_count: int,
) -> dict[str, Any]:
    xs = [r["duration_ms"] for r in rows]
    passed = sum(1 for r in rows if r["ok"])
    runs = len(rows)

    def span(cat: str, field: str) -> float | None:
        return trace_summary.get((condition, cat), {}).get(field)

    total_e2e_ms = sum(xs)
    projection_total = span("projection", "total_ms") or 0.0
    validation_total = span("validation", "total_ms") or 0.0
    compensation_total = span("compensation", "total_ms") or 0.0
    admission_total = span("admission", "total_ms") or 0.0
    commit_total = span("commit", "total_ms") or 0.0

    return {
        "condition": condition,
        "runs": runs,
        "passed_runs": passed,
        "unit_count_per_run": unit_count,
        "duration_p50_ms": percentile(xs, 0.50),
        "duration_p95_ms": percentile(xs, 0.95),
        "admission_p50_ms": span("admission", "p50_ms"),
        "admission_p95_ms": span("admission", "p95_ms"),
        "commit_p50_ms": span("commit", "p50_ms"),
        "commit_p95_ms": span("commit", "p95_ms"),
        "projection_p50_ms": span("projection", "p50_ms"),
        "projection_p95_ms": span("projection", "p95_ms"),
        "validation_p50_ms": span("validation", "p50_ms"),
        "validation_p95_ms": span("validation", "p95_ms"),
        "compensation_p50_ms": span("compensation", "p50_ms"),
        "compensation_p95_ms": span("compensation", "p95_ms"),
        "admission_commit_overhead_frac": (admission_total + commit_total) / total_e2e_ms if total_e2e_ms else None,
        "projection_validation_overhead_frac": (projection_total + validation_total) / total_e2e_ms if total_e2e_ms else None,
        "compensation_overhead_frac": compensation_total / total_e2e_ms if total_e2e_ms else None,
        "throughput_units_per_min": (passed * unit_count / elapsed_s * 60.0) if elapsed_s > 0 else None,
    }


def write_outputs(
    *,
    outdir: Path,
    summaries: list[dict[str, Any]],
    raw_runs: list[dict[str, Any]],
    trace_summary: dict[tuple[str, str], dict[str, Any]],
    semantic_nodes: list[str],
    atp_nodes: list[str],
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "rq9b_real_infra_summary.csv"
    json_path = outdir / "rq9b_real_infra_summary.json"
    md_path = outdir / "rq9b_real_infra_report.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        w.writeheader()
        for s in summaries:
            w.writerow(s)

    json_path.write_text(json.dumps({
        "summary": summaries,
        "raw_runs": raw_runs,
        "trace_summary": {f"{k[0]}::{k[1]}": v for k, v in trace_summary.items()},
        "semantic_comparator_nodes": semantic_nodes,
        "atp_infra_nodes": atp_nodes,
    }, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# RQ9b Real Infrastructure Runtime-Cost Report\n")
    lines.append("This run benchmarks real pytest infrastructure paths, not the RQ9 ATP oracle.\n")
    lines.append("## Summary\n")
    lines.append("| Condition | Passed/Runs | Unit Count/Run | End-to-End p50/p95 ms | Admission p50/p95 ms | Commit p50/p95 ms | Projection p50/p95 ms | Validation p50/p95 ms | Projection+Validation Overhead | Throughput units/min |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for s in summaries:
        pv = "NA" if s["projection_validation_overhead_frac"] is None else f"{100*s['projection_validation_overhead_frac']:.2f}%"
        lines.append(
            f"| {s['condition']} | {s['passed_runs']}/{s['runs']} | {s['unit_count_per_run']} | "
            f"{fmt(s['duration_p50_ms'])}/{fmt(s['duration_p95_ms'])} | "
            f"{fmt(s['admission_p50_ms'])}/{fmt(s['admission_p95_ms'])} | "
            f"{fmt(s['commit_p50_ms'])}/{fmt(s['commit_p95_ms'])} | "
            f"{fmt(s['projection_p50_ms'])}/{fmt(s['projection_p95_ms'])} | "
            f"{fmt(s['validation_p50_ms'])}/{fmt(s['validation_p95_ms'])} | "
            f"{pv} | {fmt(s['throughput_units_per_min'], 2)} |"
        )

    lines.append("\n## Workloads\n")
    lines.append("### Semantic workflow/saga comparator\n")
    for n in semantic_nodes:
        lines.append(f"- `{n}`")
    lines.append("\n### ATP real infrastructure workload\n")
    for n in atp_nodes:
        lines.append(f"- `{n}`")

    lines.append("\n## Interpretation guardrail\n")
    lines.append(
        "The semantic comparator workload preserves the RQ9 state-of-practice safety baseline. "
        "The ATP workload measures real repository infrastructure paths: admission, commit boundary, "
        "effective-state projection, validation, compensation, recovery, and Temporal boundary. "
        "If any pytest nodes fail, do not use the timing table until the failure is fixed."
    )

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nWrote:")
    print(f"  {csv_path}")
    print(f"  {json_path}")
    print(f"  {md_path}")


def split_nodes(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--outdir", default="benchmarks/realm/reports")
    ap.add_argument("--pytest-args", default="-s")
    ap.add_argument("--semantic-nodes", default="")
    ap.add_argument("--atp-nodes", default="")
    args = ap.parse_args()

    repo_root = Path.cwd().resolve()
    outdir = Path(args.outdir)
    (outdir / "logs").mkdir(parents=True, exist_ok=True)
    (outdir / "traces").mkdir(parents=True, exist_ok=True)

    semantic_nodes = split_nodes(args.semantic_nodes) if args.semantic_nodes else DEFAULT_SEMANTIC_COMPARATOR_NODES
    atp_nodes = split_nodes(args.atp_nodes) if args.atp_nodes else DEFAULT_ATP_INFRA_NODES
    extra_args = shlex.split(args.pytest_args)

    hook_dir = make_trace_hook()

    all_runs: list[dict[str, Any]] = []
    elapsed: dict[str, float] = {}

    conditions = [
        ("workflow_saga_semantic_comparator", semantic_nodes),
        ("atp_real_infrastructure", atp_nodes),
    ]

    for condition, nodes in conditions:
        print(f"\n=== {condition}: {len(nodes)} pytest node(s), repeats={args.repeats}, workers={args.workers} ===")
        t0 = time.perf_counter()
        rows = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [
                ex.submit(
                    run_pytest_once,
                    condition=condition,
                    run_id=i,
                    nodes=nodes,
                    outdir=outdir,
                    repo_root=repo_root,
                    hook_dir=hook_dir,
                    extra_args=extra_args,
                )
                for i in range(args.repeats)
            ]
            for fut in concurrent.futures.as_completed(futs):
                row = fut.result()
                rows.append(row)
                all_runs.append(row)
                status = "PASS" if row["ok"] else "FAIL"
                print(f"{condition} run={row['run_id']} {status} {row['duration_ms']:.1f} ms")
        elapsed[condition] = time.perf_counter() - t0

    trace_records = read_trace_records(outdir / "traces")
    trace_summary = summarize_trace(trace_records)

    summaries = []
    summaries.append(condition_summary(
        condition="workflow_saga_semantic_comparator",
        rows=[r for r in all_runs if r["condition"] == "workflow_saga_semantic_comparator"],
        trace_summary=trace_summary,
        elapsed_s=elapsed["workflow_saga_semantic_comparator"],
        unit_count=len(semantic_nodes),
    ))
    summaries.append(condition_summary(
        condition="atp_real_infrastructure",
        rows=[r for r in all_runs if r["condition"] == "atp_real_infrastructure"],
        trace_summary=trace_summary,
        elapsed_s=elapsed["atp_real_infrastructure"],
        unit_count=len(atp_nodes),
    ))

    write_outputs(
        outdir=outdir,
        summaries=summaries,
        raw_runs=all_runs,
        trace_summary=trace_summary,
        semantic_nodes=semantic_nodes,
        atp_nodes=atp_nodes,
    )

    failed = [r for r in all_runs if not r["ok"]]
    if failed:
        print("\nWARNING: Some pytest runs failed. Inspect logs under benchmarks/realm/reports/logs.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
