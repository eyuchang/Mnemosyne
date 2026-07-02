# R80: REALM-Bench Tier 6 Mnemosyne Adapter

## Purpose

This milestone adds a Mnemosyne-side adapter for REALM-Bench Tier 6:
Cross-Episode Causal Loop.

REALM-Bench owns the benchmark. Mnemosyne is one system submission that emits
Tier-6-compatible traces.

## Current status

The current adapter is deterministic and validates trace compatibility only.
It is not a live LLM run and not evidence for H1-H5.

## Configurations

- E0: engine only
- E2: +R causal audit
- E3: +T temporal accountability
- E7: +C+R+T full stack

## Outputs

The adapter writes one run directory per configuration:

```text
results/realm_tier6_mnemosyne/
  mnemosyne_tier6_E0_adapter_v0/
  mnemosyne_tier6_E2_adapter_v0/
  mnemosyne_tier6_E3_adapter_v0/
  mnemosyne_tier6_E7_adapter_v0/
```

Each directory contains:

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
python -m pytest -q tests/benchmarks/test_tier6_mnemosyne_adapter.py
python benchmarks/realm/tier6_mnemosyne_adapter.py
```

## Claim boundary

The deterministic adapter constructs expected traces by design. These outputs
validate adapter compatibility with REALM Tier 6 only. Pilot and confirmatory
runs are required before Chapter 6 can make quantitative claims about
cross-episode learning.
