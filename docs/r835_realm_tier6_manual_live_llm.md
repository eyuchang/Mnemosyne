# R83.5a: REALM-Bench Tier 6 Manual Live-LLM Injection

## Purpose

R83.5a adds manual live-LLM proposal injection for REALM-Bench Tier 6.

The LLM generates proposal text. Mnemosyne owns admission. REALM owns scoring.

This addresses the prior limitation that R80, R82, and R83 were not live LLM behavior.

## Boundary update

Old limitation:

    not live LLM behavior

New boundary:

    live LLM proposal behavior, manually injected and mediated by Mnemosyne
    kernel admission; not yet API-automated LLM behavior; not yet full
    production CTL-domain StateView realization; not yet confirmatory Chapter 6
    evidence.

## Pipeline

    REALM Tier-6 episode
    -> prompt file
    -> external/chat LLM
    -> pasted response file
    -> JSON parser
    -> Mnemosyne kernel-admission import step
    -> REALM-compatible events.jsonl
    -> REALM Tier-6 scorer

## What is hidden from the LLM

The prompt does not expose:

- ground-truth failure_signature
- scorer labels
- future observed outcome
- answer key

## Export prompts

Set:

    export REALM_BENCH_ROOT=/Users/edward.chang/REALM-Bench

Export an E7 pilot prompt pack:

    python benchmarks/realm/tier6_live_llm_manual.py export --configs E7 --subset pilot --max-sequences 1

The prompt pack is written to:

    results/realm_tier6_live_llm_manual/prompt_pack_v0/

## Manual collection

Open each prompt under:

    results/realm_tier6_live_llm_manual/prompt_pack_v0/prompts/

Paste it into the LLM.

Paste the LLM JSON answer into the matching file under:

    results/realm_tier6_live_llm_manual/prompt_pack_v0/responses/

## Validate responses

After responses are filled, run:

    python benchmarks/realm/tier6_live_llm_manual.py validate-responses

## Test fixture mode

For automated smoke testing only:

    python benchmarks/realm/tier6_live_llm_manual.py write-fixture-responses
    python benchmarks/realm/tier6_live_llm_manual.py validate-responses

Fixture responses are not live LLM behavior and must not be reported as live LLM evidence.

## Claim boundary

R83.5a validates prompt export, manual response capture, and response parsing for manually injected live LLM proposal behavior.

The next substep imports parsed responses into Mnemosyne kernel-admission events.

R83.5a does not validate API automation, full production CTL-domain StateView realization, or confirmatory H1-H5 hypotheses.

## Pilot Report

A detailed report for the Claude, GPT, DeepSeek expert, and DeepSeek instant manual live-LLM pilots is maintained in:

`docs/r835_realm_tier6_live_llm_pilot_report.md`

The report summarizes validation, episode-order auditing, model behavior differences, DeepSeek expert-vs-instant mode findings, and the claim boundary for R83.5a.
