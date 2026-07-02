"""Mnemosyne adapter for REALM-Bench Tier 6.

This deterministic adapter validates that Mnemosyne can emit REALM Tier-6-
compatible traces. It is not a live LLM run and not evidence for H1-H5.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


CONFIGS = {
    "E0": {"C": 0, "R": 0, "T": 0, "A": 0, "label": "engine_only"},
    "E2": {"C": 0, "R": 1, "T": 0, "A": 0, "label": "causal_audit"},
    "E3": {"C": 0, "R": 0, "T": 1, "A": 0, "label": "temporal_accountability"},
    "E7": {"C": 1, "R": 1, "T": 1, "A": 0, "label": "full_crt_stack"},
}

FIXTURE_TIMESTAMP_UTC = "2026-07-02T00:00:00Z"

CANONICAL_SENTENCE = (
    "This implements and validates the Mnemosyne REALM-Bench Tier-6 adapter; "
    "pilot and confirmatory runs follow under the registered protocol."
)


def resolve_realm_root(path: str | Path | None = None) -> Path:
    root_value = path or os.environ.get("REALM_BENCH_ROOT")
    if not root_value:
        raise RuntimeError("REALM_BENCH_ROOT is not set")
    root = Path(root_value).expanduser().resolve()
    if not (root / "datasets" / "T6" / "generator.py").exists():
        raise RuntimeError(f"REALM_BENCH_ROOT is not a Tier-6 REALM repo: {root}")
    return root


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_realm_support(realm_root: Path):
    if str(realm_root) not in sys.path:
        sys.path.insert(0, str(realm_root))

    generator = load_module(
        "realm_tier6_generator_for_mnemosyne",
        realm_root / "datasets" / "T6" / "generator.py",
    )
    scorer = load_module(
        "realm_tier6_scorer_for_mnemosyne",
        realm_root / "evaluation" / "tier6" / "scorer.py",
    )
    return generator, scorer


def make_event(
    *,
    config_id: str,
    sequence: Dict[str, Any],
    episode: Dict[str, Any],
    event_type: str,
    proposal_id: str,
    failure_signature: str,
    predicted_outcome: str,
    observed_outcome: str,
    delta: str,
    constraint_violations: List[str],
    repair_radius: int = 0,
    evidence_preserved: bool = True,
    time_to_correction: int | None = None,
    time_to_correction_censored: bool = True,
    rejection_reason_code: str | None = None,
    horizon_reward: float | None = None,
    grounded_admission: bool | None = None,
) -> Dict[str, Any]:
    event = {
        "sequence_id": sequence["sequence_id"],
        "episode_id": episode["episode_id"],
        "seed": sequence["sequence_seed"],
        "t": FIXTURE_TIMESTAMP_UTC,
        "event": event_type,
        "proposal_id": proposal_id,
        "failure_signature": failure_signature,
        "predicted_outcome": predicted_outcome,
        "observed_outcome": observed_outcome,
        "delta": delta,
        "constraint_violations": constraint_violations,
        "repair": {"radius": repair_radius, "evidence_preserved": evidence_preserved},
        "cost": {"tokens_in": 0, "tokens_out": 0, "wallclock_ms": 0},
        "time_to_correction": time_to_correction,
        "time_to_correction_censored": time_to_correction_censored,
        "invalid_commit_count": 0,
        "evidence_destroying_repair_count": 0,
        "orphaned_dependent_count": 0,
        "is_control_sequence": sequence["is_control_sequence"],
        "base_instance_id": episode["base_instance_id"],
        "family": episode["family"],
        "source_path": episode["source_path"],
        "dictionary_version": "tier6-signature-dictionary-v0",
        "generator_version": "tier6-generator-v0",
        "scorer_version": "tier6-scorer-v0",
        "system_id": "mnemosyne",
        "adapter_id": "tier6-mnemosyne-adapter-v0",
        "config_id": config_id,
        "condition_switches": CONFIGS[config_id],
        "claim_status": "adapter_validation_only",
    }
    if rejection_reason_code is not None:
        event["rejection_reason_code"] = rejection_reason_code
    if horizon_reward is not None:
        event["horizon_reward"] = horizon_reward
    if grounded_admission is not None:
        event["grounded_admission"] = grounded_admission
    return event


def emit_events_for_sequence(config_id: str, sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
    if config_id not in CONFIGS:
        raise ValueError(f"unknown config_id: {config_id}")

    episodes = sequence["episodes"]
    events: List[Dict[str, Any]] = []

    if sequence["is_control_sequence"] or not sequence["hazard_signatures"]:
        for episode in episodes:
            events.append(make_event(
                config_id=config_id,
                sequence=sequence,
                episode=episode,
                event_type="observe",
                proposal_id=f"{sequence['sequence_id']}-{config_id}-e{episode['episode_id']}-control",
                failure_signature="",
                predicted_outcome="no_recurring_structure",
                observed_outcome="no_recurring_structure",
                delta="",
                constraint_violations=[],
                horizon_reward=0.0 if config_id in {"E0", "E2"} else 0.75,
                grounded_admission=True if config_id == "E7" else None,
            ))
        return events

    primary = sequence["hazard_signatures"][0]
    secondary = sequence["hazard_signatures"][1] if len(sequence["hazard_signatures"]) > 1 else primary

    if config_id in {"E0", "E3"}:
        reward = 0.0 if config_id == "E0" else 0.75
        return [
            make_event(
                config_id=config_id,
                sequence=sequence,
                episode=episodes[0],
                event_type="observe",
                proposal_id=f"{sequence['sequence_id']}-{config_id}-e1-observe",
                failure_signature=primary,
                predicted_outcome="expected_success",
                observed_outcome="failure_observed",
                delta="failure_observed",
                constraint_violations=[primary],
                horizon_reward=reward,
            ),
            make_event(
                config_id=config_id,
                sequence=sequence,
                episode=episodes[1],
                event_type="repair",
                proposal_id=f"{sequence['sequence_id']}-{config_id}-e2-local-repair",
                failure_signature=primary,
                predicted_outcome="local_repair",
                observed_outcome="local_repair_applied",
                delta="corrected",
                constraint_violations=[],
                repair_radius=1,
                evidence_preserved=True,
                time_to_correction=1,
                time_to_correction_censored=False,
                horizon_reward=reward,
            ),
            make_event(
                config_id=config_id,
                sequence=sequence,
                episode=episodes[2],
                event_type="observe",
                proposal_id=f"{sequence['sequence_id']}-{config_id}-e3-recur",
                failure_signature=primary,
                predicted_outcome="expected_success_after_repair",
                observed_outcome="failure_recurred",
                delta="failure_recurred",
                constraint_violations=[primary],
                horizon_reward=reward,
            ),
            make_event(
                config_id=config_id,
                sequence=sequence,
                episode=episodes[3],
                event_type="reject",
                proposal_id=f"{sequence['sequence_id']}-{config_id}-e4-reject",
                failure_signature=secondary,
                predicted_outcome="unsafe_repair",
                observed_outcome="rejected_before_commit",
                delta="proposal_rejected",
                constraint_violations=[secondary],
                rejection_reason_code="mnemosyne_atp_rejected_unsafe_proposal",
                horizon_reward=reward,
            ),
        ]

    reward = 0.5 if config_id == "E2" else 0.9
    grounded = True if config_id == "E7" else None
    return [
        make_event(
            config_id=config_id,
            sequence=sequence,
            episode=episodes[0],
            event_type="observe",
            proposal_id=f"{sequence['sequence_id']}-{config_id}-e1-observe",
            failure_signature=primary,
            predicted_outcome="expected_success",
            observed_outcome="failure_observed",
            delta="failure_observed",
            constraint_violations=[primary],
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        make_event(
            config_id=config_id,
            sequence=sequence,
            episode=episodes[1],
            event_type="repair",
            proposal_id=f"{sequence['sequence_id']}-{config_id}-e2-causal-repair",
            failure_signature=primary,
            predicted_outcome="causal_correction",
            observed_outcome="causal_correction_applied",
            delta="corrected",
            constraint_violations=[],
            repair_radius=1,
            evidence_preserved=True,
            time_to_correction=1,
            time_to_correction_censored=False,
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        make_event(
            config_id=config_id,
            sequence=sequence,
            episode=episodes[2],
            event_type="observe",
            proposal_id=f"{sequence['sequence_id']}-{config_id}-e3-monitor",
            failure_signature=primary,
            predicted_outcome="corrected_success",
            observed_outcome="corrected_success",
            delta="",
            constraint_violations=[],
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        make_event(
            config_id=config_id,
            sequence=sequence,
            episode=episodes[3],
            event_type="reject",
            proposal_id=f"{sequence['sequence_id']}-{config_id}-e4-reject-known-hazard",
            failure_signature="",
            predicted_outcome="repeat_known_hazard",
            observed_outcome="rejected_before_commit",
            delta="proposal_rejected",
            constraint_violations=[],
            rejection_reason_code="causal_audit_blocks_known_signature",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
    ]


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_summary_csv(path: Path, summary: Dict[str, Any]) -> None:
    rows = [
        ("num_events", summary["num_events"]),
        ("safety_passed", summary["safety_passed"]),
        ("invalid_commit_count", summary["safety_counts"]["invalid_commit_count"]),
        ("evidence_destroying_repair_count", summary["safety_counts"]["evidence_destroying_repair_count"]),
        ("orphaned_dependent_count", summary["safety_counts"]["orphaned_dependent_count"]),
        ("repeated_failure_rate", summary["repeated_failure_rate"]),
        ("repeated_failure_rate_controls", summary["repeated_failure_rate_controls"]),
        ("time_to_correction_observed_count", summary["time_to_correction_observed_count"]),
        ("time_to_correction_censored_count", summary["time_to_correction_censored_count"]),
        ("horizon_reward_mean", summary["horizon_reward_mean"]),
        ("grounded_admission_rate", summary["grounded_admission_rate"]),
        ("bracket_position_repeated_failure_rate", summary["bracket"]["position_repeated_failure_rate"]),
        ("bracket_position_horizon_reward", summary["bracket"]["position_horizon_reward"]),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)


def write_report(path: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    text = f"""# Mnemosyne REALM-Bench Tier 6 Adapter Report

