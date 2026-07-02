"""Runtime-backed Mnemosyne adapter for REALM-Bench Tier 6.

This adapter uses Mnemosyne's runtime proposal/admission substrate:
RuntimeProposalEnvelope, RuntimeProposalStore, and RuntimeAdmissionFacade.

It is stronger than the deterministic R80 adapter because each REALM event is
backed by a submitted runtime proposal and an actual recorded admission
decision. It is still not a live LLM run and not yet a full kernel/ATP commit
run.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.realm.tier6_mnemosyne_adapter import (  # noqa: E402
    CANONICAL_SENTENCE,
    CONFIGS,
    FIXTURE_TIMESTAMP_UTC,
    load_realm_support,
    make_event,
    resolve_realm_root,
    write_json,
    write_jsonl,
)
from mnemosyne.runtime.admission import RuntimeAdmissionFacade  # noqa: E402
from mnemosyne.runtime.models import (  # noqa: E402
    AgentSpec,
    RuntimeProposalEnvelope,
    WorkflowBinding,
    WorkflowSpec,
)
from mnemosyne.runtime.proposals import RuntimeProposalStore  # noqa: E402


class _WorkflowAccessor:
    def __init__(self, workflow: WorkflowSpec, binding: WorkflowBinding):
        self.workflow = workflow
        self.binding = binding

    def get_workflow(self, workflow_id: str) -> WorkflowSpec:
        if workflow_id != self.workflow.workflow_id:
            raise KeyError(f"unknown workflow_id: {workflow_id}")
        return self.workflow

    def get_binding(self, binding_id: str) -> WorkflowBinding:
        if binding_id != self.binding.binding_id:
            raise KeyError(f"unknown binding_id: {binding_id}")
        return self.binding


class _AgentAccessor:
    def __init__(self, agent: AgentSpec):
        self.agent = agent

    def get_agent(self, agent_id: str) -> AgentSpec:
        if agent_id != self.agent.agent_id:
            raise KeyError(f"unknown agent_id: {agent_id}")
        return self.agent


class _StaticRuntimeRegistry:
    def __init__(self, workflow: WorkflowSpec, binding: WorkflowBinding, agent: AgentSpec):
        self.workflows = _WorkflowAccessor(workflow, binding)
        self.agents = _AgentAccessor(agent)


class RuntimeTraceHarness:
    """Small deterministic harness over Mnemosyne runtime proposal/admission APIs."""

    def __init__(self, *, sequence: Dict[str, Any], config_id: str):
        self.sequence = sequence
        self.config_id = config_id
        self.tenant_id = "tenant:realm_tier6"
        self.workflow_id = f"workflow:{sequence['sequence_id']}:{config_id}"
        self.binding_id = f"binding:{sequence['sequence_id']}:{config_id}"
        self.entity_id = f"entity:{sequence['sequence_id']}"
        self.agent_id = f"agent:mnemosyne:{config_id}"
        self.app_id = "realm_tier6"
        self.schema_id = "realm_tier6_trace"
        self.fsm = "realm_tier6_runtime"

        workflow = WorkflowSpec(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            app_id=self.app_id,
            schema_id=self.schema_id,
            fsm=self.fsm,
            workflow_type="realm_tier6_sequence",
            created_by="tier6-runtime-adapter",
            metadata={
                "sequence_id": sequence["sequence_id"],
                "config_id": config_id,
                "adapter_id": "tier6-mnemosyne-runtime-adapter-v0",
            },
        )
        binding = WorkflowBinding(
            binding_id=self.binding_id,
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            entity_id=self.entity_id,
            fsm=self.fsm,
            initial_state="episode_pending",
            created_by="tier6-runtime-adapter",
            metadata={
                "sequence_id": sequence["sequence_id"],
                "is_control_sequence": sequence["is_control_sequence"],
            },
        )
        agent = AgentSpec(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            agent_type="mnemosyne_runtime_adapter",
            display_name=f"Mnemosyne {config_id}",
            capabilities=tuple(k for k, v in CONFIGS[config_id].items() if k in {"C", "R", "T", "A"} and v),
            model_id=None,
            metadata={"config": CONFIGS[config_id]},
        )

        self.registry = _StaticRuntimeRegistry(workflow, binding, agent)
        self.proposal_store = RuntimeProposalStore()
        self.admission = RuntimeAdmissionFacade(self.proposal_store)

    def submit_and_decide(
        self,
        *,
        proposal_id: str,
        episode: Dict[str, Any],
        event_type: str,
        accepted: bool,
        reason: str,
        error_codes: List[str],
        payload: Dict[str, Any],
    ):
        before = len(self.proposal_store.list_trace_events())

        envelope = RuntimeProposalEnvelope(
            proposal_id=proposal_id,
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            binding_id=self.binding_id,
            entity_id=self.entity_id,
            agent_id=self.agent_id,
            app_id=self.app_id,
            schema_id=self.schema_id,
            proposal_kind=f"realm_tier6_{event_type}",
            payload=payload,
            assumptions=tuple(payload.get("assumptions", [])),
            provenance={
                "adapter_id": "tier6-mnemosyne-runtime-adapter-v0",
                "sequence_id": self.sequence["sequence_id"],
                "episode_id": episode["episode_id"],
                "config_id": self.config_id,
            },
        )
        self.proposal_store.submit_proposal(envelope, registry=self.registry)

        if accepted:
            decision = self.admission.accept_proposal(
                proposal_id=proposal_id,
                reason=reason,
                committed_rids=[f"rid:{proposal_id}"],
                decision_id=f"decision:accept:{proposal_id}",
                metadata={
                    "realm_event_type": event_type,
                    "runtime_adapter_phase": "proposal_admission_validation",
                },
            )
        else:
            decision = self.admission.reject_proposal(
                proposal_id=proposal_id,
                reason=reason,
                error_codes=error_codes,
                decision_id=f"decision:reject:{proposal_id}",
                metadata={
                    "realm_event_type": event_type,
                    "runtime_adapter_phase": "proposal_admission_validation",
                },
            )

        after_events = self.proposal_store.list_trace_events()[before:]
        return decision, after_events


def _runtime_event(
    *,
    harness: RuntimeTraceHarness,
    config_id: str,
    sequence: Dict[str, Any],
    episode: Dict[str, Any],
    event_type: str,
    proposal_suffix: str,
    failure_signature: str,
    predicted_outcome: str,
    observed_outcome: str,
    delta: str,
    constraint_violations: List[str],
    accepted: bool,
    reason: str,
    error_codes: List[str] | None = None,
    repair_radius: int = 0,
    evidence_preserved: bool = True,
    time_to_correction: int | None = None,
    time_to_correction_censored: bool = True,
    rejection_reason_code: str | None = None,
    horizon_reward: float | None = None,
    grounded_admission: bool | None = None,
) -> Dict[str, Any]:
    proposal_id = f"{sequence['sequence_id']}-{config_id}-e{episode['episode_id']}-{proposal_suffix}"

    payload = {
        "sequence_id": sequence["sequence_id"],
        "episode_id": episode["episode_id"],
        "config_id": config_id,
        "event_type": event_type,
        "failure_signature": failure_signature,
        "predicted_outcome": predicted_outcome,
        "observed_outcome": observed_outcome,
        "delta": delta,
        "constraint_violations": constraint_violations,
        "assumptions": [
            {
                "kind": "realm_tier6_hazard_signature",
                "value": failure_signature,
                "active": bool(failure_signature),
            }
        ],
    }

    decision, runtime_trace_events = harness.submit_and_decide(
        proposal_id=proposal_id,
        episode=episode,
        event_type=event_type,
        accepted=accepted,
        reason=reason,
        error_codes=error_codes or [],
        payload=payload,
    )

    event = make_event(
        config_id=config_id,
        sequence=sequence,
        episode=episode,
        event_type=event_type,
        proposal_id=proposal_id,
        failure_signature=failure_signature,
        predicted_outcome=predicted_outcome,
        observed_outcome=observed_outcome,
        delta=delta,
        constraint_violations=constraint_violations,
        repair_radius=repair_radius,
        evidence_preserved=evidence_preserved,
        time_to_correction=time_to_correction,
        time_to_correction_censored=time_to_correction_censored,
        rejection_reason_code=rejection_reason_code,
        horizon_reward=horizon_reward,
        grounded_admission=grounded_admission,
    )

    event["runtime_surface"] = {
        "adapter_id": "tier6-mnemosyne-runtime-adapter-v0",
        "runtime_phase": "proposal_admission_validation",
        "decision_id": decision.decision_id,
        "accepted": decision.accepted,
        "reason": decision.reason,
        "error_codes": list(decision.error_codes),
        "committed_rids": list(decision.committed_rids),
        "trace_events": [asdict(trace_event) for trace_event in runtime_trace_events],
    }

    return event


def emit_runtime_events_for_sequence(config_id: str, sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
    if config_id not in CONFIGS:
        raise ValueError(f"unknown config_id: {config_id}")

    harness = RuntimeTraceHarness(sequence=sequence, config_id=config_id)
    episodes = sequence["episodes"]
    events: List[Dict[str, Any]] = []

    if sequence["is_control_sequence"] or not sequence["hazard_signatures"]:
        for episode in episodes:
            events.append(_runtime_event(
                harness=harness,
                config_id=config_id,
                sequence=sequence,
                episode=episode,
                event_type="observe",
                proposal_suffix="control",
                failure_signature="",
                predicted_outcome="no_recurring_structure",
                observed_outcome="no_recurring_structure",
                delta="",
                constraint_violations=[],
                accepted=True,
                reason="control observation admitted",
                horizon_reward=0.0 if config_id in {"E0", "E2"} else 0.75,
                grounded_admission=True if config_id == "E7" else None,
            ))
        return events

    primary = sequence["hazard_signatures"][0]
    secondary = sequence["hazard_signatures"][1] if len(sequence["hazard_signatures"]) > 1 else primary

    if config_id in {"E0", "E3"}:
        reward = 0.0 if config_id == "E0" else 0.75
        return [
            _runtime_event(
                harness=harness,
                config_id=config_id,
                sequence=sequence,
                episode=episodes[0],
                event_type="observe",
                proposal_suffix="observe",
                failure_signature=primary,
                predicted_outcome="expected_success",
                observed_outcome="failure_observed",
                delta="failure_observed",
                constraint_violations=[primary],
                accepted=True,
                reason="runtime admitted observed failure record",
                horizon_reward=reward,
            ),
            _runtime_event(
                harness=harness,
                config_id=config_id,
                sequence=sequence,
                episode=episodes[1],
                event_type="repair",
                proposal_suffix="local-repair",
                failure_signature=primary,
                predicted_outcome="local_repair",
                observed_outcome="local_repair_applied",
                delta="corrected",
                constraint_violations=[],
                accepted=True,
                reason="runtime admitted local repair",
                repair_radius=1,
                evidence_preserved=True,
                time_to_correction=1,
                time_to_correction_censored=False,
                horizon_reward=reward,
            ),
            _runtime_event(
                harness=harness,
                config_id=config_id,
                sequence=sequence,
                episode=episodes[2],
                event_type="observe",
                proposal_suffix="recur",
                failure_signature=primary,
                predicted_outcome="expected_success_after_repair",
                observed_outcome="failure_recurred",
                delta="failure_recurred",
                constraint_violations=[primary],
                accepted=True,
                reason="runtime admitted recurrence observation",
                horizon_reward=reward,
            ),
            _runtime_event(
                harness=harness,
                config_id=config_id,
                sequence=sequence,
                episode=episodes[3],
                event_type="reject",
                proposal_suffix="reject",
                failure_signature=secondary,
                predicted_outcome="unsafe_repair",
                observed_outcome="rejected_before_commit",
                delta="proposal_rejected",
                constraint_violations=[secondary],
                accepted=False,
                reason="runtime rejected unsafe proposal",
                error_codes=["MNEMOSYNE_ATP_REJECTED_UNSAFE_PROPOSAL"],
                rejection_reason_code="mnemosyne_atp_rejected_unsafe_proposal",
                horizon_reward=reward,
            ),
        ]

    reward = 0.5 if config_id == "E2" else 0.9
    grounded = True if config_id == "E7" else None

    return [
        _runtime_event(
            harness=harness,
            config_id=config_id,
            sequence=sequence,
            episode=episodes[0],
            event_type="observe",
            proposal_suffix="observe",
            failure_signature=primary,
            predicted_outcome="expected_success",
            observed_outcome="failure_observed",
            delta="failure_observed",
            constraint_violations=[primary],
            accepted=True,
            reason="runtime admitted observed failure record",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _runtime_event(
            harness=harness,
            config_id=config_id,
            sequence=sequence,
            episode=episodes[1],
            event_type="repair",
            proposal_suffix="causal-repair",
            failure_signature=primary,
            predicted_outcome="causal_correction",
            observed_outcome="causal_correction_applied",
            delta="corrected",
            constraint_violations=[],
            accepted=True,
            reason="runtime admitted causal repair",
            repair_radius=1,
            evidence_preserved=True,
            time_to_correction=1,
            time_to_correction_censored=False,
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _runtime_event(
            harness=harness,
            config_id=config_id,
            sequence=sequence,
            episode=episodes[2],
            event_type="observe",
            proposal_suffix="monitor",
            failure_signature=primary,
            predicted_outcome="corrected_success",
            observed_outcome="corrected_success",
            delta="",
            constraint_violations=[],
            accepted=True,
            reason="runtime admitted corrected monitor observation",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _runtime_event(
            harness=harness,
            config_id=config_id,
            sequence=sequence,
            episode=episodes[3],
            event_type="reject",
            proposal_suffix="reject-known-hazard",
            failure_signature="",
            predicted_outcome="repeat_known_hazard",
            observed_outcome="rejected_before_commit",
            delta="proposal_rejected",
            constraint_violations=[],
            accepted=False,
            reason="runtime rejected known recurring hazard before commit",
            error_codes=["CAUSAL_AUDIT_BLOCKS_KNOWN_SIGNATURE"],
            rejection_reason_code="causal_audit_blocks_known_signature",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
    ]


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


def write_runtime_report(path: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    text = f"""# Mnemosyne REALM-Bench Tier 6 Runtime Adapter Report

