# R83.5a REALM Tier-6 Manual Live-LLM Pilot Report

## Scope

This document records the R83.5a manual live-LLM proposal-injection pilot for REALM Tier-6.

The purpose of this segment is to address the reviewer concern that earlier adapters were not testing live LLM proposal behavior.

R83.5a tests live model proposal behavior under the same public REALM Tier-6 prompt pack while preserving the separation of responsibilities:

- LLMs generate proposals only.
- Mnemosyne owns admission.
- REALM owns scoring.
- Hidden failure signatures, scorer labels, future observed outcomes, and answer keys are not exposed to the LLM.

This is not yet API automation, kernel-trace import, full CTL-domain StateView realization, or confirmatory Chapter 6 evidence.

## Prompt Pack

All runs use the same E7 pilot prompt pack:

- Family: `jobshop_breakdown`
- Base instance: `datasets/J4/custom/j4_custom_001.json`
- Config: `E7`
- Condition stack: `A=0, C=1, R=1, T=1`
- Label: `full_crt_stack`
- Sequence: `T6-7e17ef0cc5f3`
- Episodes: `e01` through `e10`
- Control sequence: `true`

The public prompt contains only public episode metadata and visible prior history. It explicitly withholds:

- ground-truth failure signature
- scorer labels
- future observed outcome
- answer key

## Response Packs

Four manual live-LLM packs were collected:

| Pack | Location | Notes |
|---|---|---|
| Claude | `results/realm_tier6_live_llm_manual/claude_e7_pilot/` | Active minimal-repair / right-shift planner |
| GPT | `results/realm_tier6_live_llm_manual/gpt_e7_pilot/` | Conservative, observation-first, sometimes rejects unsupported action |
| DeepSeek expert | `results/realm_tier6_live_llm_manual/deepseek_e7_pilot/` | Structured technical repair narratives, but with unsupported concretization |
| DeepSeek instant | `results/realm_tier6_live_llm_manual/deepseek_instant_e7_pilot/` | Faster and higher-variance; often invents concrete machine/job/timing details |

## Validation Commands

Each pack validates using the R83.5a response validator.

    python benchmarks/realm/tier6_live_llm_manual.py validate-responses \
      --pack-dir results/realm_tier6_live_llm_manual/claude_e7_pilot

    python benchmarks/realm/tier6_live_llm_manual.py validate-responses \
      --pack-dir results/realm_tier6_live_llm_manual/gpt_e7_pilot

    python benchmarks/realm/tier6_live_llm_manual.py validate-responses \
      --pack-dir results/realm_tier6_live_llm_manual/deepseek_e7_pilot

    python benchmarks/realm/tier6_live_llm_manual.py validate-responses \
      --pack-dir results/realm_tier6_live_llm_manual/deepseek_instant_e7_pilot

Expected result for each completed pack:

- `num_parsed = 10`
- `num_missing = 0`
- `num_errors = 0`

## Order Audit

An additional filename/prompt-order audit was run for Claude and GPT, and should also be run for DeepSeek expert and DeepSeek instant.

The intended invariant is:

- `e01` response corresponds to prompt episode 1
- `e02` response corresponds to prompt episode 2
- ...
- `e10` response corresponds to prompt episode 10

Claude and GPT passed this audit. A duplicated Claude `e04/e05` response was detected and corrected.

Relevant commits:

- `83fab5b` Add Claude manual live LLM pilot responses for REALM Tier 6
- `a45000b` Correct Claude manual live LLM pilot e05 response
- `c6abff4` Add GPT manual live LLM pilot responses for REALM Tier 6

## Observed Model Behavior

### Claude

Claude consistently produced active repair proposals.

Observed pattern:

- minimal perturbation
- right-shift repair
- affected-operations rescheduling
- preserve completed operations
- log deltas for audit
- `should_reject = false` across the pilot

Claude’s behavior is useful as an active-repair baseline. It is less refusal-prone than GPT and usually frames the recovery as a conservative local repair rather than a full global reschedule.

### GPT

GPT was the most epistemically cautious model in this pilot.

Observed pattern:

