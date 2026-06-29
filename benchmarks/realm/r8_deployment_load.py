#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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


def post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any], float]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        status = int(exc.code)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}

    return status, data, elapsed_ms


def make_payload(i: int) -> tuple[dict[str, Any], bool]:
    """Return payload and whether it is valid under the test C."""
    mode = i % 5

    if mode in (0, 1, 2):
        return (
            {
                "tenant": "r8-load",
                "workflow": "deployment",
                "entity": f"entity-{i % 20}",
                "operation": "valid_transition",
                "payload": {"valid_under_c": True, "value": i},
                "idempotency_key": f"valid-{i}",
                "conflict_scope": f"entity-{i % 20}",
            },
            True,
        )

    if mode == 3:
        return (
            {
                "tenant": "r8-load",
                "workflow": "deployment",
                "entity": f"entity-{i % 20}",
                "operation": "valid_transition",
                "payload": {"valid_under_c": False, "value": i},
                "idempotency_key": f"invalid-{i}",
                "conflict_scope": f"entity-{i % 20}",
            },
            False,
        )

    return (
        {
            "tenant": "r8-load",
            "workflow": "deployment",
            "entity": f"entity-{i % 20}",
            "operation": "raw_append",
            "payload": {"direct_commit": True, "value": i},
            "idempotency_key": f"bypass-{i}",
            "conflict_scope": f"entity-{i % 20}",
        },
        False,
    )


def run_setting(base_url: str, total: int, workers: int, timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/proposals"
    rows: list[dict[str, Any]] = []

    def one(i: int) -> dict[str, Any]:
        payload, valid = make_payload(i)
        status, data, elapsed_ms = post_json(url, payload, timeout)

        accepted = bool(data.get("accepted")) if isinstance(data, dict) else False
        invalid_commit = accepted and not valid

        return {
            "i": i,
            "status": status,
            "valid_under_c": valid,
            "accepted": accepted,
            "invalid_commit": invalid_commit,
            "latency_ms": elapsed_ms,
            "reason": data.get("reason") if isinstance(data, dict) else None,
        }

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, i) for i in range(total)]
        for fut in concurrent.futures.as_completed(futs):
            rows.append(fut.result())
    elapsed_s = time.perf_counter() - t0

    latencies = [float(r["latency_ms"]) for r in rows]
    accepted = sum(1 for r in rows if r["accepted"])
    rejected = sum(1 for r in rows if not r["accepted"])
    invalid_commits = sum(1 for r in rows if r["invalid_commit"])
    errors = sum(1 for r in rows if int(r["status"]) >= 500)
    malformed = sum(1 for r in rows if int(r["status"]) >= 400)

    return {
        "workers": workers,
        "submitted": total,
        "accepted": accepted,
        "rejected": rejected,
        "http_4xx_or_5xx": malformed,
        "http_5xx": errors,
        "invalid_commits": invalid_commits,
        "elapsed_s": elapsed_s,
        "throughput_proposals_per_min": total / elapsed_s * 60.0 if elapsed_s > 0 else None,
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "latency_max_ms": max(latencies) if latencies else None,
        "rows": rows,
    }


def write_outputs(outdir: Path, summaries: list[dict[str, Any]]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    summary_rows = [
        {k: v for k, v in s.items() if k != "rows"}
        for s in summaries
    ]

    csv_path = outdir / "r8_deployment_load_summary.csv"
    json_path = outdir / "r8_deployment_load_summary.json"
    md_path = outdir / "r8_deployment_load_report.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    json_path.write_text(json.dumps(summaries, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# R8 Deployment Load Report\n")
    lines.append("This report exercises the R8 deployment service over HTTP. It is a deployment smoke/load audit, not a production load test.\n")
    lines.append("| Workers | Submitted | Accepted | Rejected | Invalid commits | Latency p50/p95 ms | Throughput proposals/min |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for s in summary_rows:
        lines.append(
            f"| {s['workers']} | {s['submitted']} | {s['accepted']} | {s['rejected']} | "
            f"{s['invalid_commits']} | {s['latency_p50_ms']:.3f} / {s['latency_p95_ms']:.3f} | "
            f"{s['throughput_proposals_per_min']:.2f} |"
        )

    lines.append("\nExpected safety criterion: invalid commits must remain 0 at every worker setting.\n")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8088")
    parser.add_argument("--total", type=int, default=200)
    parser.add_argument("--workers", default="1,4,8,16")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--outdir", default="benchmarks/realm/reports/r8_deployment")
    args = parser.parse_args()

    worker_values = [int(x.strip()) for x in args.workers.split(",") if x.strip()]
    summaries = [
        run_setting(args.base_url, args.total, w, args.timeout)
        for w in worker_values
    ]

    write_outputs(Path(args.outdir), summaries)

    bad = [s for s in summaries if s["invalid_commits"] != 0 or s["http_5xx"] != 0]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
