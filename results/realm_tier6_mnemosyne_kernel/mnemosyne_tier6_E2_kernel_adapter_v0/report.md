# Mnemosyne REALM-Bench Tier 6 Kernel Adapter Report

Status: kernel-admission adapter validation only.

This implements and validates the Mnemosyne REALM-Bench Tier-6 adapter; pilot and confirmatory runs follow under the registered protocol.

This report validates Mnemosyne's KernelAdmissionAdapter surface as a source for
REALM Tier-6-compatible traces. Accepted events pass through accept_via_kernel;
blocked events pass through reject_before_commit. Durable RecoveryEvent records
and StateView API snapshots are attached as evidence.

It is not a live LLM run and not yet a full production CTL-domain commit run.

## Manifest

- Run ID: mnemosyne_tier6_E2_kernel_adapter_v0
- Config: E2
- Phase: kernel_admission_adapter_validation
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
| Horizon reward mean | 0.3076923076923077 |
| Grounded admission rate | None |
| RFR bracket position | 1.0 |
| Horizon bracket position | 0.3076923076923077 |

## Claim boundary

These outputs validate kernel-admission trace compatibility with REALM Tier 6.
They do not yet validate live LLM behavior, full production CTL commits, or
confirmatory Chapter 6 hypotheses.
