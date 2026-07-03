# R83.5c REALM Tier-6 Live LLM Kernel-Trace Attachment Report

## Claim Boundary

Deterministic kernel-admission trace attachment report only. Does not mutate runtime store, does not emit nondeterministic events.jsonl, and is not confirmatory Chapter 6 evidence.

## Pilot

- Sequence: `T6-7e17ef0cc5f3`
- Config: `E7`
- Condition label: `full_crt_stack`

## Summary

- Records: `40`
- Admitted: `34`
- Rejected before commit: `6`
- Kernel method counts: `{'accept_via_kernel': 29, 'reject_before_commit': 6, 'accept_via_kernel_with_flags': 5}`
- Pack counts: `{'claude': 10, 'gpt': 10, 'deepseek_expert': 10, 'deepseek_instant': 10}`

## Per-Pack Kernel Attachment Summary

| Pack | Records | accept_via_kernel | accept_via_kernel_with_flags | reject_before_commit |
|---|---:|---:|---:|---:|
| claude | 10 | 10 | 0 | 0 |
| gpt | 10 | 7 | 0 | 3 |
| deepseek_expert | 10 | 5 | 4 | 1 |
| deepseek_instant | 10 | 7 | 1 | 2 |

## Per-Episode Records

| Pack | Episode | Method | Admitted | Flags | Policy | Unsupported | Summary |
|---|---:|---|---|---|---|---:|---|
| claude | 1 | accept_via_kernel | True |  | mixed | 0 | Verify breakdown state, then repair the existing schedule via minimal right-shift with optional machine rea... |
| claude | 2 | accept_via_kernel | True |  | mixed | 1 | Reactive partial reschedule for the J4 breakdown instance: freeze operations already completed or in-proces... |
| claude | 3 | accept_via_kernel | True |  | mixed | 2 | Affected-operations rescheduling (right-shift + local re-sequencing) for the J4 jobshop breakdown: freeze a... |
| claude | 4 | accept_via_kernel | True |  | mixed | 1 | Localized right-shift repair of the broken machine's queue with optional migration of feasible operations, ... |
| claude | 5 | accept_via_kernel | True |  | mixed | 1 | Apply an affected-operations rescheduling (AOR) repair for the J4 breakdown instance: freeze all operations... |
| claude | 6 | accept_via_kernel | True |  | mixed | 1 | Affected-operations local reschedule after breakdown: freeze failed machine, reroute or right-shift only bl... |
| claude | 7 | accept_via_kernel | True |  | mixed | 1 | Treat episode 7 as a machine-breakdown disruption on the J4 instance: freeze the pre-breakdown schedule pre... |
| claude | 8 | accept_via_kernel | True |  | mixed | 1 | Verify the breakdown signal against a fresh state observation, then apply a minimal right-shift repair with... |
| claude | 9 | accept_via_kernel | True |  | mixed | 1 | Affected-operations right-shift repair on the broken machine with one availability observation before commi... |
| claude | 10 | accept_via_kernel | True |  | mixed | 2 | Reactive right-shift repair for the J4 breakdown: freeze completed/in-progress operations, reroute or delay... |
| gpt | 1 | accept_via_kernel | True |  | observation_first | 1 | Start with evidence-preserving inspection only; no repair or schedule mutation yet. |
| gpt | 2 | accept_via_kernel | True |  | observation_first | 1 | Continue with conservative observation/preservation rather than speculative repair. |
| gpt | 3 | accept_via_kernel | True |  | observation_first | 1 | Preserve state and validate; do not repair without visible violation evidence. |
| gpt | 4 | accept_via_kernel | True |  | observation_first | 1 | Use a conservative audit-first recovery step and only apply a minimal local job-shop repair if directly sup... |
| gpt | 5 | reject_before_commit | False | model_requested_rejection | observation_first | 1 | Do not commit a concrete repair from the visible information; reject irreversible action and preserve state... |
| gpt | 6 | reject_before_commit | False | model_requested_rejection | observation_first | 1 | Conservative diagnostic-first recovery: preserve all visible facts, reject unsupported repair, and re-deriv... |
| gpt | 7 | accept_via_kernel | True |  | observation_first | 1 | Do not reject yet; preserve evidence and perform a fresh constraint/schedule validation checkpoint before a... |
| gpt | 8 | reject_before_commit | False | model_requested_rejection | observation_first | 1 | Insufficient visible state for a concrete job-shop repair; recommend observation-only rejection of any unsu... |
| gpt | 9 | accept_via_kernel | True |  | observation_first | 1 | Conservative no-op/observation step: preserve state, reject unsupported repairs, and wait for visible evide... |
| gpt | 10 | accept_via_kernel | True |  | observation_first | 1 | Continue conservatively; preserve all visible metadata and prior prompt-emission history; do not perform un... |
| deepseek_expert | 1 | accept_via_kernel | True |  | observation_first | 1 | Gather initial system state observation before acting |
| deepseek_expert | 2 | accept_via_kernel | True |  | mixed | 3 | Immediate M2 repair with right-shift rescheduling prioritizing non-critical-path operations |
| deepseek_expert | 3 | accept_via_kernel_with_flags | True | moderate_unsupported_specificity | mixed | 6 | Run spindle health diagnostic on Machine-2 before committing to full production schedule |
| deepseek_expert | 4 | accept_via_kernel_with_flags | True | moderate_unsupported_specificity | mixed | 6 | Inspect M2, reroute its jobs, and preserve diagnostic data. |
| deepseek_expert | 5 | accept_via_kernel_with_flags | True | moderate_unsupported_specificity | mixed | 9 | Observe M2 reliability for 20 units, then apply Johnson's rule if stable; fall back to SPT dispatch if brea... |
| deepseek_expert | 6 | accept_via_kernel_with_flags | True | moderate_unsupported_specificity | active_repair | 9 | Repair M2 immediately and reschedule downstream operations to mitigate breakdown impact on J3/J4. |
| deepseek_expert | 7 | accept_via_kernel | True |  | mixed | 0 | Conduct full system state observation before intervening |
| deepseek_expert | 8 | accept_via_kernel | True |  | observation_first | 0 | Observe system state and prepare a conditional recovery plan for the most critical job in case of machine a... |
| deepseek_expert | 9 | reject_before_commit | False | high_unsupported_specificity,requires_human_review | observation_first | 14 | Apply targeted repair R to machine M2 based on observed intermittent failure signature, preserving diagnost... |
| deepseek_expert | 10 | accept_via_kernel | True |  | mixed | 4 | Defer M2 repair; continue J4 with active monitoring and plan inspection after job end. |
| deepseek_instant | 1 | reject_before_commit | False | high_unsupported_specificity,requires_human_review | mixed | 16 | Conduct emergent maintenance on C1 based on sensor history, pause non-critical jobs, and restart J4 only af... |
| deepseek_instant | 2 | accept_via_kernel | True |  | mixed | 0 | Observe current machine states and job queues; re-sequence only operations impacted by the breakdown, prese... |
| deepseek_instant | 3 | accept_via_kernel | True |  | mixed | 1 | Halt and restart with enhanced CRT diagnostics to resolve invisible state uncertainty. |
| deepseek_instant | 4 | accept_via_kernel | True |  | active_repair | 3 | Reset schedule and re-sequence remaining operations with SPT rule and due-date priority. |
| deepseek_instant | 5 | accept_via_kernel | True |  | observation_first | 0 | Run a full resource-deadlock scan, then release the least critical blocked job to restore flow. |
| deepseek_instant | 6 | accept_via_kernel | True |  | mixed | 0 | Pause and observe to fully characterize the breakdown before acting, reducing future missteps. |
| deepseek_instant | 7 | reject_before_commit | False | high_unsupported_specificity,requires_human_review | active_repair | 17 | Shift J4, op3 from M1 start t=8 to M1 start t=12, preserving other assignments and precedence. |
| deepseek_instant | 8 | accept_via_kernel | True |  | mixed | 1 | Execute full maintenance release on all machines to counter potential CRT-stack-induced wear, sacrificing s... |
| deepseek_instant | 9 | accept_via_kernel_with_flags | True | moderate_unsupported_specificity | mixed | 6 | Insert one extra maintenance pause on M1 before the most congested period, and re-sequence the two largest ... |
| deepseek_instant | 10 | accept_via_kernel | True |  | mixed | 2 | Proceed with a state-gathering observation of machine loads and queues, focusing on bottleneck machine M3, ... |

## Interpretation

This report attaches each deterministic live-LLM response summary to a stable kernel-admission-style record using deterministic UUIDv5 IDs and synthetic deterministic timestamps.

The artifact is suitable for review and regression testing. It deliberately does not emit nondeterministic raw trace files.
