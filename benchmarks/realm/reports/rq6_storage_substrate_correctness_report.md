# RQ6 Storage-Substrate Correctness Report

Storage-level uniqueness, idempotency, and transactional projection must reject invalid duplicate attempts without corrupting effective state.

| System | Substrate | Attempts | Committed | Rejected | Invalid commits | State total | Expected total | StateView mismatches | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| unconstrained_log_baseline | memory | 128 | 128 | 0 | 64 | 128 | 64 | 1 | ran |
| sqlite_atp_storage | sqlite | 128 | 64 | 64 | 0 | 64 | 64 | 0 | ran |
| postgres_atp_storage | postgres | 128 | 0 | 0 | 0 | 0 | 64 | 0 | skipped: MNEMOSYNE_POSTGRES_DATABASE_URL not set |

## Claim boundary

This experiment tests storage-substrate correctness for idempotent admission and effective-state projection.
It does not claim learning, regret reduction, or preemptive planning.
PostgreSQL evidence is optional and gated by MNEMOSYNE_POSTGRES_DATABASE_URL so default CI remains PostgreSQL-free.
