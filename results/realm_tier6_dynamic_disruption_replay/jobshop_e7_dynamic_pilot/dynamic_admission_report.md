# R98 Dynamic Disruption Admission Replay

## Claim Boundary

R98 is Mnemosyne-side deterministic dynamic admission/replay. It is not an official REALM-Bench score and does not claim final Chapter 6 dynamic closure until R99 scoring is complete.

## Summary

- Events: `40`
- Official REALM score: `False`
- Safety passed: `True`
- Horizon reward proxy mean: `0.925`
- TTC count: `40`
- TTC mean: `0.725`
- TTC min: `0`
- TTC max: `1`

## Admission Decisions

| Decision | Count |
|---|---:|
| admit | 24 |
| reject | 16 |

## Dynamic Outcomes

| Outcome | Count |
|---|---:|
| admitted_repair | 24 |
| rejected_other | 12 |
| safe_rejection | 4 |

## By Proposer Pack

| Pack | Events | Admit | Reject | Observe | Safe rejection |
|---|---:|---:|---:|---:|---:|
| claude | 10 | 9 | 1 | 0 | 0 |
| deepseek_expert | 10 | 5 | 5 | 0 | 3 |
| deepseek_instant | 10 | 5 | 5 | 0 | 1 |
| gpt | 10 | 5 | 5 | 0 | 0 |

## Safety Totals

| Counter | Value |
|---|---:|
| invalid_commit_count | 0 |
| evidence_destroying_repair_count | 0 |
| orphaned_dependent_count | 0 |

## Interpretation

R98 consumes the 40 validated dynamic responses and applies deterministic admission guards. It records admitted repairs, safe rejections, observation requests, safety counters, and time-to-correction proxies. This prepares the R99 handoff to REALM-Bench dynamic Tier-6 scoring.
