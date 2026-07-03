# R81: REALM-Bench Tier 6 Experiment Plan

## Purpose

This document defines the planned experiments for Mnemosyne on REALM-Bench
Tier 6: Cross-Episode Causal Loop.

REALM-Bench owns the benchmark, trace schema, scorer, baselines, pilot subset,
and confirmatory protocol. Mnemosyne is one system submission that emits
Tier-6-compatible traces.

## Current completed milestone

R80 completed deterministic adapter validation.

Implemented outputs:

- events.jsonl
- manifest.json
- summary.json
- summary.csv
- report.md

Validated configurations:

- E0: engine only
- E2: +R causal audit
- E3: +T temporal accountability
- E7: +C+R+T full stack

Observed deterministic adapter-validation pattern:

- E0: repeated_failure_rate = 1.0, horizon_reward_mean = 0.0
- E2: repeated_failure_rate = 0.0, horizon_reward_mean = 0.3077
- E3: repeated_failure_rate = 1.0, horizon_reward_mean = 0.75
- E7: repeated_failure_rate = 0.0, horizon_reward_mean = 0.8423, grounded_admission_rate = 1.0
- all configurations: safety_passed = true

These are adapter-validation outputs only. They are not live LLM results and
must not be used as evidence for H1-H5.

## Experiment 1: Runtime trace equivalence test

### Goal

Replace deterministic hand-constructed events with events produced by the
actual Mnemosyne runtime.

Pipeline:

REALM Tier-6 sequence -> Mnemosyne runtime -> ATP admission / rejection ->
repair / observation / trace export -> REALM scorer.

### Problem specification

Each Tier-6 episode is translated into a Mnemosyne runtime task containing:

- sequence_id
- episode_id
- family
- source_path
- hazard_signature
- prior episode memory
- candidate proposal
- expected outcome
- observed outcome
- repair opportunity

The runtime-backed adapter must emit boundary-observable events:

- commit
- observe
- repair
- reject

Each exported event must preserve the REALM Tier-6 trace fields:

- failure_signature
- predicted_outcome
- observed_outcome
- delta
- constraint_violations
- repair metadata
- time_to_correction
- safety counters
- horizon_reward
- grounded_admission

### Expected outcome

Exact numbers are not the target. The target is qualitative equivalence with
the deterministic adapter:

- E0: high repeated_failure_rate, low horizon_reward, safety passed
- E2: lower repeated_failure_rate than E0, moderate horizon_reward, safety passed
- E3: higher horizon_reward than E0, but recurrence may remain high
- E7: lowest repeated_failure_rate, highest grounded_admission_rate, safety passed

Expected ordering:

- repeated_failure_rate(E7) <= repeated_failure_rate(E2) < repeated_failure_rate(E0)
- horizon_reward(E7) >= horizon_reward(E3) >= horizon_reward(E2) >= horizon_reward(E0)
- grounded_admission(E7) > grounded_admission(E0/E2/E3)
- safety_passed = true for all configurations

## Experiment 2: Four-point live runtime ablation

### Goal

Test whether C/R/T faculties produce diagnostically different effects.

Initial configurations:

- E0: engine only
- E2: +R causal audit
- E3: +T temporal accountability
- E7: +C+R+T full stack

### Problem families

The initial development generator covers:

- jobshop_breakdown
- ride_or_routing_disruption
- wedding_recovery

### Expected family-level outcomes

jobshop_breakdown:

- E0 repeats local repair mistakes
- E2 identifies recurring causal dependencies
- E3 improves horizon reward but may still repeat causal failures
- E7 gives strongest combined performance

ride_or_routing_disruption:

- E0 continues stale route assumptions
- E2 notices recurring stale-world signatures
- E3 improves horizon-aware choices
- E7 combines context, causal audit, and temporal accountability

wedding_recovery:

- E0 risks dependent-commitment errors
- E2 catches dependency failures
- E3 improves long-horizon planning
- E7 should best preserve safety and evidence

## Experiment 3: Full E0-E8 ablation

### Goal

Expand beyond the four-point slice to isolate all faculty combinations.

Planned mapping:

- E0: base engine
- E1: +C context grounding
- E2: +R causal audit
- E3: +T temporal accountability
- E4: +C+R
- E5: +C+T
- E6: +R+T
- E7: +C+R+T
- E8: full production stack with ATP, CTL, and StateView export

Expected interpretation:

- C should help contextual ambiguity
- R should reduce repeated causal failure
- T should improve horizon reward
- C+R+T should dominate single-faculty configurations
- E8 should match or exceed E7 while producing richer audit evidence

## Experiment 4: Frozen pilot subset

### Goal

Run the runtime-backed adapter on the frozen public pilot subset.

Pilot subset:

- 5 sequences
- 50 episodes
- 1 control sequence

Expected outcome:

- no schema failures
- no safety-gate violations
- controls do not inflate repeated_failure_rate
- E7 directionally outperforms E0

This remains pilot evidence only, not confirmatory evidence.

## Experiment 5: Confirmatory run

### Goal

Produce registered quantitative evidence for Chapter 6.

Requirements:

- fixed seeds
- frozen scorer
- frozen signature dictionary
- multiple families
- K = 10 episodes per sequence
- at least 20 percent controls
- no post-hoc metric changes

Target hypotheses:

- H1: E7 reduces repeated_failure_rate relative to E0
- H2: E7 improves time_to_correction relative to E0
- H3: E7 improves horizon_reward relative to E0
- H4: E7 improves grounded_admission_rate
- H5: E7 preserves the safety gate

Permitted Chapter 6 claim:

Mnemosyne improves cross-episode causal-loop recovery under Tier-6 scoring
while preserving the safety gate.

Disallowed overclaim:

- Mnemosyne proves AGI
- Mnemosyne proves wisdom
- Mnemosyne solves all long-horizon reasoning

## Next implementation milestone

The next implementation target is a runtime-backed adapter:

benchmarks/realm/tier6_mnemosyne_runtime_adapter.py

This adapter should call actual Mnemosyne ATP admission, recovery, CTL/event
logging, and StateView surfaces rather than constructing deterministic events
directly.
