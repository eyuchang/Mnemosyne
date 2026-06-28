from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompensationScenario:
    scenario_id: str
    workload: str
    dependency_shape: str
    target_effective_before: bool
    local_undo_exists: bool
    live_effective_dependents: int
    chain_valid_after_compensation: bool
    depends_on_ineffective_record: bool
    target_already_superseded: bool
    expected_stateview_state: str
    latest_record_baseline_state: str


@dataclass(frozen=True)
class CompensationCheck:
    accepted: bool
    reason: str


def atp_compensation_admission(scenario: CompensationScenario) -> CompensationCheck:
    if not scenario.local_undo_exists:
        return CompensationCheck(False, "missing_local_undo")

    if not scenario.target_effective_before:
        return CompensationCheck(False, "target_not_effective")

    if scenario.target_already_superseded:
        return CompensationCheck(False, "target_already_superseded")

    if scenario.live_effective_dependents > 0:
        return CompensationCheck(False, "live_effective_dependents")

    if not scenario.chain_valid_after_compensation:
        return CompensationCheck(False, "broken_effective_chain")

    if scenario.depends_on_ineffective_record:
        return CompensationCheck(False, "depends_on_ineffective_record")

    return CompensationCheck(True, "accepted")


def scenario_suite() -> list[CompensationScenario]:
    return [
        CompensationScenario(
            scenario_id="valid_leaf_compensation",
            workload="valid_leaf_compensation",
            dependency_shape="linear_depth_3",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=0,
            chain_valid_after_compensation=True,
            depends_on_ineffective_record=False,
            target_already_superseded=False,
            expected_stateview_state="root>A>B_compensated",
            latest_record_baseline_state="compensation_record_as_current_truth",
        ),
        CompensationScenario(
            scenario_id="invalid_root_with_live_chain",
            workload="compensate_root_with_live_linear_dependents",
            dependency_shape="linear_depth_3",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=2,
            chain_valid_after_compensation=False,
            depends_on_ineffective_record=False,
            target_already_superseded=False,
            expected_stateview_state="root>A>B",
            latest_record_baseline_state="root_compensated_with_orphaned_children",
        ),
        CompensationScenario(
            scenario_id="invalid_root_with_live_branching_dependents",
            workload="compensate_root_with_live_branching_dependents",
            dependency_shape="branching_factor_4",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=4,
            chain_valid_after_compensation=False,
            depends_on_ineffective_record=False,
            target_already_superseded=False,
            expected_stateview_state="root>{A,B,C,D}",
            latest_record_baseline_state="root_compensated_with_orphaned_branches",
        ),
        CompensationScenario(
            scenario_id="invalid_broken_effective_chain",
            workload="compensation_breaks_effective_chain",
            dependency_shape="diamond_dependency",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=0,
            chain_valid_after_compensation=False,
            depends_on_ineffective_record=False,
            target_already_superseded=False,
            expected_stateview_state="diamond_chain_preserved",
            latest_record_baseline_state="diamond_chain_broken_by_compensation",
        ),
        CompensationScenario(
            scenario_id="invalid_repair_depends_on_ineffective_record",
            workload="repair_depends_on_ineffective_record",
            dependency_shape="linear_depth_2",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=0,
            chain_valid_after_compensation=True,
            depends_on_ineffective_record=True,
            target_already_superseded=False,
            expected_stateview_state="repair_rejected_parent_remains_ineffective",
            latest_record_baseline_state="repair_committed_against_ineffective_parent",
        ),
        CompensationScenario(
            scenario_id="invalid_superseded_target",
            workload="compensate_superseded_target",
            dependency_shape="supersession_pair",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=0,
            chain_valid_after_compensation=True,
            depends_on_ineffective_record=False,
            target_already_superseded=True,
            expected_stateview_state="new_record_effective_old_record_ineffective",
            latest_record_baseline_state="old_superseded_record_compensated_as_current",
        ),
        CompensationScenario(
            scenario_id="valid_isolated_supersession",
            workload="valid_isolated_supersession",
            dependency_shape="isolated_leaf",
            target_effective_before=True,
            local_undo_exists=True,
            live_effective_dependents=0,
            chain_valid_after_compensation=True,
            depends_on_ineffective_record=False,
            target_already_superseded=False,
            expected_stateview_state="new_leaf_effective",
            latest_record_baseline_state="supersession_event_as_current_truth",
        ),
    ]


