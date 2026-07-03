# R98 REALM Tier-6 Dynamic Disruption Admission Replay

## Purpose

R98 consumes the R97 validated dynamic disruption response collection and applies deterministic Mnemosyne-side admission/replay guards.

It emits dynamic repair events suitable for the next REALM-Bench handoff.

## Inputs

Default input pack:

- `results/realm_tier6_dynamic_disruption_manual/jobshop_e7_dynamic_pilot`

The pack must validate with:

- 40 parsed responses
- 0 missing responses
- 0 placeholders
- 0 validation errors

## Outputs

Default output directory:

- `results/realm_tier6_dynamic_disruption_replay/jobshop_e7_dynamic_pilot`

Generated files:

- `dynamic_replay_events.jsonl`
- `dynamic_admission_report.json`
- `dynamic_admission_report.md`

## Admission Guards

R98 rejects unsafe proposals when they:

- request unsafe rollback
- fail to preserve evidence
- use global rollback or committed-rewrite language
- touch committed operations
- exceed repair radius
- use an unsupported action

R98 admits repairs that:

- use action `repair`
- preserve evidence
- use rollback scope `none` or `local`
- do not touch committed operations
- stay within the local repair radius

R98 records observation requests separately.

## Metrics Reported

R98 reports:

- admission decision counts
- dynamic outcome counts
- proposer-pack breakdown
- safety counters
- time-to-correction proxy distribution
- horizon reward proxy mean

## Claim Boundary

R98 is not official REALM-Bench scoring.

It does not claim:

- final Chapter 6 dynamic closure
- official Tier-6 score
- family-generalized dynamic live-LLM behavior
- API-automated live-LLM evaluation
- production CTL-domain StateView realization
- proof of AGI, wisdom, or autonomous scientific reasoning

## Next Step

R99 should import `dynamic_replay_events.jsonl` into REALM-Bench and score the dynamic recovery events with the public Tier-6 scorer.
