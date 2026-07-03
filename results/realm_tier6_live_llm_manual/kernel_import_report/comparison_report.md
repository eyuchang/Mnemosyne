# R83.5b REALM Tier-6 Live LLM Kernel-Import Comparison Report

## Claim Boundary

Deterministic live-pack comparison/import report only. Not API automation, not full CTL-domain StateView realization, and not confirmatory Chapter 6 evidence.

## Pilot

- Sequence: `T6-7e17ef0cc5f3`
- Config: `E7`
- Condition label: `full_crt_stack`

## Pack Summary

| Pack | Responses | should_reject=true | Mean confidence | Policy counts | Unsupported specificity total | Admission recommendations |
|---|---:|---:|---:|---|---:|---|
| claude | 10 | 0 | 0.606 | {'mixed': 10} | 11 | {'admit_parseable_proposal': 10} |
| gpt | 10 | 3 | 0.689 | {'observation_first': 10} | 10 | {'admit_parseable_proposal': 7, 'model_requests_rejection': 3} |
| deepseek_expert | 10 | 0 | 0.759 | {'observation_first': 3, 'mixed': 6, 'active_repair': 1} | 52 | {'admit_parseable_proposal': 5, 'admit_with_grounding_flags': 4, 'review_high_unsupported_specificity': 1} |
| deepseek_instant | 10 | 0 | 0.715 | {'mixed': 7, 'active_repair': 2, 'observation_first': 1} | 46 | {'review_high_unsupported_specificity': 2, 'admit_parseable_proposal': 7, 'admit_with_grounding_flags': 1} |

## Per-Episode Summary

### claude

| Episode | Reject? | Confidence | Policy | Unsupported count | Recommendation | Summary |
|---:|---|---:|---|---:|---|---|
| 1 | False | 0.55 | mixed | 0 | admit_parseable_proposal | Verify breakdown state, then repair the existing schedule via minimal right-shift with optional machine reassignment ... |
| 2 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Reactive partial reschedule for the J4 breakdown instance: freeze operations already completed or in-process on unaff... |
| 3 | False | 0.62 | mixed | 2 | admit_parseable_proposal | Affected-operations rescheduling (right-shift + local re-sequencing) for the J4 jobshop breakdown: freeze all operati... |
| 4 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Localized right-shift repair of the broken machine's queue with optional migration of feasible operations, minimal di... |
| 5 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Apply an affected-operations rescheduling (AOR) repair for the J4 breakdown instance: freeze all operations completed... |
| 6 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Affected-operations local reschedule after breakdown: freeze failed machine, reroute or right-shift only blocked oper... |
| 7 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Treat episode 7 as a machine-breakdown disruption on the J4 instance: freeze the pre-breakdown schedule prefix, mark ... |
| 8 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Verify the breakdown signal against a fresh state observation, then apply a minimal right-shift repair with local rea... |
| 9 | False | 0.55 | mixed | 1 | admit_parseable_proposal | Affected-operations right-shift repair on the broken machine with one availability observation before committing, pre... |
| 10 | False | 0.62 | mixed | 2 | admit_parseable_proposal | Reactive right-shift repair for the J4 breakdown: freeze completed/in-progress operations, reroute or delay only oper... |

### gpt

| Episode | Reject? | Confidence | Policy | Unsupported count | Recommendation | Summary |
|---:|---|---:|---|---:|---|---|
| 1 | False | 0.74 | observation_first | 1 | admit_parseable_proposal | Start with evidence-preserving inspection only; no repair or schedule mutation yet. |
| 2 | False | 0.64 | observation_first | 1 | admit_parseable_proposal | Continue with conservative observation/preservation rather than speculative repair. |
| 3 | False | 0.55 | observation_first | 1 | admit_parseable_proposal | Preserve state and validate; do not repair without visible violation evidence. |
| 4 | False | 0.62 | observation_first | 1 | admit_parseable_proposal | Use a conservative audit-first recovery step and only apply a minimal local job-shop repair if directly supported by ... |
| 5 | True | 0.74 | observation_first | 1 | model_requests_rejection | Do not commit a concrete repair from the visible information; reject irreversible action and preserve state until act... |
| 6 | True | 0.68 | observation_first | 1 | model_requests_rejection | Conservative diagnostic-first recovery: preserve all visible facts, reject unsupported repair, and re-derive the job-... |
| 7 | False | 0.62 | observation_first | 1 | admit_parseable_proposal | Do not reject yet; preserve evidence and perform a fresh constraint/schedule validation checkpoint before any repair. |
| 8 | True | 0.86 | observation_first | 1 | model_requests_rejection | Insufficient visible state for a concrete job-shop repair; recommend observation-only rejection of any unsupported mu... |
| 9 | False | 0.72 | observation_first | 1 | admit_parseable_proposal | Conservative no-op/observation step: preserve state, reject unsupported repairs, and wait for visible evidence. |
| 10 | False | 0.72 | observation_first | 1 | admit_parseable_proposal | Continue conservatively; preserve all visible metadata and prior prompt-emission history; do not perform unsupported ... |

