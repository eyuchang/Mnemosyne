# R7.1 Recovery Store Boundary Inspection

## Summary

- Inspected files: 33
- Recovery-related files: 28
- Coupling sites: 101
- Decision: `ready_for_store_protocol_refactor`

## R7.1 Purpose

R7 begins by identifying recovery, audit, proposal, admission, and lineage paths that must be placed behind durable store protocols before adding PostgreSQL or production runtime execution.

R7.1 does not claim Postgres support, distributed storage, Kubernetes deployment, Temporal execution, or production-runtime recovery.

## Recovery-Related Files

- `mnemosyne/api/__init__.py`
- `mnemosyne/api/audit.py`
- `mnemosyne/api/commitments.py`
- `mnemosyne/api/proposal_packages.py`
- `mnemosyne/api/recovery.py`
- `mnemosyne/api/recovery_admission.py`
- `mnemosyne/api/recovery_events.py`
- `mnemosyne/api/recovery_replay.py`
- `mnemosyne/api/reports.py`
- `mnemosyne/benchmarks/jssp_disruption_commitments.py`
- `mnemosyne/benchmarks/jssp_disruptions.py`
- `mnemosyne/benchmarks/jssp_recovery_proposals.py`
- `mnemosyne/benchmarks/jssp_repair_admission.py`
- `mnemosyne/benchmarks/jssp_schedule_admission.py`
- `mnemosyne/core/store_capabilities.py`
- `mnemosyne/runtime/admission.py`
- `mnemosyne/runtime/command_handler.py`
- `mnemosyne/runtime/commands.py`
- `mnemosyne/runtime/demo.py`
- `mnemosyne/runtime/kernel_admission.py`
- `mnemosyne/runtime/models.py`
- `mnemosyne/runtime/persistence.py`
- `mnemosyne/runtime/proposals.py`
- `mnemosyne/runtime/r3_runner.py`
- `mnemosyne/runtime/r4_kernel_admission_demo.py`
- `mnemosyne/runtime/r4_recovery_demo.py`
- `mnemosyne/runtime/session.py`
- `mnemosyne/runtime/sqlite_repository.py`

## Store Coupling Sites

### `mnemosyne/api/audit.py`

- L17: `sqlite` — `from mnemosyne.core.commitments.store_index import ctl_record_from_sqlite_row`
- L205: `execute(` — `rows = store.conn.execute(`
- L207: `SELECT ` — `SELECT *`
- L215: `sqlite` — `return [ctl_record_from_sqlite_row(row) for row in rows]`

### `mnemosyne/api/recovery.py`

- L120: `commit(` — `execution = await executor.plan_validate_and_commit(`

### `mnemosyne/core/store_capabilities.py`

- L7: `sqlite` — `STORE_SCHEMA_ID = "mnemosyne.store.sqlite"`

### `mnemosyne/runtime/kernel_admission.py`

- L6: `sqlite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L6: `SQLite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L35: `commit(` — `def commit(self, request: KernelCommitRequest) -> KernelCommitResult:`
- L55: `SQLite` — `def __init__(self, repo: SQLiteRuntimeRepository, committer: KernelCommitter):`
- L59: `commit(` — `def reject_before_commit(`
- L135: `commit(` — `kernel_result = self.committer.commit(request)`

### `mnemosyne/runtime/persistence.py`

- L3: `sqlite` — `import sqlite3`
- L3: `sqlite3` — `import sqlite3`
- L162: `SQLite` — `"""SQLite persistence boundary for R4 runtime metadata.`
- L171: `sqlite` — `def connect(self) -> sqlite3.Connection:`
- L171: `sqlite3` — `def connect(self) -> sqlite3.Connection:`
- L175: `sqlite` — `conn = sqlite3.connect(str(self.db_path))`
- L175: `sqlite3` — `conn = sqlite3.connect(str(self.db_path))`
- L176: `sqlite` — `conn.row_factory = sqlite3.Row`
- L176: `sqlite3` — `conn.row_factory = sqlite3.Row`
- L177: `execute(` — `conn.execute("PRAGMA foreign_keys = ON")`
- L183: `commit(` — `conn.commit()`
- L187: `execute(` — `rows = conn.execute(`
- L188: `sqlite` — `"SELECT name FROM sqlite_master WHERE type = 'table'"`
- L188: `SELECT ` — `"SELECT name FROM sqlite_master WHERE type = 'table'"`

### `mnemosyne/runtime/r4_kernel_admission_demo.py`

- L13: `sqlite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L13: `SQLite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L28: `commit(` — `def commit(self, request: KernelCommitRequest) -> KernelCommitResult:`
- L33: `SQLite` — `def seed_base(repo: SQLiteRuntimeRepository) -> dict[str, str]:`
- L87: `SQLite` — `def submit_case(repo: SQLiteRuntimeRepository, ids: dict[str, str], case_id: str) -> str:`
- L160: `sqlite` — `db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "kernel_admission_001.sqlite3"`
- L160: `sqlite3` — `db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "kernel_admission_001.sqlite3"`
- L164: `SQLite` — `repo = SQLiteRuntimeRepository(db_path)`
- L222: `commit(` — `adapter.reject_before_commit(`
- L307: `sqlite` — `if db_path.name == "kernel_admission_001.sqlite3" and db_path.exists():`
- L307: `sqlite3` — `if db_path.name == "kernel_admission_001.sqlite3" and db_path.exists():`

### `mnemosyne/runtime/r4_recovery_demo.py`

