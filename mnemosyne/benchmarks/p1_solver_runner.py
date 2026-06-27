# File: mnemosyne/benchmarks/p1_solver_runner.py
#
# Purpose:
#   CLI runner for local P1-compatible solver-derived benchmark cases.
#
# Stage:
#   R0.2, R2.1, R2.2, and R2.3.
#
# R2.1:
#   Solver backend is selected through the solver registry:
#
#     --solver p1-bruteforce
#
# R2.2:
#   Solver proposals are preflight-checked for proposal conflicts before
#   any proposal is admitted into the Mnemosyne commit path.
#
# R2.3:
#   Solver proposals may carry world assumptions. If a world snapshot is
#   provided, proposals are reconciled against currently observed facts before
#   commit admission.
#
# Design rule:
#   A solver produces a certified proposal.
#   Conflict-free and world-reconciled admission is still not commit.
#   Mnemosyne remains the commit authority.

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mnemosyne.apps.campus_tour.app import CampusTourApp
from mnemosyne.apps.registry import AppRegistry
from mnemosyne.benchmarks.domain_feasibility import DomainFeasibilityReport, check_domain_feasibility
from mnemosyne.benchmarks.proposal_conflicts import detect_proposal_conflicts
from mnemosyne.benchmarks.runner import run_realm_case
from mnemosyne.benchmarks.solver import PlanProposal, SolverResult
from mnemosyne.benchmarks.solver_registry import default_solver_registry
from mnemosyne.benchmarks.stale_world_repair import repair_case_data_from_stale_world
from mnemosyne.benchmarks.world_reconciliation import (
    ObservedWorldFact,
    load_world_snapshot,
    reconcile_world,
)
from mnemosyne.core.fsm.registry import FSMRegistry
from mnemosyne.core.validation.validator import Validator
from mnemosyne.store.sqlite.store import SQLiteStore


JsonDict = dict[str, Any]


def make_store() -> SQLiteStore:
    return SQLiteStore(":memory:")


def make_validator() -> Validator:
    app_registry = AppRegistry()
    app_registry.register(CampusTourApp())

    fsm_registry = FSMRegistry()

    for app in app_registry.apps.values():
        for fsm_spec in app.fsms():
            fsm_registry.register(fsm_spec)

    return Validator(fsm_registry=fsm_registry)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _jsonable(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _jsonable(item)
            for item in value
        ]

    if isinstance(value, Path):
        return str(value)

    return value


def result_to_dict(result: Any) -> JsonDict:
    return _jsonable(result)


def discover_case_paths(cases_path: Path) -> list[Path]:
    if cases_path.is_file():
        return [cases_path]

    if not cases_path.exists():
        raise FileNotFoundError(f"cases path does not exist: {cases_path}")

    return sorted(
        path
        for path in cases_path.glob("*.json")
        if path.is_file()
    )


def load_case_data(case_path: Path) -> JsonDict:
    return json.loads(case_path.read_text(encoding="utf-8"))


def _solver_failed_row(
    *,
    case_path: Path,
    data: JsonDict,
    solver_result: SolverResult,
) -> JsonDict:
    return {
        "case_id": data.get("case_id", str(case_path)),
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": ["SOLVER_FAILED"],
        "error_message": solver_result.error_message,
        "details": {
            "solver_certificate": result_to_dict(solver_result.certificate),
            "solver_details": result_to_dict(solver_result.details),
            "observed": {
                "committed": False,
            },
        },
        "source_case_path": str(case_path),
    }


def _domain_feasibility_row(
    *,
    case_path: Path,
    data: JsonDict,
    solver_result: SolverResult,
    domain_report: DomainFeasibilityReport,
) -> JsonDict:
    return {
        "case_id": data.get("case_id", str(case_path)),
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": domain_report.error_codes,
        "error_message": "domain feasibility rejected before commit",
        "details": {
            "solver_certificate": result_to_dict(solver_result.certificate),
            "plan_proposal": result_to_dict(solver_result.plan_proposal),
            "domain_feasibility": result_to_dict(domain_report),
            "observed": {
                "committed": False,
            },
        },
        "source_case_path": str(case_path),
    }


def _proposal_conflict_row(
    *,
    case_path: Path,
    data: JsonDict,
    solver_result: SolverResult,
    conflict_report: Any,
) -> JsonDict:
    return {
        "case_id": data.get("case_id", str(case_path)),
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": [
            "SOLVER_PROPOSAL_CONFLICT",
            *conflict_report.error_codes,
        ],
        "error_message": "solver proposal conflict detected before commit",
        "details": {
            "solver_certificate": result_to_dict(solver_result.certificate),
            "plan_proposal": result_to_dict(solver_result.plan_proposal),
            "proposal_conflicts": result_to_dict(conflict_report),
            "observed": {
                "committed": False,
            },
        },
        "source_case_path": str(case_path),
    }