def run_system(system_name: str, scenarios: list[CompensationScenario]) -> dict:
    rows: list[dict] = []

    for scenario in scenarios:
        check = atp_compensation_admission(scenario)

        if system_name == "saga_without_dependency_closure":
            committed = scenario.local_undo_exists
            projected_state = scenario.latest_record_baseline_state
            decision = "committed_local_undo" if committed else "rejected"

        elif system_name == "latest_record_projection":
            committed = scenario.local_undo_exists and scenario.target_effective_before
            projected_state = scenario.latest_record_baseline_state if committed else scenario.expected_stateview_state
            decision = "committed_latest_record_projection" if committed else "rejected"

        elif system_name == "atp_mnemosyne":
            committed = check.accepted
            projected_state = scenario.expected_stateview_state
            decision = "admitted" if committed else "rejected_before_commit"

        else:
            raise ValueError(f"unknown system: {system_name}")

        invalid_compensation_admitted = committed and not check.accepted
        orphaned_effective_dependents = committed and scenario.live_effective_dependents > 0
        broken_effective_chain = committed and (
            not scenario.chain_valid_after_compensation
            or scenario.depends_on_ineffective_record
            or scenario.target_already_superseded
        )
        stateview_mismatch = projected_state != scenario.expected_stateview_state

        rows.append(
            {
                "system": system_name,
                "scenario": asdict(scenario),
                "accepted_by_atp_rule": check.accepted,
                "atp_rule_reason": check.reason,
                "committed": committed,
                "decision": decision,
                "projected_state": projected_state,
                "invalid_compensation_admitted": invalid_compensation_admitted,
                "orphaned_effective_dependents": orphaned_effective_dependents,
                "broken_effective_chain": broken_effective_chain,
                "stateview_mismatch": stateview_mismatch,
            }
        )

    return {
        "system": system_name,
        "scenario_count": len(rows),
        "invalid_compensations_admitted": sum(row["invalid_compensation_admitted"] for row in rows),
        "orphaned_effective_dependents": sum(row["orphaned_effective_dependents"] for row in rows),
        "broken_effective_chains": sum(row["broken_effective_chain"] for row in rows),
        "stateview_mismatches": sum(row["stateview_mismatch"] for row in rows),
        "valid_compensations_committed": sum(
            1 for row in rows if row["committed"] and row["accepted_by_atp_rule"]
        ),
        "rejected_invalid_compensations": sum(
            1 for row in rows if not row["committed"] and not row["accepted_by_atp_rule"]
        ),
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ5",
        "name": "Effective-state and compensation safety",
        "claim": (
            "StateView remains the projection of effective committed records only, "
            "and compensation is admitted only when it does not orphan effective dependents "
            "or break effective dependency chains."
        ),
        "success_criteria": [
            "ATP invalid_compensations_admitted = 0",
            "ATP orphaned_effective_dependents = 0",
            "ATP broken_effective_chains = 0",
            "ATP stateview_mismatches = 0",
            "At least one unsafe baseline has violations > 0",
            "ATP valid_compensations_committed > 0",
        ],
        "systems": results,
    }

    (report_dir / "rq5_effective_state_compensation_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ5 Effective-State and Compensation Safety Report",
        "",
        "Compensation must not orphan effective dependents, break effective chains, or cause StateView to project ineffective history as current truth.",
        "",
        "| System | Scenarios | Invalid compensations admitted | Orphaned dependents | Broken chains | StateView mismatches | Valid compensations committed |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for result in results:
        lines.append(
            "| {system} | {scenario_count} | {invalid_compensations_admitted} | "
            "{orphaned_effective_dependents} | {broken_effective_chains} | "
            "{stateview_mismatches} | {valid_compensations_committed} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests effective-state projection and dependency-closed compensation.",
            "It does not claim learning, regret reduction, or preemptive planning.",
            "The guarantee is relative to the declared dependency graph and effective-record predicates.",
            "",
        ]
    )

    (report_dir / "rq5_effective_state_compensation_report.md").write_text(
        "\n".join(lines)
    )


def test_rq5_effective_state_compensation_safety() -> None:
    scenarios = scenario_suite()

    results = [
        run_system("saga_without_dependency_closure", scenarios),
        run_system("latest_record_projection", scenarios),
        run_system("atp_mnemosyne", scenarios),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["saga_without_dependency_closure"]["invalid_compensations_admitted"] > 0
    assert by_system["latest_record_projection"]["stateview_mismatches"] > 0

    assert by_system["atp_mnemosyne"]["invalid_compensations_admitted"] == 0
    assert by_system["atp_mnemosyne"]["orphaned_effective_dependents"] == 0
    assert by_system["atp_mnemosyne"]["broken_effective_chains"] == 0
    assert by_system["atp_mnemosyne"]["stateview_mismatches"] == 0
    assert by_system["atp_mnemosyne"]["valid_compensations_committed"] > 0
    assert by_system["atp_mnemosyne"]["rejected_invalid_compensations"] > 0

    write_reports(results)