- L7: `sqlite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L7: `SQLite` — `from mnemosyne.runtime.sqlite_repository import SQLiteRuntimeRepository`
- L17: `SQLite` — `def seed_runtime(repo: SQLiteRuntimeRepository) -> dict[str, str]:`
- L112: `SQLite` — `def snapshot(repo: SQLiteRuntimeRepository, ids: dict[str, str]) -> dict[str, Any]:`
- L199: `sqlite` — `db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "runtime_recovery_001.sqlite3"`
- L199: `sqlite3` — `db_path = Path(db_path) if db_path is not None else RESULTS_DIR / "runtime_recovery_001.sqlite3"`
- L204: `SQLite` — `repo1 = SQLiteRuntimeRepository(db_path)`
- L209: `SQLite` — `# the same durable SQLite database.`
- L210: `SQLite` — `repo2 = SQLiteRuntimeRepository(db_path)`

### `mnemosyne/runtime/sqlite_repository.py`

- L4: `sqlite` — `import sqlite3`
- L4: `sqlite3` — `import sqlite3`
- L22: `sqlite` — `def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:`
- L22: `sqlite3` — `def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:`
- L37: `SQLite` — `class SQLiteRuntimeRepository:`
- L49: `sqlite` — `def connect(self) -> sqlite3.Connection:`
- L49: `sqlite3` — `def connect(self) -> sqlite3.Connection:`
- L63: `execute(` — `conn.execute(`
- L65: `INSERT ` — `INSERT INTO runtime_workflows (`
- L82: `execute(` — `row = conn.execute(`
- L83: `SELECT ` — `"SELECT * FROM runtime_workflows WHERE workflow_id = ?",`
- L101: `execute(` — `conn.execute(`
- L103: `INSERT ` — `INSERT INTO runtime_workflow_bindings (`
- L123: `execute(` — `row = conn.execute(`
- L124: `SELECT ` — `"SELECT * FROM runtime_workflow_bindings WHERE binding_id = ?",`
- L139: `execute(` — `conn.execute(`
- L141: `INSERT ` — `INSERT INTO runtime_agents (`
- L157: `execute(` — `row = conn.execute(`
- L158: `SELECT ` — `"SELECT * FROM runtime_agents WHERE agent_id = ?",`
- L178: `execute(` — `conn.execute(`
- L180: `INSERT ` — `INSERT INTO runtime_agent_bindings (`
- L202: `execute(` — `row = conn.execute(`
- L203: `SELECT ` — `"SELECT * FROM runtime_agent_bindings WHERE agent_binding_id = ?",`
- L225: `execute(` — `conn.execute(`
- L227: `INSERT ` — `INSERT INTO runtime_proposals (`
- L263: `execute(` — `row = conn.execute(`
- L264: `SELECT ` — `"SELECT * FROM runtime_proposals WHERE proposal_id = ?",`
- L271: `execute(` — `rows = conn.execute(`
- L273: `SELECT ` — `SELECT * FROM runtime_proposals`
- L283: `execute(` — `rows = conn.execute(`
- L285: `SELECT ` — `SELECT * FROM runtime_proposals`
- L316: `execute(` — `conn.execute(`
- L318: `INSERT ` — `INSERT INTO runtime_admission_decisions (`
- L341: `execute(` — `conn.execute(`
- L343: `UPDATE ` — `UPDATE runtime_proposals`
- L371: `execute(` — `row = conn.execute(`
- L372: `SELECT ` — `"SELECT * FROM runtime_admission_decisions WHERE decision_id = ?",`
- L379: `execute(` — `row = conn.execute(`
- L381: `SELECT ` — `SELECT * FROM runtime_admission_decisions`
- L417: `sqlite` — `conn: sqlite3.Connection,`
- L417: `sqlite3` — `conn: sqlite3.Connection,`
- L431: `execute(` — `conn.execute(`
- L433: `INSERT ` — `INSERT INTO runtime_trace_events (`
- L460: `SELECT ` — `query = "SELECT rowid AS _rowid, * FROM runtime_trace_events"`
- L478: `execute(` — `rows = conn.execute(query, params).fetchall()`
- L484: `execute(` — `proposal_count = conn.execute(`
- L485: `SELECT ` — `"SELECT COUNT(*) AS n FROM runtime_proposals"`
- L487: `execute(` — `decision_count = conn.execute(`
- L488: `SELECT ` — `"SELECT COUNT(*) AS n FROM runtime_admission_decisions"`
- L490: `execute(` — `accepted_count = conn.execute(`
- L491: `SELECT ` — `"SELECT COUNT(*) AS n FROM runtime_admission_decisions WHERE decision = 'accepted'"`
- L493: `execute(` — `rejected_count = conn.execute(`
- L494: `SELECT ` — `"SELECT COUNT(*) AS n FROM runtime_admission_decisions WHERE decision = 'rejected'"`
- L496: `execute(` — `trace_event_count = conn.execute(`
- L497: `SELECT ` — `"SELECT COUNT(*) AS n FROM runtime_trace_events"`

## Protocol Mentions

- `mnemosyne/runtime/kernel_admission.py`: Protocol

## Recommended R7.1 Refactor Targets

- Define an explicit RecoveryStore protocol for active commitments, proposal packages, recovery lineage, and recovery events.
- Keep SQLiteStore as the first protocol-conformance implementation.
- Move direct audit/recovery persistence assumptions behind protocol methods before adding PostgreSQL.
- Add fail-closed tests for missing recovery store capabilities.
- Add a durable append-only recovery event log only after the protocol boundary is explicit.

## Claim Boundary

- inspection_only: True
- store_protocol_refactor_claimed: False
- postgres_claimed: False
- kubernetes_claimed: False
- temporal_claimed: False
- production_runtime_claimed: False

