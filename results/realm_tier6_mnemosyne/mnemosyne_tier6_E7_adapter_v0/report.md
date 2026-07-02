# Mnemosyne REALM-Bench Tier 6 Adapter Report

Status: deterministic adapter validation only.

This implements and validates the Mnemosyne REALM-Bench Tier-6 adapter; pilot and confirmatory runs follow under the registered protocol.

This report validates Mnemosyne's ability to emit REALM Tier-6-compatible
traces. It is not a live LLM run and must not be used as evidence for H1-H5.

## Manifest

- Run ID: mnemosyne_tier6_E7_adapter_v0
- Config: E7
- Phase: deterministic_adapter_validation
- Claim status: not_chapter_result
- Sequences: 15
- Episodes: 150
- Events: 78
- Families: jobshop_breakdown, ride_or_routing_disruption, wedding_recovery

## Scorer summary

| Metric | Value |
|---|---:|
| Safety passed | True |
| Invalid commits | 0 |
| Evidence-destroying repairs | 0 |
| Orphaned dependents | 0 |
| Repeated failure rate | 0.0 |
| Control repeated failure rate | 0.0 |
| Observed TTC count | 12 |
| Censored TTC count | 66 |
| Horizon reward mean | 0.8423076923076923 |
| Grounded admission rate | 1.0 |
| RFR bracket position | 1.0 |
| Horizon bracket position | 0.8423076923076923 |

## Claim boundary

The deterministic adapter constructs expected traces by design. These outputs
validate adapter compatibility with REALM Tier 6 only. Pilot and confirmatory
runs are required before Chapter 6 can make quantitative claims about
cross-episode learning.
