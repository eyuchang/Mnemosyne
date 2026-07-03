# R96 REALM Tier-6 Dynamic Disruption Manual Prompt Pack

## Purpose

R96 prepares the first dynamic disruption live-LLM collection pack for Chapter 6.

Unlike the earlier static live-LLM pilot, R96 gives the proposer a workflow already in execution, committed evidence, uncommitted operations, and a mid-execution disruption.

The proposer must produce one of three responses:

- bounded repair
- safe rejection
- observation request

## Why Manual Collection

The public release must not require private API keys.

Therefore R96 defaults to manual prompt-pack collection:

1. generate prompts
2. paste prompts into Claude, GPT, DeepSeek expert, and DeepSeek instant
3. paste each JSON response into the generated response placeholder
4. validate responses locally

No API keys are required.

No vendor API is called by the script.

## Collection Size

Stage 1 dynamic closure pilot:

- one family: jobshop_breakdown
- one E7 full CRT-stack sequence
- ten dynamic disruption episodes
- four proposer packs
- forty manual live-LLM responses

This is the minimum dynamic pilot needed to close the gap left by the static plan-entry pilot.

## Commands

Export prompt pack:

    python benchmarks/realm/tier6_dynamic_disruption_manual.py export --output-dir results/realm_tier6_dynamic_disruption_manual/jobshop_e7_dynamic_pilot

Validate responses:

    python benchmarks/realm/tier6_dynamic_disruption_manual.py validate-responses --pack-dir results/realm_tier6_dynamic_disruption_manual/jobshop_e7_dynamic_pilot

## Outputs

Generated pack:

- manifest.json
- INSTRUCTIONS.md
- claude/e01_prompt.md through claude/e10_prompt.md
- gpt/e01_prompt.md through gpt/e10_prompt.md
- deepseek_expert/e01_prompt.md through deepseek_expert/e10_prompt.md
- deepseek_instant/e01_prompt.md through deepseek_instant/e10_prompt.md
- matching response JSON placeholders

Validation output:

- validation_report.json

## Response Schema

Each model must return one JSON object with these fields:

- schema
- action
- repair_summary
- affected_steps
- preserve_evidence
- rollback_scope
- expected_time_to_correction
- risk_flags
- should_reject
- confidence

Valid action values:

- repair
- reject
- observe

Valid rollback_scope values:

- none
- local
- unsafe

## Claim Boundary

R96 prepares prompts only.

It does not claim:

- dynamic repair performance
- REALM scoring
- API automation
- family-generalized live-LLM behavior
- production CTL-domain StateView realization
- proof of AGI, wisdom, or autonomous scientific reasoning

## Next Step

R97 should import the collected dynamic responses into Mnemosyne admission/runtime replay and emit Tier-6-compatible dynamic traces.
