"""Kernel-admission-backed Mnemosyne adapter for REALM-Bench Tier 6.

R83 uses Mnemosyne's KernelAdmissionAdapter over SQLiteRuntimeRepository.
Accepted events go through accept_via_kernel with controlled KernelCommitResult.
Blocked events go through reject_before_commit. Each event also appends a
durable RecoveryEvent and exports a StateView read snapshot.

Boundary: this validates kernel-admission and evidence-surface wiring. It is
not a live LLM run and not yet a full production CTL-domain commit run.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.realm.tier6_mnemosyne_adapter import (  # noqa: E402
    CANONICAL_SENTENCE,
    CONFIGS,
    load_realm_support,
    make_event,
    resolve_realm_root,
    write_json,
    write_jsonl,
)
from mnemosyne.core.recovery.events import (  # noqa: E402
    RecoveryEvent,
    recovery_event_to_dict,
)
from mnemosyne.runtime.kernel_admission import (  # noqa: E402
    KernelAdmissionAdapter,
    KernelCommitRequest,
    KernelCommitResult,
)
from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository  # noqa: E402
from mnemosyne.store.sqlite import SQLiteStore  # noqa: E402


@dataclass
class ControlledKernelCommitter:
    results_by_proposal_id: dict[str, KernelCommitResult] = field(default_factory=dict)
    calls: list[KernelCommitRequest] = field(default_factory=list)

    def commit(self, request: KernelCommitRequest) -> KernelCommitResult:
        self.calls.append(request)
        return self.results_by_proposal_id[request.proposal_id]


class KernelTraceHarness:
    """Small harness over KernelAdmissionAdapter for one Tier-6 sequence/config."""

    def __init__(self, *, sequence: Dict[str, Any], config_id: str, runtime_db_path: Path):
        self.sequence = sequence
        self.config_id = config_id

        self.tenant_id = "tenant:realm_tier6_kernel"
        self.workflow_id = f"workflow:{sequence['sequence_id']}:{config_id}:kernel"
        self.binding_id = f"binding:{sequence['sequence_id']}:{config_id}:kernel"
        self.agent_id = f"agent:mnemosyne:{config_id}:kernel"
        self.agent_binding_id = f"agent-binding:{sequence['sequence_id']}:{config_id}:kernel"
        self.entity_id = f"entity:{sequence['sequence_id']}"
        self.fsm = "REALMTier6KernelFSM"
        self.app_id = "realm_tier6"
        self.schema_id = "realm_tier6.kernel_admission"
        self.recovery_id = f"recovery:{sequence['sequence_id']}:{config_id}:kernel"
        self.recovery_seq = 0

        self.repo = SQLiteRuntimeRepository(runtime_db_path)
        self.store = SQLiteStore()
        self.committer = ControlledKernelCommitter()
        self.adapter = KernelAdmissionAdapter(self.repo, self.committer)

        self._seed_runtime()

    def _seed_runtime(self) -> None:
        self.repo.create_workflow(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            fsm=self.fsm,
            app_id=self.app_id,
            schema_id=self.schema_id,
            metadata={
                "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
                "sequence_id": self.sequence["sequence_id"],
                "config_id": self.config_id,
            },
        )
        self.repo.create_workflow_binding(
            binding_id=self.binding_id,
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            entity_id=self.entity_id,
            fsm=self.fsm,
            app_id=self.app_id,
            schema_id=self.schema_id,
            metadata={"is_control_sequence": self.sequence["is_control_sequence"]},
        )
        self.repo.create_agent(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            agent_type="mnemosyne_kernel_adapter",
            display_name=f"Mnemosyne Kernel {self.config_id}",
            metadata={"config": CONFIGS[self.config_id]},
        )
        self.repo.create_agent_binding(
            agent_binding_id=self.agent_binding_id,
            agent_id=self.agent_id,
            workflow_id=self.workflow_id,
            binding_id=self.binding_id,
            tenant_id=self.tenant_id,
            entity_id=self.entity_id,
            fsm=self.fsm,
            app_id=self.app_id,
            schema_id=self.schema_id,
            metadata={"role": "tier6_kernel_adapter"},
        )

    def submit_proposal(self, *, proposal_id: str, episode: Dict[str, Any], payload: Dict[str, Any]) -> None:
        self.repo.submit_proposal(
            proposal_id=proposal_id,
            workflow_id=self.workflow_id,
            binding_id=self.binding_id,
            agent_id=self.agent_id,
            agent_binding_id=self.agent_binding_id,
            tenant_id=self.tenant_id,
            entity_id=self.entity_id,
            fsm=self.fsm,
            app_id=self.app_id,
            schema_id=self.schema_id,
            payload=payload,
            metadata={
                "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
                "sequence_id": self.sequence["sequence_id"],
                "episode_id": episode["episode_id"],
                "config_id": self.config_id,
            },
        )

    def decide(
        self,
        *,
        proposal_id: str,
        payload: Dict[str, Any],
        accepted: bool,
        reason: str,
        error_codes: List[str],
    ):
        if accepted:
            rid = f"rid:realm-tier6:{proposal_id}"
            audit_ref = f"audit:realm-tier6:{proposal_id}"
            self.committer.results_by_proposal_id[proposal_id] = KernelCommitResult(
                ok=True,
                status="committed",
                committed_rids=(rid,),
                audit_ref=audit_ref,
                message="controlled kernel commit succeeded",
            )
            return self.adapter.accept_via_kernel(
                proposal_id=proposal_id,
                decision_id=f"decision:accept:{proposal_id}",
                tenant_id=self.tenant_id,
                workflow_id=self.workflow_id,
                binding_id=self.binding_id,
                agent_id=self.agent_id,
                entity_id=self.entity_id,
                fsm=self.fsm,
                app_id=self.app_id,
                schema_id=self.schema_id,
                payload=payload,
                metadata={
                    "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
                    "controlled_kernel_commit": True,
                },
            )

        return self.adapter.reject_before_commit(
            proposal_id=proposal_id,
            decision_id=f"decision:reject:{proposal_id}",
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            binding_id=self.binding_id,
            agent_id=self.agent_id,
            reason=reason,
            error_codes=tuple(error_codes),
            metadata={
                "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
                "controlled_kernel_commit": False,
            },
        )

    async def append_recovery_and_stateview(
        self,
        *,
        proposal_id: str,
        episode: Dict[str, Any],
        event_type: str,
        decision: Any,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.recovery_seq += 1
        recovery_event = RecoveryEvent(
            event_id=f"recovery-event:{proposal_id}",
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            recovery_id=self.recovery_id,
            sequence_no=self.recovery_seq,
            event_type=f"realm_tier6_{event_type}_kernel_admission",
            idempotency_key=f"idem:{proposal_id}",
            causality_key=payload.get("failure_signature") or proposal_id,
            payload={
                "proposal_id": proposal_id,
                "episode_id": episode["episode_id"],
                "config_id": self.config_id,
                "event_type": event_type,
                "runtime_decision": decision.runtime_decision,
                "status": decision.status,
                "kernel_commit_performed": decision.kernel_commit_performed,
                "committed_rids": list(decision.committed_rids),
                "error_codes": list(decision.error_codes),
            },
        )
        appended = await self.store.append_recovery_event(recovery_event)
        state_view = await self.store.get_state_view(self.tenant_id, self.entity_id, self.fsm)
        return {
            "recovery_event": recovery_event_to_dict(appended),
            "stateview_snapshot": asdict(state_view),
        }

    def kernel_evidence(
        self,
        *,
        proposal_id: str,
        episode: Dict[str, Any],
        event_type: str,
        decision: Any,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        recovery_state = asyncio.run(
            self.append_recovery_and_stateview(
                proposal_id=proposal_id,
                episode=episode,
                event_type=event_type,
                decision=decision,
                payload=payload,
            )
        )

        return {
            "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
            "kernel_phase": "kernel_admission_validation",
            "decision": asdict(decision),
            "kernel_calls": [asdict(call) for call in self.committer.calls if call.proposal_id == proposal_id],
            "runtime_trace_events": self.repo.list_trace_events(proposal_id=proposal_id),
            "recovery_event": recovery_state["recovery_event"],
            "stateview_snapshot": recovery_state["stateview_snapshot"],
            "stateview_boundary_note": (
                "StateView is read through the public SQLiteStore API. "
                "R83 does not yet perform full CTL-domain record commits."
            ),
        }


def _kernel_event(
    *,
    harness: KernelTraceHarness,
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
    }

    harness.submit_proposal(proposal_id=proposal_id, episode=episode, payload=payload)
    decision = harness.decide(
        proposal_id=proposal_id,
        payload=payload,
        accepted=accepted,
        reason=reason,
        error_codes=error_codes or [],
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
    event["kernel_surface"] = harness.kernel_evidence(
        proposal_id=proposal_id,
        episode=episode,
        event_type=event_type,
        decision=decision,
        payload=payload,
    )
    return event


def emit_kernel_events_for_sequence(config_id: str, sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
    if config_id not in CONFIGS:
        raise ValueError(f"unknown config_id: {config_id}")

    with tempfile.TemporaryDirectory() as tmpdir:
        harness = KernelTraceHarness(
            sequence=sequence,
            config_id=config_id,
            runtime_db_path=Path(tmpdir) / "runtime.sqlite3",
        )
        return _emit_kernel_events_with_harness(config_id, sequence, harness)


def _emit_kernel_events_with_harness(
    config_id: str,
    sequence: Dict[str, Any],
    harness: KernelTraceHarness,
) -> List[Dict[str, Any]]:
    episodes = sequence["episodes"]

    if sequence["is_control_sequence"] or not sequence["hazard_signatures"]:
        events = []
        for episode in episodes:
            events.append(_kernel_event(
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
                reason="kernel admitted control observation",
                horizon_reward=0.0 if config_id in {"E0", "E2"} else 0.75,
                grounded_admission=True if config_id == "E7" else None,
            ))
        return events

    primary = sequence["hazard_signatures"][0]
    secondary = sequence["hazard_signatures"][1] if len(sequence["hazard_signatures"]) > 1 else primary

    if config_id in {"E0", "E3"}:
        reward = 0.0 if config_id == "E0" else 0.75
        return [
            _kernel_event(
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
                reason="kernel admitted observed failure record",
                horizon_reward=reward,
            ),
            _kernel_event(
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
                reason="kernel admitted local repair",
                repair_radius=1,
                evidence_preserved=True,
                time_to_correction=1,
                time_to_correction_censored=False,
                horizon_reward=reward,
            ),
            _kernel_event(
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
                reason="kernel admitted recurrence observation",
                horizon_reward=reward,
            ),
            _kernel_event(
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
                reason="kernel rejected unsafe proposal before commit",
                error_codes=["MNEMOSYNE_KERNEL_REJECTED_UNSAFE_PROPOSAL"],
                rejection_reason_code="mnemosyne_kernel_rejected_unsafe_proposal",
                horizon_reward=reward,
            ),
        ]

    reward = 0.5 if config_id == "E2" else 0.9
    grounded = True if config_id == "E7" else None

    return [
        _kernel_event(
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
            reason="kernel admitted observed failure record",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _kernel_event(
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
            reason="kernel admitted causal repair",
            repair_radius=1,
            evidence_preserved=True,
            time_to_correction=1,
            time_to_correction_censored=False,
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _kernel_event(
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
            reason="kernel admitted corrected monitor observation",
            horizon_reward=reward,
            grounded_admission=grounded,
        ),
        _kernel_event(
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
            reason="kernel rejected known recurring hazard before commit",
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


def write_kernel_report(path: Path, manifest: Dict[str, Any], summary: Dict[str, Any]) -> None:
    text = f"""# Mnemosyne REALM-Bench Tier 6 Kernel Adapter Report

