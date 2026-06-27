# File: mnemosyne/benchmarks/realm_runner.py
#
# Purpose:
#   Command-line runner for local deterministic REALM-style benchmark fixtures.
#
# Stage:
#   Stage 1.5R-CLI adds a reproducible non-pytest benchmark entry point.
#
# Example:
#   python -m mnemosyne.benchmarks.realm_runner \
#     --cases benchmarks/realm/cases \
#     --out results/realm/realm_run.jsonl
#
# Rule:
#   Benchmark fixtures provide scenarios.
#   Mnemosyne owns transactional truth through Validator -> Store -> StateView.

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from mnemosyne.apps import AppRegistry
from mnemosyne.apps.campus_tour import CampusTourApp
from mnemosyne.apps.jssp import JSSPApp
from mnemosyne.apps.rideshare import RideshareApp
from mnemosyne.apps.travel import TravelApp
from mnemosyne.benchmarks.results import BenchmarkRunResult, benchmark_result_to_jsonl
from mnemosyne.benchmarks.runner import load_benchmark_cases, run_realm_cases
from mnemosyne.core.validation import Validator
from mnemosyne.store.sqlite import SQLiteStore


@dataclass(frozen=True)
class RealmCliSummary:
    cases: int
    passed: int
    failed: int
    output_path: str | None


def make_default_store() -> SQLiteStore:
    """Create an isolated local store for one benchmark case."""
    return SQLiteStore()


def make_default_validator() -> Validator:
    """Create the default local validator used by current benchmark fixtures."""
    registry = AppRegistry()
    registry.register(RideshareApp())
    registry.register(TravelApp())
    registry.register(JSSPApp())
    registry.register(CampusTourApp())

    return Validator(
        registry.build_fsm_registry(),
        registry.build_constraint_registry(),
    )


def write_jsonl_results(
    *,
    results: Sequence[BenchmarkRunResult],
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(benchmark_result_to_jsonl(result))
            file.write("\n")


async def run_realm_cli_async(
    *,
    case_dir: str | Path,
    output_path: str | Path | None,
) -> tuple[list[BenchmarkRunResult], RealmCliSummary]:
    cases = load_benchmark_cases(case_dir)

    results = await run_realm_cases(
        cases=cases,
        store_factory=make_default_store,
        validator_factory=make_default_validator,
    )

    if output_path is not None:
        write_jsonl_results(results=results, output_path=output_path)

    passed = sum(1 for result in results if result.ok)
    failed = len(results) - passed

    return results, RealmCliSummary(
        cases=len(results),
        passed=passed,
        failed=failed,
        output_path=str(output_path) if output_path is not None else None,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local deterministic REALM-style benchmark fixtures.",
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/realm/cases",
        help="Directory containing REALM-style JSON fixture files.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional JSONL output path for benchmark results.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Exit with status 0 even when one or more benchmark cases fail.",
    )

    return parser


def print_summary(summary: RealmCliSummary) -> None:
    print(
        "REALM run complete: "
        f"{summary.passed}/{summary.cases} passed, "
        f"{summary.failed} failed"
    )

    if summary.output_path is not None:
        print(f"Results written to: {summary.output_path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    _results, summary = asyncio.run(
        run_realm_cli_async(
            case_dir=args.cases,
            output_path=args.out,
        )
    )

    print_summary(summary)

    if summary.failed and not args.allow_failures:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())