def _world_reconciliation_row(
    *,
    case_path: Path,
    data: JsonDict,
    solver_result: SolverResult,
    reconciliation_report: Any,
) -> JsonDict:
    return {
        "case_id": data.get("case_id", str(case_path)),
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": [
            "STALE_WORLD_RECONCILIATION",
            *reconciliation_report.error_codes,
        ],
        "error_message": "world reconciliation failed before commit",
        "details": {
            "solver_certificate": result_to_dict(solver_result.certificate),
            "plan_proposal": result_to_dict(solver_result.plan_proposal),
            "world_reconciliation": result_to_dict(reconciliation_report),
            "observed": {
                "committed": False,
            },
        },
        "source_case_path": str(case_path),
    }


def _stale_world_repair_failed_row(
    *,
    case_path: Path,
    data: JsonDict,
    solver_result: SolverResult,
    reconciliation_report: Any,
    repair_error_message: str | None,
) -> JsonDict:
    return {
        "case_id": data.get("case_id", str(case_path)),
        "ok": False,
        "committed_rids": [],
        "metrics": None,
        "error_codes": [
            "STALE_WORLD_REPAIR_FAILED",
            "STALE_WORLD_RECONCILIATION",
            *reconciliation_report.error_codes,
        ],
        "error_message": repair_error_message or "stale-world repair failed",
        "details": {
            "solver_certificate": result_to_dict(solver_result.certificate),
            "plan_proposal": result_to_dict(solver_result.plan_proposal),
            "world_reconciliation": result_to_dict(reconciliation_report),
            "observed": {
                "committed": False,
            },
        },
        "source_case_path": str(case_path),
    }


