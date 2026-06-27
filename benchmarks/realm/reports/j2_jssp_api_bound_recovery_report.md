# REALM J2 API-Bound JSSP Recovery Report

## Summary

- Case: J2
- Schedule case id: `realm-j2`
- Operation count: 9
- Machine unavailable: `MachineA`
- Unavailable window: 4 to 6
- Registered commitments: 9
- Fired commitments: 2
- Repair candidates: 2
- Repair admission ok: True
- Finalization ok: True
- Admitted commitments: 2
- Live commitments: 7
- Unresolved after finalization: 7

## API Sequence

- `admit_baseline_schedule`
- `register_schedule_commitments`
- `signal_machine_breakdown`
- `emit_recovery_proposals_for_disruption`
- `admit_and_finalize_repair_candidates_from_proposal_batch`
- `audit_active_commitments`
- `audit_recovery_lineage`
- `list_unresolved_commitments`

## Affected Operations

- `Job2:O1`
- `Job3:O2`

## Repair Candidates

| RID | Entity | Start | End |
|---|---|---:|---:|
| `rid:jssp:realm-j2:repair-candidate:Job2-O1` | `jssp:realm-j2:operation:Job2:O1` | 6 | 8 |
| `rid:jssp:realm-j2:repair-candidate:Job3-O2` | `jssp:realm-j2:operation:Job3:O2` | 8 | 9 |

## Claims

- api_bound_recovery_claimed: True
- active_commitment_memory_claimed: True
- admission_boundary_claimed: True
- audit_lineage_claimed: True
- benchmark_local_recovery_claimed: True
- global_schedule_feasibility_after_api_admission_claimed: False
- durable_logs_claimed: False
- production_runtime_claimed: False
- j4_full_recovery_claimed: False

## Limitations

- This binds REALM J2 to the active commitment, proposal, admission, and audit APIs.
- It does not claim production-runtime durable recovery.
- It does not claim J4 material/resource recovery.
- The current JSSP repair-admission API mutates selected disrupted operation StateViews; full downstream propagation remains future work.