### deepseek_expert

| Episode | Reject? | Confidence | Policy | Unsupported count | Recommendation | Summary |
|---:|---|---:|---|---:|---|---|
| 1 | False | 0.85 | observation_first | 1 | admit_parseable_proposal | Gather initial system state observation before acting |
| 2 | False | 0.78 | mixed | 3 | admit_parseable_proposal | Immediate M2 repair with right-shift rescheduling prioritizing non-critical-path operations |
| 3 | False | 0.78 | mixed | 6 | admit_with_grounding_flags | Run spindle health diagnostic on Machine-2 before committing to full production schedule |
| 4 | False | 0.85 | mixed | 6 | admit_with_grounding_flags | Inspect M2, reroute its jobs, and preserve diagnostic data. |
| 5 | False | 0.65 | mixed | 9 | admit_with_grounding_flags | Observe M2 reliability for 20 units, then apply Johnson's rule if stable; fall back to SPT dispatch if breakdowns con... |
| 6 | False | 0.78 | active_repair | 9 | admit_with_grounding_flags | Repair M2 immediately and reschedule downstream operations to mitigate breakdown impact on J3/J4. |
| 7 | False | 0.7 | mixed | 0 | admit_parseable_proposal | Conduct full system state observation before intervening |
| 8 | False | 0.7 | observation_first | 0 | admit_parseable_proposal | Observe system state and prepare a conditional recovery plan for the most critical job in case of machine anomaly. |
| 9 | False | 0.78 | observation_first | 14 | review_high_unsupported_specificity | Apply targeted repair R to machine M2 based on observed intermittent failure signature, preserving diagnostic evidenc... |
| 10 | False | 0.72 | mixed | 4 | admit_parseable_proposal | Defer M2 repair; continue J4 with active monitoring and plan inspection after job end. |

### deepseek_instant

| Episode | Reject? | Confidence | Policy | Unsupported count | Recommendation | Summary |
|---:|---|---:|---|---:|---|---|
| 1 | False | 0.72 | mixed | 16 | review_high_unsupported_specificity | Conduct emergent maintenance on C1 based on sensor history, pause non-critical jobs, and restart J4 only after cleara... |
| 2 | False | 0.78 | mixed | 0 | admit_parseable_proposal | Observe current machine states and job queues; re-sequence only operations impacted by the breakdown, preserving comp... |
| 3 | False | 0.72 | mixed | 1 | admit_parseable_proposal | Halt and restart with enhanced CRT diagnostics to resolve invisible state uncertainty. |
| 4 | False | 0.62 | active_repair | 3 | admit_parseable_proposal | Reset schedule and re-sequence remaining operations with SPT rule and due-date priority. |
| 5 | False | 0.72 | observation_first | 0 | admit_parseable_proposal | Run a full resource-deadlock scan, then release the least critical blocked job to restore flow. |
| 6 | False | 0.85 | mixed | 0 | admit_parseable_proposal | Pause and observe to fully characterize the breakdown before acting, reducing future missteps. |
| 7 | False | 0.68 | active_repair | 17 | review_high_unsupported_specificity | Shift J4, op3 from M1 start t=8 to M1 start t=12, preserving other assignments and precedence. |
| 8 | False | 0.62 | mixed | 1 | admit_parseable_proposal | Execute full maintenance release on all machines to counter potential CRT-stack-induced wear, sacrificing short-term ... |
| 9 | False | 0.72 | mixed | 6 | admit_with_grounding_flags | Insert one extra maintenance pause on M1 before the most congested period, and re-sequence the two largest remaining ... |
| 10 | False | 0.72 | mixed | 2 | admit_parseable_proposal | Proceed with a state-gathering observation of machine loads and queues, focusing on bottleneck machine M3, to inform ... |

## Interpretation

- Claude is expected to appear as an active local-repair planner.
- GPT is expected to appear as the most cautious observation/rejection baseline.
- DeepSeek expert is expected to be more structured than DeepSeek instant, but still prone to unsupported concretization.
- DeepSeek instant is expected to be higher variance and less controlled than expert mode.

The report is deterministic and suitable for review. It does not commit nondeterministic `events.jsonl` traces.
