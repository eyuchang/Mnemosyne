-- Phase 0 Postgres schema draft. Alembic migrations should be generated from this contract.
-- Global log_position is audit/identity only. Hot-path correctness is scoped by tenant/workflow/eid/fsm/dependency DAG.

CREATE TABLE IF NOT EXISTS commands (
  command_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  command_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  idempotency_key TEXT NOT NULL,
  workflow_id TEXT,
  submitted_at TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS event_log (
  log_position BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  source TEXT NOT NULL,
  event_type TEXT NOT NULL,
  entity_refs JSONB NOT NULL,
  payload JSONB NOT NULL,
  workflow_id TEXT,
  binding_id TEXT,
  schema_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_inbox (
  inbox_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  source TEXT NOT NULL,
  dedupe_key TEXT NOT NULL,
  workflow_id TEXT,
  binding_id TEXT,
  payload JSONB NOT NULL,
  schema_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  processed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  UNIQUE (tenant_id, source, dedupe_key)
);

CREATE TABLE IF NOT EXISTS ctl_records (
  log_position BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rid TEXT NOT NULL,
  op_id TEXT,
  tenant_id TEXT NOT NULL,
  tx_group_id TEXT NOT NULL,
  workflow_id TEXT,
  binding_id TEXT,
  eid TEXT NOT NULL,
  fsm TEXT NOT NULL,
  version INTEGER NOT NULL,
  state_before TEXT NOT NULL,
  state_after TEXT NOT NULL,
  action_type TEXT NOT NULL,
  triggers JSONB NOT NULL,
  dependencies JSONB NOT NULL,
  metadata JSONB NOT NULL,
  extension JSONB NOT NULL,
  app_id TEXT NOT NULL,
  app_version TEXT NOT NULL,
  schema_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  fsm_version TEXT NOT NULL,
  policy_id TEXT,
  policy_version TEXT,
  validator_id TEXT,
  validator_version TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  local_log_position BIGINT NOT NULL,
  UNIQUE (tenant_id, rid),
  UNIQUE (tenant_id, op_id),
  UNIQUE (tenant_id, eid, fsm, version),
  UNIQUE (tenant_id, workflow_id, local_log_position)
);

CREATE INDEX IF NOT EXISTS idx_ctl_scope ON ctl_records (tenant_id, workflow_id, eid, fsm);
CREATE INDEX IF NOT EXISTS idx_ctl_tx_group ON ctl_records (tenant_id, tx_group_id);

CREATE TABLE IF NOT EXISTS effective_record_index (
  tenant_id TEXT NOT NULL,
  rid TEXT NOT NULL,
  effective BOOLEAN NOT NULL,
  changed_by_rid TEXT,
  PRIMARY KEY (tenant_id, rid)
);

CREATE TABLE IF NOT EXISTS entity_projection (
  tenant_id TEXT NOT NULL,
  eid TEXT NOT NULL,
  fsm TEXT NOT NULL,
  state TEXT,
  version INTEGER NOT NULL,
  attrs JSONB NOT NULL,
  effective_records JSONB NOT NULL,
  as_of_log_position BIGINT,
  workflow_id TEXT,
  binding_id TEXT,
  PRIMARY KEY (tenant_id, eid, fsm)
);

CREATE TABLE IF NOT EXISTS outbox (
  outbox_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  effect_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  provider_idempotency_key TEXT NOT NULL,
  workflow_id TEXT,
  binding_id TEXT,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, outbox_id),
  UNIQUE (tenant_id, provider, provider_idempotency_key)
);

CREATE TABLE IF NOT EXISTS app_registry (
  app_id TEXT NOT NULL,
  app_version TEXT NOT NULL,
  payload JSONB NOT NULL,
  immutable BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (app_id, app_version)
);

CREATE TABLE IF NOT EXISTS schema_registry (
  schema_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  schema JSONB NOT NULL,
  immutable BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (schema_id, schema_version)
);

CREATE TABLE IF NOT EXISTS fsm_registry (
  fsm_id TEXT NOT NULL,
  fsm_version TEXT NOT NULL,
  fsm JSONB NOT NULL,
  immutable BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (fsm_id, fsm_version)
);

CREATE TABLE IF NOT EXISTS policy_registry (
  policy_id TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  policy JSONB NOT NULL,
  immutable BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (policy_id, policy_version)
);

-- R7.8.1 PostgreSQL recovery-event adapter contract.
CREATE TABLE IF NOT EXISTS store_schema_metadata (
    schema_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    store_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_events (
    event_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    workflow_id TEXT,
    recovery_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    causality_key TEXT,
    payload JSONB NOT NULL,
    schema_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, event_id),
    UNIQUE (tenant_id, idempotency_key),
    UNIQUE (tenant_id, recovery_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_recovery_events_recovery
ON recovery_events (tenant_id, recovery_id, sequence_no);

CREATE INDEX IF NOT EXISTS idx_recovery_events_workflow
ON recovery_events (tenant_id, workflow_id, created_at);
