# R7.3 Recovery Replay and Idempotency Report

## Summary

- Tenant: `tenant-r73`
- Workflow: `workflow-r73`
- Recovery count: 1
- Replayed event count: 3
- Duplicate event count: 0
- Last sequence number: 3
- Terminal event seen: True
- Duplicate replay tolerance checked: True
- Duplicate replay duplicate count: 2

## Deterministic Replay Order

- `r73-event-1`
- `r73-event-2`
- `r73-event-3`

## Claims

- durable_event_log_replay_claimed: True
- deterministic_replay_order_claimed: True
- idempotent_duplicate_tolerance_claimed: True
- checkpoint_projection_claimed: True
- postgres_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

## Limitations

- R7.3 replays durable recovery events into deterministic recovery state.
- R7.3 does not yet replay domain CTL mutation after crash.
- R7.3 does not claim PostgreSQL, Kubernetes, Temporal, or production-runtime execution.

