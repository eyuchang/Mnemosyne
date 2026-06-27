# REALM JSSP Dynamic Disruption Contracts Report

## Summary

- Case count: 2
- Existing substrate ready: 1
- Requires extension: 1

## Case Readiness

| Case | Readiness | Machine breakdown | Material unavailable | Full recovery claimed |
|---|---|---:|---:|---:|
| J2 | `ready_for_existing_machine_breakdown_recovery` | True | False | False |
| J4 | `requires_material_recovery_extension` | False | True | False |

## Actionable Events

### J2

- `j2-stochastic-operation-delay-1`
  - type: `stochastic_operation_delay`
  - substrate: `contract_only`
  - distribution: `Uniform(0, 2)`
  - revealed at: `operation_start`
- `j2-machine-breakdown-2`
  - type: `machine_breakdown`
  - substrate: `supported`
  - machine: `MachineA`
  - unavailable: 4 to 6

### J4

- `j4-stochastic-operation-delay-1`
  - type: `stochastic_operation_delay`
  - substrate: `contract_only`
  - distribution: `Uniform(0, 3)`
- `j4-material-unavailability-2`
  - type: `material_unavailability`
  - substrate: `requires_extension`
  - materials examples: `['C-X', 'F']`

## Decision

- J2 can proceed to existing machine-breakdown recovery binding.
- J4 must not be presented as fully recoverable yet.
- J4 needs material/resource recovery extension before an honest full-recovery claim.
- R6.8 should keep recovery claims benchmark-local and contract-scoped.

