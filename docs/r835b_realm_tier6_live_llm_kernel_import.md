# R83.5b REALM Tier-6 Live LLM Kernel-Import Comparison

## Purpose

R83.5b imports the R83.5a manual live-LLM response packs into a deterministic comparison/report path.

The goal is to compare live proposal behavior across:

- Claude
- GPT
- DeepSeek expert
- DeepSeek instant

The report is deterministic and reviewable. It intentionally avoids committing nondeterministic `events.jsonl` churn.

## Inputs

The default input packs are:

- `results/realm_tier6_live_llm_manual/claude_e7_pilot/`
- `results/realm_tier6_live_llm_manual/gpt_e7_pilot/`
- `results/realm_tier6_live_llm_manual/deepseek_e7_pilot/`
- `results/realm_tier6_live_llm_manual/deepseek_instant_e7_pilot/`

All four packs use the same E7 Tier-6 pilot sequence:

- `T6-7e17ef0cc5f3`
- `jobshop_breakdown`
- `datasets/J4/custom/j4_custom_001.json`
- `A=0, C=1, R=1, T=1`
- `full_crt_stack`
- episodes `e01` through `e10`

## Command

    python benchmarks/realm/tier6_live_llm_kernel_import.py report

Default output:

- `results/realm_tier6_live_llm_manual/kernel_import_report/comparison_report.json`
- `results/realm_tier6_live_llm_manual/kernel_import_report/comparison_report.md`

## Report Fields

The report summarizes:

- number of responses
- parse count
- `should_reject=true` count
- mean confidence
- policy style counts
- unsupported specificity counts
- deterministic admission recommendations

Policy styles are heuristic labels:

- `active_repair`
- `observation_first`
- `mixed`
- `unclear`

Admission recommendations are deterministic review labels, not production kernel decisions:

- `admit_parseable_proposal`
- `admit_with_grounding_flags`
- `review_high_unsupported_specificity`
- `model_requests_rejection`

## Claim Boundary

R83.5b phase 1 is a deterministic live-pack import/comparison report.

It is not yet:

- API-automated LLM behavior
- production CTL-domain StateView realization
- confirmatory Chapter 6 evidence
- proof of AGI, wisdom, or autonomous scientific reasoning

Mnemosyne still owns admission. REALM still owns scoring.

## Next Step

A later R83.5b phase may attach these response summaries to actual kernel trace records. If so, trace IDs and timestamps must be determinized before any generated `events.jsonl` is committed.
