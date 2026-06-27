# Postgres Store Contract

Phase 0 ships the schema contract only. The async SQLAlchemy/asyncpg implementation lands after the SQLite conformance path is green.

Important rules:

- CTL is the source of truth for committed state.
- Event log is the source of truth for observed causes and non-commit decisions.
- Global `log_position` is identity/audit order, not a correctness bottleneck.
- Correctness is scoped by tenant/workflow/eid/fsm/dependency DAG.
- `entity_projection` and `effective_record_index` are updated synchronously with CTL append.