Status: runtime proposal/admission adapter validation only.

{CANONICAL_SENTENCE}

This report validates Mnemosyne's runtime proposal/admission substrate as a
source for REALM Tier-6-compatible traces. It uses RuntimeProposalEnvelope,
RuntimeProposalStore, and RuntimeAdmissionFacade.

It is not a live LLM run and not yet a full kernel/ATP commit run.

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

These outputs validate runtime proposal/admission trace compatibility with
REALM Tier 6. Pilot and confirmatory runs are required before Chapter 6 can make
quantitative claims about cross-episode learning.
"""
    path.write_text(text, encoding="utf-8")


def emit_runtime_config_run(
    *,
    realm_root: Path,
    output_dir: Path,
    config_id: str,
) -> Dict[str, Any]:
    generator, scorer = load_realm_support(realm_root)
    sequences = generator.generate_development_sequences(realm_root)

    events: List[Dict[str, Any]] = []
    for sequence in sequences:
        events.extend(emit_runtime_events_for_sequence(config_id, sequence))

    summary = scorer.score_trace(events)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": f"mnemosyne_tier6_{config_id}_runtime_adapter_v0",
        "phase": "runtime_proposal_admission_adapter_validation",
        "claim_status": "not_chapter_result",
        "system_id": "mnemosyne",
        "adapter_id": "tier6-mnemosyne-runtime-adapter-v0",
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
    write_runtime_report(output_dir / "report.md", manifest, summary)

    return {
        "manifest": manifest,
        "summary": summary,
        "events": events,
        "output_dir": str(output_dir),
    }


def emit_all_runtime_config_runs(
    *,
    realm_root: Path,
    output_base: Path,
    config_ids: Iterable[str] = ("E0", "E2", "E3", "E7"),
) -> Dict[str, Any]:
    results = {}
    for config_id in config_ids:
        result = emit_runtime_config_run(
            realm_root=realm_root,
            output_dir=output_base / f"mnemosyne_tier6_{config_id}_runtime_adapter_v0",
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
    parser.add_argument("--output-base", default="results/realm_tier6_mnemosyne_runtime")
    args = parser.parse_args()

    realm_root = resolve_realm_root(args.realm_root)
    results = emit_all_runtime_config_runs(
        realm_root=realm_root,
        output_base=Path(args.output_base),
    )
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
