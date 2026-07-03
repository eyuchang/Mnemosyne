# R83: REALM-Bench Tier 6 Kernel Adapter

## Purpose

R83 adds a kernel-admission-backed Mnemosyne adapter for REALM-Bench Tier 6.

R80 validated deterministic trace formatting.  
R82 validated runtime proposal/admission trace export.  
R83 validates the next authority layer: `KernelAdmissionAdapter`.

## What R83 uses

R83 uses:

- `SQLiteRuntimeRepository`
- `KernelAdmissionAdapter`
- `KernelCommitRequest`
- `KernelCommitResult`
- `RecoveryEvent`
- `SQLiteStore.append_recovery_event`
- `SQLiteStore.get_state_view`

Accepted events pass through:

```text
KernelAdmissionAdapter.accept_via_kernel(...)
```

Rejected or blocked events pass through:

```text
KernelAdmissionAdapter.reject_before_commit(...)
```

## Status

This is kernel-admission adapter validation.

It is not yet:

- a live LLM run
- a full production CTL-domain commit run
- a final ATP/StateView/CTL confirmatory run
- confirmatory Chapter 6 evidence

## Pipeline

```text
REALM Tier-6 sequence
-> SQLiteRuntimeRepository proposal
-> KernelAdmissionAdapter accept/reject
-> controlled KernelCommitResult
-> durable RecoveryEvent append
-> StateView API snapshot
-> REALM-compatible events.jsonl
-> REALM Tier-6 scorer
```

## Configurations

Current kernel-backed configurations:

- E0: engine only
- E2: +R causal audit
- E3: +T temporal accountability
- E7: +C+R+T full stack

## Outputs

The kernel adapter writes:

```text
results/realm_tier6_mnemosyne_kernel/
  mnemosyne_tier6_E0_kernel_adapter_v0/
  mnemosyne_tier6_E2_kernel_adapter_v0/
  mnemosyne_tier6_E3_kernel_adapter_v0/
  mnemosyne_tier6_E7_kernel_adapter_v0/
```

Each run directory contains:

```text
manifest.json
events.jsonl
summary.json
summary.csv
report.md
```

## Validation

Set:

```bash
export REALM_BENCH_ROOT=/Users/edward.chang/REALM-Bench
```

Run:

```bash
python -m pytest -q tests/benchmarks/test_tier6_mnemosyne_kernel_adapter.py
python benchmarks/realm/tier6_mnemosyne_kernel_adapter.py
```

## Expected pattern

- E0: high repeated_failure_rate, low horizon_reward
- E2: lower repeated_failure_rate than E0
- E3: higher horizon_reward than E0 but recurrence may remain high
- E7: lowest repeated_failure_rate, highest grounded_admission_rate
- all configurations: safety_passed = true

## Claim boundary

R83 validates kernel-admission trace compatibility with REALM Tier 6.

It does not yet validate live LLM behavior, full production CTL-domain commits,
or confirmatory Chapter 6 hypotheses.