Status: kernel-admission adapter validation only.

{CANONICAL_SENTENCE}

This report validates Mnemosyne's KernelAdmissionAdapter surface as a source for
REALM Tier-6-compatible traces. Accepted events pass through accept_via_kernel;
blocked events pass through reject_before_commit. Durable RecoveryEvent records
and StateView API snapshots are attached as evidence.

It is not a live LLM run and not yet a full production CTL-domain commit run.

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

These outputs validate kernel-admission trace compatibility with REALM Tier 6.
They do not yet validate live LLM behavior, full production CTL commits, or
confirmatory Chapter 6 hypotheses.
"""
    path.write_text(text, encoding="utf-8")


def emit_kernel_config_run(
    *,
    realm_root: Path,
    output_dir: Path,
    config_id: str,
) -> Dict[str, Any]:
    generator, scorer = load_realm_support(realm_root)
    sequences = generator.generate_development_sequences(realm_root)

    events: List[Dict[str, Any]] = []
    for sequence in sequences:
        events.extend(emit_kernel_events_for_sequence(config_id, sequence))

    summary = scorer.score_trace(events)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": f"mnemosyne_tier6_{config_id}_kernel_adapter_v0",
        "phase": "kernel_admission_adapter_validation",
        "claim_status": "not_chapter_result",
        "system_id": "mnemosyne",
        "adapter_id": "tier6-mnemosyne-kernel-adapter-v0",
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
    write_kernel_report(output_dir / "report.md", manifest, summary)

    return {
        "manifest": manifest,
        "summary": summary,
        "events": events,
        "output_dir": str(output_dir),
    }


def emit_all_kernel_config_runs(
    *,
    realm_root: Path,
    output_base: Path,
    config_ids: Iterable[str] = ("E0", "E2", "E3", "E7"),
) -> Dict[str, Any]:
    results = {}
    for config_id in config_ids:
        result = emit_kernel_config_run(
            realm_root=realm_root,
            output_dir=output_base / f"mnemosyne_tier6_{config_id}_kernel_adapter_v0",
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
    parser.add_argument("--output-base", default="results/realm_tier6_mnemosyne_kernel")
    args = parser.parse_args()

    realm_root = resolve_realm_root(args.realm_root)
    results = emit_all_kernel_config_runs(
        realm_root=realm_root,
        output_base=Path(args.output_base),
    )
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
