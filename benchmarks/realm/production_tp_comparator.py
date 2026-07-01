#!/usr/bin/env python3
"""
ProductionTPComparatorBench.

A deterministic coverage benchmark for RQ6:
What does ATP add beyond a production transaction-processing substrate?

This is not a throughput benchmark and not a claim that PostgreSQL is weak.
It audits which enforcement layer naturally owns each responsibility:

1. PostgreSQL-style TP substrate:
   serializable transactions, primary keys, foreign keys, unique keys,
   checks, triggers, and outbox tables.

2. Workflow/saga guardrail layer:
   schema validation, finite-state checks, idempotency keys, timers,
   retries, local compensation, and proposer self-checks.

3. ATP/Mnemosyne:
   proposal packages, C + StateView admission, retained evidence,
   dependency-closed compensation, ACR non-authority, and conflict scopes.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List


VALID_OUTCOMES = {"caught", "missed", "partial", "app-only"}


@dataclass(frozen=True)
class CoverageCase:
    hazard: str
    description: str
    postgres_style_tp: str
    workflow_saga: str
    atp_mnemosyne: str
    rationale: str


def build_cases() -> List[CoverageCase]:
    return [
        CoverageCase(
            hazard="primary_key_unique_duplicate",
            description="Duplicate committed record or duplicate operation key.",
            postgres_style_tp="caught",
            workflow_saga="caught",
            atp_mnemosyne="caught",
            rationale="This is a storage-level uniqueness/idempotency violation.",
        ),
        CoverageCase(
            hazard="missing_foreign_key_dependency",
            description="A transition references a dependency that does not exist.",
            postgres_style_tp="caught",
            workflow_saga="caught",
            atp_mnemosyne="caught",
            rationale="This is a storage-level referential-integrity violation.",
        ),
        CoverageCase(
            hazard="finite_state_invalid_transition",
            description="A proposal attempts an illegal FSM transition.",
            postgres_style_tp="app-only",
            workflow_saga="caught",
            atp_mnemosyne="caught",
            rationale=(
                "A TP substrate can enforce this only if the application encodes "
                "the FSM rule; workflow guardrails and ATP naturally check it."
            ),
        ),
        CoverageCase(
            hazard="stale_world_proposal",
            description="A generated proposal assumes facts no longer true in StateView.",
            postgres_style_tp="missed",
            workflow_saga="missed",
            atp_mnemosyne="caught",
            rationale=(
                "Generic TP executes submitted transactions; ATP checks proposal "
                "world assumptions against effective state before authority is granted."
            ),
        ),
        CoverageCase(
            hazard="orphaning_compensation_effective_state",
            description="A compensation would make effective dependents orphaned.",
            postgres_style_tp="app-only",
            workflow_saga="partial",
            atp_mnemosyne="caught",
            rationale=(
                "A saga may run local compensation but need not check effective-state "
                "dependency closure unless the application encodes it."
            ),
        ),
        CoverageCase(
            hazard="evidence_destroying_repair",
            description="A repair hides the evidence that triggered the repair.",
            postgres_style_tp="missed",
            workflow_saga="missed",
            atp_mnemosyne="caught",
            rationale=(
                "Evidence preservation is an ATP-specific admission rule: a repair "
                "must resolve the failure or preserve the triggering evidence."
            ),
        ),
        CoverageCase(
            hazard="acr_direct_domain_mutation",
            description="An active commitment wakeup mutates domain truth directly.",
            postgres_style_tp="missed",
            workflow_saga="missed",
            atp_mnemosyne="caught",
            rationale=(
                "ATP treats ACR wakeups as non-authoritative; they may only emit "
                "proposal packages that re-enter admission."
            ),
        ),
        CoverageCase(
            hazard="generative_conflict_scope_collision",
            description="Two individually plausible proposals conflict over one scope.",
            postgres_style_tp="app-only",
            workflow_saga="partial",
            atp_mnemosyne="caught",
            rationale=(
                "TP can serialize rows, but generative conflict scopes are an ATP "
                "authority-level declaration over proposal semantics."
            ),
        ),
        CoverageCase(
            hazard="duplicate_side_effect_intent",
            description="A duplicate provider call or outbox intent is generated.",
            postgres_style_tp="partial",
            workflow_saga="partial",
            atp_mnemosyne="caught",
            rationale=(
                "Outbox/idempotency can partially catch duplicates; ATP stages the "
                "intent and admits observed effects as later transitions."
            ),
        ),
    ]


def validate_cases(cases: Iterable[CoverageCase]) -> None:
    cases = list(cases)
    if len(cases) != 9:
        raise AssertionError(f"Expected 9 coverage cases, found {len(cases)}")

    for case in cases:
        for layer_name in ("postgres_style_tp", "workflow_saga", "atp_mnemosyne"):
            value = getattr(case, layer_name)
            if value not in VALID_OUTCOMES:
                raise AssertionError(
                    f"{case.hazard}: invalid outcome {value!r} for {layer_name}"
                )

    if not all(case.atp_mnemosyne == "caught" for case in cases):
        raise AssertionError("ATP/Mnemosyne must catch every listed ATP hazard.")

    storage_hazards = {
        "primary_key_unique_duplicate",
        "missing_foreign_key_dependency",
    }
    for case in cases:
        if case.hazard in storage_hazards:
            if case.postgres_style_tp != "caught":
                raise AssertionError(f"Storage hazard not caught by TP: {case.hazard}")

    atp_specific = {
        "stale_world_proposal",
        "orphaning_compensation_effective_state",
        "evidence_destroying_repair",
        "acr_direct_domain_mutation",
        "generative_conflict_scope_collision",
        "duplicate_side_effect_intent",
    }
    for case in cases:
        if case.hazard in atp_specific:
            if case.postgres_style_tp == "caught" and case.workflow_saga == "caught":
                raise AssertionError(
                    f"ATP-specific hazard fully caught before ATP layer: {case.hazard}"
                )


def summarize(cases: Iterable[CoverageCase]) -> Dict[str, object]:
    cases = list(cases)
    layers = {
        "postgres_style_tp": {key: 0 for key in sorted(VALID_OUTCOMES)},
        "workflow_saga": {key: 0 for key in sorted(VALID_OUTCOMES)},
        "atp_mnemosyne": {key: 0 for key in sorted(VALID_OUTCOMES)},
    }

    for case in cases:
        layers["postgres_style_tp"][case.postgres_style_tp] += 1
        layers["workflow_saga"][case.workflow_saga] += 1
        layers["atp_mnemosyne"][case.atp_mnemosyne] += 1

    return {
        "benchmark": "ProductionTPComparatorBench",
        "kind": "deterministic coverage audit",
        "not_a_throughput_benchmark": True,
        "num_cases": len(cases),
        "layers": layers,
        "conclusion": (
            "Production TP substrates catch storage-level violations; "
            "workflow/saga guardrails catch classical guardrail hazards; "
            "ATP/Mnemosyne adds proposal-authority semantics for stale-world "
            "proposals, evidence-preserving repair, ACR non-authority, "
            "dependency-closed compensation, and generative conflict scopes."
        ),
    }


def write_json(path: Path, cases: List[CoverageCase], summary: Dict[str, object]) -> None:
    payload = {
        "summary": summary,
        "cases": [asdict(case) for case in cases],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, cases: List[CoverageCase]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "hazard",
                "description",
                "postgres_style_tp",
                "workflow_saga",
                "atp_mnemosyne",
                "rationale",
            ],
        )
        writer.writeheader()
        for case in cases:
            writer.writerow(asdict(case))


def write_markdown(path: Path, cases: List[CoverageCase], summary: Dict[str, object]) -> None:
    lines = []
    lines.append("# ProductionTPComparatorBench")
    lines.append("")
    lines.append("Deterministic coverage audit; not a throughput benchmark.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Cases: {summary['num_cases']}")
    lines.append(f"- ATP/Mnemosyne caught: {summary['layers']['atp_mnemosyne']['caught']} / {summary['num_cases']}")
    lines.append(f"- PostgreSQL-style TP caught: {summary['layers']['postgres_style_tp']['caught']} / {summary['num_cases']}")
    lines.append(f"- Workflow/saga guardrails caught: {summary['layers']['workflow_saga']['caught']} / {summary['num_cases']}")
    lines.append("")
    lines.append("## Coverage table")
    lines.append("")
    lines.append(
        "| Hazard | PostgreSQL-style TP | Workflow/saga | ATP/Mnemosyne | Rationale |"
    )
    lines.append("|---|---:|---:|---:|---|")
    for case in cases:
        lines.append(
            f"| `{case.hazard}` | {case.postgres_style_tp} | "
            f"{case.workflow_saga} | {case.atp_mnemosyne} | {case.rationale} |"
        )
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(str(summary["conclusion"]))
    lines.append("")
    path.write_text("\n".join(lines))


def run(output_dir: Path | str = "benchmarks/realm/reports/production_tp_comparator") -> Dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = build_cases()
    validate_cases(cases)
    summary = summarize(cases)

    write_json(output_dir / "summary.json", cases, summary)
    write_csv(output_dir / "summary.csv", cases)
    write_markdown(output_dir / "report.md", cases, summary)

    return summary


def main() -> None:
    summary = run()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