async def run_p1_solver_cases(
    *,
    case_paths: list[Path],
    solver_name: str = "p1-bruteforce",
    observed_world_facts: list[ObservedWorldFact] | None = None,
    repair_stale_world: bool = False,
) -> list[JsonDict]:
    solver = default_solver_registry().create(solver_name)

    failed_rows: list[JsonDict] = []
    solved_entries: list[tuple[Path, JsonDict, SolverResult, PlanProposal]] = []

    for case_path in case_paths:
        data = load_case_data(case_path)
        solver_result = solver.solve(data)

        if (
            not solver_result.ok
            or solver_result.benchmark_case is None
            or solver_result.plan_proposal is None
        ):
            failed_rows.append(
                _solver_failed_row(
                    case_path=case_path,
                    data=data,
                    solver_result=solver_result,
                )
            )
            continue

        solved_entries.append(
            (
                case_path,
                data,
                solver_result,
                solver_result.plan_proposal,
            )
        )

    conflict_report = detect_proposal_conflicts(
        proposal
        for _, _, _, proposal in solved_entries
    )

    if not conflict_report.ok:
        conflict_rows = [
            _proposal_conflict_row(
                case_path=case_path,
                data=data,
                solver_result=solver_result,
                conflict_report=conflict_report,
            )
            for case_path, data, solver_result, _ in solved_entries
        ]

        return [
            *failed_rows,
            *conflict_rows,
        ]

    stale_world_repair_actions_by_case_id: dict[str, Any] = {}

    if observed_world_facts is not None:
        reconciliation_report = reconcile_world(
            proposals=(
                proposal
                for _, _, _, proposal in solved_entries
            ),
            observed_facts=observed_world_facts,
        )

        if not reconciliation_report.ok:
            if not repair_stale_world:
                stale_rows = [
                    _world_reconciliation_row(
                        case_path=case_path,
                        data=data,
                        solver_result=solver_result,
                        reconciliation_report=reconciliation_report,
                    )
                    for case_path, data, solver_result, _ in solved_entries
                ]

                return [
                    *failed_rows,
                    *stale_rows,
                ]

            repaired_entries: list[tuple[Path, JsonDict, SolverResult, PlanProposal]] = []
            stale_repair_failed_rows: list[JsonDict] = []

            for case_path, data, solver_result, _ in solved_entries:
                repair_result = repair_case_data_from_stale_world(
                    case_data=data,
                    reconciliation_report=reconciliation_report,
                )

                if not repair_result.ok or repair_result.repaired_case_data is None:
                    stale_repair_failed_rows.append(
                        _stale_world_repair_failed_row(
                            case_path=case_path,
                            data=data,
                            solver_result=solver_result,
                            reconciliation_report=reconciliation_report,
                            repair_error_message=repair_result.error_message,
                        )
                    )
                    continue

                repaired_solver_result = solver.solve(repair_result.repaired_case_data)

                if (
                    not repaired_solver_result.ok
                    or repaired_solver_result.benchmark_case is None
                    or repaired_solver_result.plan_proposal is None
                ):
                    stale_repair_failed_rows.append(
                        _stale_world_repair_failed_row(
                            case_path=case_path,
                            data=repair_result.repaired_case_data,
                            solver_result=repaired_solver_result,
                            reconciliation_report=reconciliation_report,
                            repair_error_message=repaired_solver_result.error_message,
                        )
                    )
                    continue

                repaired_case_id = repaired_solver_result.benchmark_case.case_id
                stale_world_repair_actions_by_case_id[repaired_case_id] = result_to_dict(
                    repair_result.repair_actions
                )

                repaired_entries.append(
                    (
                        case_path,
                        repair_result.repaired_case_data,
                        repaired_solver_result,
                        repaired_solver_result.plan_proposal,
                    )
                )

            if stale_repair_failed_rows:
                return [
                    *failed_rows,
                    *stale_repair_failed_rows,
                ]

            repaired_reconciliation_report = reconcile_world(
                proposals=(
                    proposal
                    for _, _, _, proposal in repaired_entries
                ),
                observed_facts=observed_world_facts,
            )

            if not repaired_reconciliation_report.ok:
                stale_rows = [
                    _world_reconciliation_row(
                        case_path=case_path,
                        data=data,
                        solver_result=solver_result,
                        reconciliation_report=repaired_reconciliation_report,
                    )
                    for case_path, data, solver_result, _ in repaired_entries
                ]

                return [
                    *failed_rows,
                    *stale_rows,
                ]

            solved_entries = repaired_entries


    domain_failed_rows: list[JsonDict] = []

    for case_path, data, solver_result, _ in solved_entries:
        domain_report = check_domain_feasibility(
            solver_result.benchmark_case,
            solver_result.plan_proposal,
        )
        if not domain_report.ok:
            domain_failed_rows.append(
                _domain_feasibility_row(
                    case_path=case_path,
                    data=data,
                    solver_result=solver_result,
                    domain_report=domain_report,
                )
            )

    if domain_failed_rows:
        return [
            *failed_rows,
            *domain_failed_rows,
        ]

    results: list[JsonDict] = [
        *failed_rows,
    ]

    for case_path, _, solver_result, _ in solved_entries:
        result = await run_realm_case(
            case=solver_result.benchmark_case,
            store=make_store(),
            validator=make_validator(),
        )

        serialized = result_to_dict(result)
        serialized["source_case_path"] = str(case_path)
        serialized["solver_certificate"] = result_to_dict(solver_result.certificate)
        serialized["plan_proposal"] = result_to_dict(solver_result.plan_proposal)

        repair_actions = stale_world_repair_actions_by_case_id.get(
            solver_result.benchmark_case.case_id
            if solver_result.benchmark_case is not None
            else None
        )
        if repair_actions is not None:
            serialized.setdefault("details", {})
            serialized["details"]["stale_world_repair"] = {
                "applied": True,
                "actions": repair_actions,
            }

        results.append(serialized)

    return results


def write_jsonl(
    *,
    results: list[JsonDict],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, sort_keys=True) + "\n")


def summarize(results: list[JsonDict]) -> tuple[int, int, int]:
    total = len(results)
    passed = sum(1 for result in results if result.get("ok") is True)
    failed = total - passed

    return total, passed, failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m mnemosyne.benchmarks.p1_solver_runner",
        description="Run local P1-compatible solver-derived benchmark cases.",
    )

    parser.add_argument(
        "--cases",
        required=True,
        help="Path to a P1 solver fixture JSON file or directory.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--solver",
        default="p1-bruteforce",
        help="Solver backend name. Default: p1-bruteforce.",
    )
    parser.add_argument(
        "--world-snapshot",
        default=None,
        help="Optional JSON file of observed world facts for stale-world reconciliation.",
    )
    parser.add_argument(
        "--repair-stale-world",
        action="store_true",
        help="Attempt deterministic repair/replan when world reconciliation fails.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    case_paths = discover_case_paths(Path(args.cases))

    observed_world_facts = None

    if args.world_snapshot:
        observed_world_facts = load_world_snapshot(Path(args.world_snapshot))

    try:
        results = asyncio.run(
            run_p1_solver_cases(
                case_paths=case_paths,
                solver_name=args.solver,
                observed_world_facts=observed_world_facts,
                repair_stale_world=args.repair_stale_world,
            )
        )
    except KeyError as exc:
        parser.error(str(exc))

    output_path = Path(args.out)
    write_jsonl(
        results=results,
        output_path=output_path,
    )

    total, passed, failed = summarize(results)

    print(f"P1 solver run complete: {passed}/{total} passed, {failed} failed")
    print(f"Results written to: {output_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