Status: deterministic adapter validation only.

{CANONICAL_SENTENCE}

This report validates Mnemosyne's ability to emit REALM Tier-6-compatible
traces. It is not a live LLM run and must not be used as evidence for H1-H5.

## Manifest

- Run ID: {manifest['run_id']}
- Config: {manifest['config_id']}
- Phase: {manifest['phase']}
- Claim status: {manifest['claim_status']}
- Sequences: {manifest['num_sequences']}
- Episodes: {manifest['num_episodes']}
- Events: {manifest['num_events']}
- Families: {', '.join(manifest['families'])}

## Scorer summary

| Metric | Value |
|---|---:|
| Safety passed | {summary['safety_passed']} |
| Invalid commits | {summary['safety_counts']['invalid_commit_count']} |
| Evidence-destroying repairs | {summary['safety_counts']['evidence_destroying_repair_count']} |
| Orphaned dependents | {summary['safety_counts']['orphaned_dependent_count']} |
| Repeated failure rate | {summary['repeated_failure_rate']} |
| Control repeated failure rate | {summary['repeated_failure_rate_controls']} |
| Observed TTC count | {summary['time_to_correction_observed_count']} |
| Censored TTC count | {summary['time_to_correction_censored_count']} |
| Horizon reward mean | {summary['horizon_reward_mean']} |
| Grounded admission rate | {summary['grounded_admission_rate']} |
| RFR bracket position | {summary['bracket']['position_repeated_failure_rate']} |
| Horizon bracket position | {summary['bracket']['position_horizon_reward']} |