- observation-first
- preserve state
- avoid unsupported repair
- reject irreversible action when visible evidence is insufficient
- `should_reject = true` on `e05`, `e06`, and `e08`

GPT’s behavior is useful as a cautious-admission baseline. It avoids unsupported concretization, but may under-act when the benchmark expects a concrete recovery proposal.

### DeepSeek Expert

DeepSeek expert produced more structured and technical repair narratives than DeepSeek instant.

Observed pattern:

- more coherent causal-repair stories
- concrete machine and job references such as `M2`, `J3`, and `J4`
- repair and rescheduling strategies such as right-shift, Johnson's rule, SPT fallback, and targeted repair
- generally active intervention rather than refusal

However, many concrete details are not visible in the public prompt. DeepSeek expert is therefore operationally richer, but still sometimes unsupported.

Summary:

DeepSeek expert is better than DeepSeek instant for Tier-6 proposal quality in this pilot because its proposals are more coherent and structured. It is not perfectly grounded; it still over-infers hidden state.

### DeepSeek Instant

DeepSeek instant was expected to be more cautious, but the pilot showed a different pattern.

Observed pattern:

- high variance
- sometimes observation-first
- sometimes very concrete and unsupported
- frequent invented operational details such as machine names, job IDs, timing values, sensor readings, scrap-rate estimates, and bottleneck claims

Examples of unsupported instant-mode details include:

- `C1`, temperature `+5°C`, vibration spikes, worn bearing, scrap rate `30% -> 5%`
- `M1/J4 op3 at t=12`, `J2 op2 from t=8 to t=14`, makespan `24`
- `M1` mean time between failures of `8 hours`
- `J7/J12` delayed by `1.5 hours`
- `M3` as a prior bottleneck

Conclusion:

DeepSeek instant appears inferior to DeepSeek expert on this task. It is faster and sometimes observation-oriented, but it is less controlled and more erratic. Expert mode is more coherent, even though it also needs Mnemosyne admission to guard against unsupported concretization.

## Cross-Model Summary

| Model / Mode | Main policy style | Strength | Weakness |
|---|---|---|---|
| Claude | Active local repair | Good repair structure | Low rejection; may act despite sparse evidence |
| GPT | Conservative observation / rejection | Best epistemic caution | May under-act |
| DeepSeek expert | Structured technical repair | More coherent than instant | Unsupported concretization |
| DeepSeek instant | Fast high-variance proposals | Sometimes useful observation steps | Most erratic; many invented specifics |

## Scientific Value

This segment is valuable because it shows that live LLM proposal behavior differs substantially across model families and inference modes under the same Tier-6 public prompt pack.

The main finding is not only model-to-model variation. It is also mode-sensitive behavior:

- DeepSeek expert and DeepSeek instant produce different recovery policies under the same task.
- Expert mode is not merely longer; it changes the proposal structure.
- Instant mode is not necessarily safer; it may be more erratic and more numerically inventive.
- GPT is the strongest epistemic-caution baseline.
- Claude is the strongest active-repair baseline.

## Claim Boundary

Permitted claim:

R83.5a demonstrates manually injected live-LLM proposal behavior under a fixed REALM Tier-6 prompt pack, with hidden labels withheld and with model responses validated for parseability and episode alignment.

Not permitted:

- This does not yet demonstrate full Mnemosyne kernel-scored recovery.
- This does not yet demonstrate API-automated LLM behavior.
- This does not yet demonstrate full CTL-domain StateView realization.
- This does not yet provide confirmatory Chapter 6 hypothesis evidence.
- This does not prove AGI, wisdom, or autonomous scientific reasoning.

## Next Step: R83.5b

R83.5b should import Claude, GPT, DeepSeek expert, and DeepSeek instant response packs into the Mnemosyne kernel-admission trace path and produce a comparison report.

The comparison should separate:

- proposal parseability
- episode alignment
- admission posture
- `should_reject` behavior
- unsupported concrete claims
- active repair vs observation-first policy
- cross-episode consistency
- kernel admission outcome
- REALM scorer output

Generated nondeterministic `events.jsonl` should not be committed unless determinized.
