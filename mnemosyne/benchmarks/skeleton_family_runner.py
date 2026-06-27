# File: mnemosyne/benchmarks/skeleton_family_runner.py
#
# Purpose:
#   Report-only runner for R2.7 benchmark-family skeleton fixtures.
#
# Design rule:
#   Skeleton fixtures are representation probes.
#   They do not invoke solvers, validators, Store, CTL, or the commit path.

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


DEFAULT_CASE_DIRS = [
    Path("benchmarks/realm/p2_skeleton"),
    Path("benchmarks/realm/p3_skeleton"),
    Path("benchmarks/realm/p5_skeleton"),
]


def _load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_case_paths(case_paths: list[Path]) -> list[Path]:
    discovered: list[Path] = []

    for path in case_paths:
        if path.is_file():
            discovered.append(path)
            continue

        if not path.exists():
            raise FileNotFoundError(f"case path does not exist: {path}")

        discovered.extend(
            candidate
            for candidate in path.glob("*.json")
            if candidate.is_file()
        )

    return sorted(discovered)


def _required_fields_missing(data: JsonDict) -> list[str]:
    missing: list[str] = []

    for key in [
        "case_id",
        "family",
        "expected_negative",
        "app_id",
        "schema_id",
        "realm_bench",
        "steps",
    ]:
        if key not in data:
            missing.append(key)

    realm = data.get("realm_bench", {})
    if isinstance(realm, dict):
        for key in [
            "tenant_id",
            "workflow_id",
            "entity_id",
            "binding_id",
            "fsm",
        ]:
            if key not in realm:
                missing.append(f"realm_bench.{key}")
    else:
        missing.append("realm_bench")

    return missing


def row_from_skeleton(path: Path) -> JsonDict:
    data = _load_json(path)
    missing = _required_fields_missing(data)

    case_id = data.get("case_id", str(path))
    family = data.get("family")
    expected_negative = bool(data.get("expected_negative", False))
    realm = data.get("realm_bench", {}) if isinstance(data.get("realm_bench"), dict) else {}

    if missing:
        return {
            "case_id": case_id,
            "ok": False,
            "committed_rids": [],
            "metrics": None,
            "error_codes": ["SKELETON_SCHEMA_INVALID"],
            "error_message": "skeleton fixture missing required fields",
            "details": {
                "missing_fields": missing,
                "observed": {
                    "committed": False,
                    "report_only": True,
                },
            },
            "source_case_path": str(path),
        }

    if expected_negative:
        return {
            "case_id": case_id,
            "ok": False,
            "committed_rids": [],
            "metrics": None,
            "error_codes": ["EXPECTED_NEGATIVE_SKELETON"],
            "error_message": "expected-negative skeleton fixture",
            "details": {
                "family": family,
                "app_id": data["app_id"],
                "schema_id": data["schema_id"],
                "fsm": realm["fsm"],
                "expected_rejection_reason": data.get("expected_rejection_reason"),
                "step_count": len(data["steps"]),
                "observed": {
                    "committed": False,
                    "report_only": True,
                },
            },
            "source_case_path": str(path),
        }

    return {
        "case_id": case_id,
        "ok": True,
        "committed_rids": [],
        "metrics": {
            "case_id": case_id,
            "family": family,
            "step_count": len(data["steps"]),
            "report_only": True,
        },
        "error_codes": [],
        "error_message": None,
        "details": {
            "family": family,
            "app_id": data["app_id"],
            "schema_id": data["schema_id"],
            "fsm": realm["fsm"],
            "observed": {
                "committed": False,
                "report_only": True,
            },
        },
        "source_case_path": str(path),
    }


def run_skeleton_families(
    *,
    case_paths: list[Path],
    output_path: Path,
) -> int:
    discovered = discover_case_paths(case_paths)

    rows = [
        row_from_skeleton(path)
        for path in discovered
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    passed = sum(1 for row in rows if row["ok"])
    failed = len(rows) - passed

    print(f"Skeleton family run complete: {passed}/{len(rows)} passed, {failed} failed")
    print(f"Results written to: {output_path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run report-only benchmark-family skeleton fixtures.",
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=[str(path) for path in DEFAULT_CASE_DIRS],
        help="Skeleton fixture file or directory paths.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSONL path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    return run_skeleton_families(
        case_paths=[Path(path) for path in args.cases],
        output_path=Path(args.out),
    )


if __name__ == "__main__":
    raise SystemExit(main())
