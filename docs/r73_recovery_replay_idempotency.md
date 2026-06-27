# R7.3 Recovery Replay and Idempotency

R7.3 reconstructs deterministic recovery state from durable recovery events.

## Added surface

- `replay_recovery_events`
- `RecoveryReplayState`
- `RecoveryReplayCheckpoint`
- `replay_recovery_events_from_store`
- `recovery_replay_api_result_to_dict`
- committed R7.3 replay report

## Invariants

- Recovery events are replayed deterministically by `recovery_id`, `sequence_no`, and `event_id`.
- Duplicate `event_id` values are ignored during state reconstruction.
- Duplicate `idempotency_key` values are ignored during state reconstruction.
- Duplicate events remain visible as audit data.
- Replay produces a checkpoint with last sequence number and idempotency keys.

## Claim boundary

R7.3 claims deterministic replay and idempotent duplicate tolerance over the durable recovery event log.

R7.3 does not claim:

- replayed domain CTL mutation after crash,
- PostgreSQL support,
- Kubernetes deployment,
- Temporal execution,
- production-runtime recovery execution.
