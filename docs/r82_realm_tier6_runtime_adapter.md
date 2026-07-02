# R82: REALM-Bench Tier 6 Runtime Adapter

## Purpose

R82 adds a runtime-backed Mnemosyne adapter for REALM-Bench Tier 6.

Unlike the R80 deterministic adapter, R82 backs each emitted REALM event with
Mnemosyne runtime proposal/admission objects:

- RuntimeProposalEnvelope
- RuntimeProposalStore
- RuntimeAdmissionFacade
- RuntimeAdmissionDecision
- RuntimeTraceEvent

## Status

This is runtime proposal/admission adapter validation.

It is not yet:

- a live LLM run
- a full kernel commit run
- a full ATP/StateView/CTL evidence run
- confirmatory evidence for Chapter 6

## Pipeline

REALM Tier-6 sequence
-> Mnemosyne runtime proposal
-> runtime admission accept/reject
-> runtime trace events
-> REALM-compatible events.jsonl
-> REALM Tier-6 scorer

## Configurations

Current runtime-backed configurations:

- E0: engine only
- E2: +R causal audit
- E3: +T temporal accountability
- E7: +C+R+T full stack

## Outputs

The runtime adapter writes:

```text
results/realm_tier6_mnemosyne_runtime/
  mnemosyne_tier6_E0_runtime_adapter_v0/
  mnemosyne_tier6_E2_runtime_adapter_v0/
  mnemosyne_tier6_E3_runtime_adapter_v0/
  mnemosyne_tier6_E7_runtime_adapter_v0/
manifest.json
events.jsonl
summary.json
summary.csv
report.md
export REALM_BENCH_ROOT=/Users/edward.chang/REALM-Bench
python -m pytest -q tests/benchmarks/test_tier6_mnemosyne_runtime_adapter.py
python benchmarks/realm/tier6_mnemosyne_runtime_adapter.py
Expected pattern
E0: high repeated_failure_rate, low horizon_reward
E2: lower repeated_failure_rate than E0
E3: higher horizon_reward than E0 but recurrence may remain high
E7: lowest repeated_failure_rate, highest grounded_admission_rate
all configurations: safety_passed = true
Claim boundary

R82 validates that REALM Tier-6-compatible traces can be emitted from actual
Mnemosyne runtime proposal/admission surfaces.

It does not yet validate full kernel admission, durable recovery events, or
StateView evidence export. Those are the next milestones.