## Claim boundary

The deterministic adapter constructs expected traces by design. These outputs
validate adapter compatibility with REALM Tier 6 only. Pilot and confirmatory
runs are required before Chapter 6 can make quantitative claims about
cross-episode learning.
"""
    path.write_text(text, encoding="utf-8")


def emit_config_run(*, realm_root: Path, output_dir: Path, config_id: str) -> Dict[str, Any]:
    generator, scorer = load_realm_support(realm_root)
    sequences = generator.generate_development_sequences(realm_root)

    events: List[Dict[str, Any]] = []
    for sequence in sequences:
        events.extend(emit_events_for_sequence(config_id, sequence))

    summary = scorer.score_trace(events)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": f"mnemosyne_tier6_{config_id}_adapter_v0",
        "phase": "deterministic_adapter_validation",
        "claim_status": "not_chapter_result",
        "system_id": "mnemosyne",
        "adapter_id": "tier6-mnemosyne-adapter-v0",
        "config_id": config_id,
        "condition_switches": CONFIGS[config_id],
        "num_sequences": len(sequences),
        "num_episodes": sum(len(seq["episodes"]) for seq in sequences),
        "num_events": len(events),
        "families": sorted({seq["base_instance"]["family"] for seq in sequences}),
        "realm_root": str(realm_root),
        "canonical_sentence": CANONICAL_SENTENCE,
    }

    write_json(output_dir / "manifest.json", manifest)
    write_jsonl(output_dir / "events.jsonl", events)
    write_json(output_dir / "summary.json", summary)
    write_summary_csv(output_dir / "summary.csv", summary)
    write_report(output_dir / "report.md", manifest, summary)

    return {"manifest": manifest, "summary": summary, "events": events, "output_dir": str(output_dir)}


def emit_all_config_runs(
    *,
    realm_root: Path,
    output_base: Path,
    config_ids: Iterable[str] = ("E0", "E2", "E3", "E7"),
) -> Dict[str, Any]:
    results = {}
    for config_id in config_ids:
        result = emit_config_run(
            realm_root=realm_root,
            output_dir=output_base / f"mnemosyne_tier6_{config_id}_adapter_v0",
            config_id=config_id,
        )
        results[config_id] = {
            "output_dir": result["output_dir"],
            "num_events": result["manifest"]["num_events"],
            "safety_passed": result["summary"]["safety_passed"],
            "repeated_failure_rate": result["summary"]["repeated_failure_rate"],
            "horizon_reward_mean": result["summary"]["horizon_reward_mean"],
            "grounded_admission_rate": result["summary"]["grounded_admission_rate"],
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--realm-root", default=os.environ.get("REALM_BENCH_ROOT"))
    parser.add_argument("--output-base", default="results/realm_tier6_mnemosyne")
    args = parser.parse_args()

    realm_root = resolve_realm_root(args.realm_root)
    results = emit_all_config_runs(realm_root=realm_root, output_base=Path(args.output_base))
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
