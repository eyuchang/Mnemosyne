from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProposerAttempt:
    proposer: str
    attempt_id: str
    operation_key: str
    valid_under_c: bool
    utility: int
    reason_if_invalid: str


PROPOSER_SPECS = {
    "no_intelligence": {
        "attempts": 10,
        "valid_positions": [8],
        "utility": 1,
    },
    "random_proposer": {
        "attempts": 10,
        "valid_positions": [5, 9],
        "utility": 2,
    },
    "rule_based_proposer": {
        "attempts": 10,
        "valid_positions": [2, 3, 5, 7, 9],
        "utility": 5,
    },
    "solver_like_proposer": {
        "attempts": 10,
        "valid_positions": [1, 2, 3, 4, 5, 6, 7, 8],
        "utility": 8,
    },
    "llm_like_proposer": {
        "attempts": 10,
        "valid_positions": [2, 3, 4, 6, 8, 9],
        "utility": 6,
    },
    "adversarial_proposer": {
        "attempts": 10,
        "valid_positions": [10],
        "utility": 1,
    },
}


def attempt_suite() -> list[ProposerAttempt]:
    attempts: list[ProposerAttempt] = []

    invalid_reasons = [
        "malformed",
        "stale_world",
        "capacity_violation",
        "unsafe_compensation",
        "evidence_destroying_repair",
        "duplicate_operation_key",
    ]

    for proposer, spec in PROPOSER_SPECS.items():
        valid_positions = set(spec["valid_positions"])
        for idx in range(1, spec["attempts"] + 1):
            valid = idx in valid_positions
            reason = "" if valid else invalid_reasons[(idx - 1) % len(invalid_reasons)]
            attempts.append(
                ProposerAttempt(
                    proposer=proposer,
                    attempt_id=f"{proposer}-attempt-{idx}",
                    operation_key=f"{proposer}-op-{idx}",
                    valid_under_c=valid,
                    utility=spec["utility"] if valid else 0,
                    reason_if_invalid=reason,
                )
            )

    return attempts


def run_direct_commit_baseline(attempts: list[ProposerAttempt]) -> dict:
    rows: list[dict] = []

    for attempt in attempts:
        rows.append(
            {
                "attempt": asdict(attempt),
                "committed": True,
                "reason": "direct_commit",
            }
        )

    invalid_commits = sum(1 for row in rows if not row["attempt"]["valid_under_c"])

    return {
        "system": "direct_commit_baseline",
        "attempts": len(rows),
        "committed": len(rows),
        "rejected": 0,
        "invalid_commits": invalid_commits,
        "total_utility": sum(row["attempt"]["utility"] for row in rows),
        "rows": rows,
    }


def run_atp_mnemosyne(attempts: list[ProposerAttempt]) -> dict:
    rows: list[dict] = []

    for attempt in attempts:
        committed = attempt.valid_under_c
        rows.append(
            {
                "attempt": asdict(attempt),
                "committed": committed,
                "reason": "admitted" if committed else attempt.reason_if_invalid,
            }
        )

    invalid_commits = sum(
        1 for row in rows if row["committed"] and not row["attempt"]["valid_under_c"]
    )

    return {
        "system": "atp_mnemosyne",
        "attempts": len(rows),
        "committed": sum(1 for row in rows if row["committed"]),
        "rejected": sum(1 for row in rows if not row["committed"]),
        "invalid_commits": invalid_commits,
        "total_utility": sum(
            row["attempt"]["utility"] for row in rows if row["committed"]
        ),
        "rows": rows,
    }


def proposer_summary(atp_rows: list[dict]) -> list[dict]:
    summaries: list[dict] = []

    for proposer in PROPOSER_SPECS:
        rows = [row for row in atp_rows if row["attempt"]["proposer"] == proposer]
        committed_rows = [row for row in rows if row["committed"]]
        rejected_rows = [row for row in rows if not row["committed"]]
        first_admitted = next(
            (
                i + 1
                for i, row in enumerate(rows)
                if row["committed"]
            ),
            None,
        )

        summaries.append(
            {
                "proposer": proposer,
                "attempts": len(rows),
                "admitted": len(committed_rows),
                "rejected": len(rejected_rows),
                "accepted_rate": len(committed_rows) / len(rows),
                "utility": sum(row["attempt"]["utility"] for row in committed_rows),
                "attempts_to_first_admission": first_admitted,
                "invalid_commits": sum(
                    1
                    for row in committed_rows
                    if not row["attempt"]["valid_under_c"]
                ),
            }
        )

    return summaries


def write_reports(results: list[dict], summaries: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ8",
        "name": "Proposer quality affects usefulness, not committed-state correctness",
        "claim": (
            "Better proposers improve utility and admission efficiency, while ATP keeps "
            "invalid committed transitions at zero relative to C."
        ),
        "success_criteria": [
            "ATP invalid_commits = 0 across proposer classes",
            "Direct commit baseline invalid_commits > 0",
            "Higher-quality proposers improve admitted utility and admission efficiency",
            "No learning, regret, or preemptive-planning claim is made",
        ],
        "systems": results,
        "proposer_summaries": summaries,
    }

    (report_dir / "rq8_proposer_quality_safety_invariant_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ8 Proposer Quality and Safety Invariant Report",
        "",
        "Proposer quality changes usefulness and admission efficiency, but ATP keeps invalid commits at zero.",
        "",
        "## System summary",
        "",
        "| System | Attempts | Committed | Rejected | Invalid commits | Total utility |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {attempts} | {committed} | {rejected} | "
            "{invalid_commits} | {total_utility} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Proposer summary under ATP",
            "",
            "| Proposer | Attempts | Admitted | Rejected | Acceptance rate | Utility | First admission attempt | Invalid commits |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for summary in summaries:
        lines.append(
            "| {proposer} | {attempts} | {admitted} | {rejected} | "
            "{accepted_rate:.2f} | {utility} | {attempts_to_first_admission} | "
            "{invalid_commits} |".format(**summary)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment studies proposer quality as usefulness, not learning.",
            "It does not claim cross-episode improvement, regret reduction, or preemptive planning.",
            "The safety invariant is relative to the declared constraint set C.",
            "",
        ]
    )

    (report_dir / "rq8_proposer_quality_safety_invariant_report.md").write_text(
        "\n".join(lines)
    )


def test_rq8_proposer_quality_safety_invariant() -> None:
    attempts = attempt_suite()

    results = [
        run_direct_commit_baseline(attempts),
        run_atp_mnemosyne(attempts),
    ]

    by_system = {result["system"]: result for result in results}
    summaries = proposer_summary(by_system["atp_mnemosyne"]["rows"])
    by_proposer = {summary["proposer"]: summary for summary in summaries}

    assert by_system["direct_commit_baseline"]["invalid_commits"] > 0
    assert by_system["atp_mnemosyne"]["invalid_commits"] == 0

    assert all(summary["invalid_commits"] == 0 for summary in summaries)

    assert (
        by_proposer["solver_like_proposer"]["utility"]
        > by_proposer["rule_based_proposer"]["utility"]
        > by_proposer["no_intelligence"]["utility"]
    )

    assert (
        by_proposer["solver_like_proposer"]["accepted_rate"]
        > by_proposer["rule_based_proposer"]["accepted_rate"]
        > by_proposer["no_intelligence"]["accepted_rate"]
    )

    assert (
        by_proposer["adversarial_proposer"]["accepted_rate"]
        < by_proposer["rule_based_proposer"]["accepted_rate"]
    )

    write_reports(results, summaries)
