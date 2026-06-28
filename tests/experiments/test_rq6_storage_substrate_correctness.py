from __future__ import annotations

import json
import os
import random
import sqlite3
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path


POSTGRES_ENV = "MNEMOSYNE_POSTGRES_DATABASE_URL"


@dataclass(frozen=True)
class StorageAttempt:
    event_id: str
    operation_key: str
    sequence_no: int
    amount: int
    kind: str
    should_commit: bool


def build_attempts() -> tuple[list[StorageAttempt], list[StorageAttempt]]:
    valid: list[StorageAttempt] = []
    invalid: list[StorageAttempt] = []

    for i in range(64):
        valid.append(
            StorageAttempt(
                event_id=f"evt-{i}",
                operation_key=f"op-{i}",
                sequence_no=i + 1,
                amount=1,
                kind="valid_unique_commit",
                should_commit=True,
            )
        )

    for i in range(16):
        invalid.append(
            StorageAttempt(
                event_id=f"evt-dup-op-{i}",
                operation_key=f"op-{i}",
                sequence_no=1000 + i,
                amount=1,
                kind="duplicate_operation_key",
                should_commit=False,
            )
        )

    for i in range(16, 32):
        invalid.append(
            StorageAttempt(
                event_id=f"evt-{i}",
                operation_key=f"op-dup-event-{i}",
                sequence_no=1100 + i,
                amount=1,
                kind="duplicate_event_id",
                should_commit=False,
            )
        )

    for i in range(32, 48):
        invalid.append(
            StorageAttempt(
                event_id=f"evt-dup-seq-{i}",
                operation_key=f"op-dup-seq-{i}",
                sequence_no=i + 1,
                amount=1,
                kind="duplicate_sequence_no",
                should_commit=False,
            )
        )

    for i in range(48, 64):
        invalid.append(
            StorageAttempt(
                event_id=f"evt-invalid-seq-{i}",
                operation_key=f"op-invalid-seq-{i}",
                sequence_no=0,
                amount=1,
                kind="invalid_sequence_no",
                should_commit=False,
            )
        )

    rng = random.Random(79)
    rng.shuffle(valid)
    rng.shuffle(invalid)
    return valid, invalid


def run_unconstrained_log_baseline(valid: list[StorageAttempt], invalid: list[StorageAttempt]) -> dict:
    attempts = valid + invalid
    committed = list(attempts)

    invalid_commits = sum(1 for attempt in committed if not attempt.should_commit)
    ledger_rows = len(committed)
    state_total = sum(attempt.amount for attempt in committed)
    expected_state_total = sum(attempt.amount for attempt in valid)

    return {
        "system": "unconstrained_log_baseline",
        "substrate": "memory",
        "attempts": len(attempts),
        "committed": len(committed),
        "rejected": 0,
        "invalid_commits": invalid_commits,
        "ledger_rows": ledger_rows,
        "state_total": state_total,
        "expected_state_total": expected_state_total,
        "stateview_mismatches": int(state_total != expected_state_total),
        "skipped": False,
        "skip_reason": "",
    }


def sqlite_connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=30.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def init_sqlite(path: str) -> None:
    con = sqlite_connect(path)
    try:
        con.execute(
            """
            CREATE TABLE recovery_events (
                event_id TEXT PRIMARY KEY,
                operation_key TEXT NOT NULL UNIQUE,
                sequence_no INTEGER NOT NULL UNIQUE CHECK (sequence_no >= 1),
                amount INTEGER NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE effective_state (
                state_key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )
    finally:
        con.close()


def apply_sqlite(path: str, attempt: StorageAttempt) -> bool:
    for _ in range(20):
        con = sqlite_connect(path)
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """
                INSERT INTO recovery_events(event_id, operation_key, sequence_no, amount)
                VALUES (?, ?, ?, ?)
                """,
                (attempt.event_id, attempt.operation_key, attempt.sequence_no, attempt.amount),
            )
            con.execute(
                """
                INSERT INTO effective_state(state_key, value)
                VALUES ('total', ?)
                ON CONFLICT(state_key)
                DO UPDATE SET value = effective_state.value + excluded.value
                """,
                (attempt.amount,),
            )
            con.execute("COMMIT")
            return True
        except sqlite3.IntegrityError:
            con.execute("ROLLBACK")
            return False
        except sqlite3.OperationalError:
            try:
                con.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            time.sleep(0.02)
        finally:
            con.close()

    raise RuntimeError("sqlite remained locked after retries")


def summarize_sqlite(path: str, valid: list[StorageAttempt], invalid: list[StorageAttempt]) -> dict:
    con = sqlite_connect(path)
    try:
        ledger_rows = con.execute("SELECT COUNT(*) FROM recovery_events").fetchone()[0]
        state_row = con.execute(
            "SELECT value FROM effective_state WHERE state_key = 'total'"
        ).fetchone()
        state_total = 0 if state_row is None else state_row[0]
    finally:
        con.close()

    expected_state_total = sum(attempt.amount for attempt in valid)

    return {
        "system": "sqlite_atp_storage",
        "substrate": "sqlite",
        "attempts": len(valid) + len(invalid),
        "committed": ledger_rows,
        "rejected": len(valid) + len(invalid) - ledger_rows,
        "invalid_commits": max(0, ledger_rows - len(valid)),
        "ledger_rows": ledger_rows,
        "state_total": state_total,
        "expected_state_total": expected_state_total,
        "stateview_mismatches": int(state_total != expected_state_total),
        "skipped": False,
        "skip_reason": "",
    }


def run_sqlite_storage(valid: list[StorageAttempt], invalid: list[StorageAttempt]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "rq6.sqlite3")
        init_sqlite(path)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda attempt: apply_sqlite(path, attempt), valid))

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda attempt: apply_sqlite(path, attempt), invalid))

        return summarize_sqlite(path, valid, invalid)


def run_postgres_storage(valid: list[StorageAttempt], invalid: list[StorageAttempt]) -> dict:
    url = os.environ.get(POSTGRES_ENV)
    if not url:
        return {
            "system": "postgres_atp_storage",
            "substrate": "postgres",
            "attempts": len(valid) + len(invalid),
            "committed": 0,
            "rejected": 0,
            "invalid_commits": 0,
            "ledger_rows": 0,
            "state_total": 0,
            "expected_state_total": sum(attempt.amount for attempt in valid),
            "stateview_mismatches": 0,
            "skipped": True,
            "skip_reason": f"{POSTGRES_ENV} not set",
        }

    import psycopg

    suffix = uuid.uuid4().hex
    events = f"rq6_events_{suffix}"
    state = f"rq6_state_{suffix}"

    def connect():
        return psycopg.connect(url)

    with connect() as con:
        con.execute(
            f"""
            CREATE TABLE {events} (
                event_id TEXT PRIMARY KEY,
                operation_key TEXT NOT NULL UNIQUE,
                sequence_no INTEGER NOT NULL UNIQUE CHECK (sequence_no >= 1),
                amount INTEGER NOT NULL
            )
            """
        )
        con.execute(
            f"""
            CREATE TABLE {state} (
                state_key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )

    def apply(attempt: StorageAttempt) -> bool:
        try:
            with connect() as con:
                with con.transaction():
                    con.execute(
                        f"""
                        INSERT INTO {events}(event_id, operation_key, sequence_no, amount)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            attempt.event_id,
                            attempt.operation_key,
                            attempt.sequence_no,
                            attempt.amount,
                        ),
                    )
                    con.execute(
                        f"""
                        INSERT INTO {state}(state_key, value)
                        VALUES ('total', %s)
                        ON CONFLICT(state_key)
                        DO UPDATE SET value = {state}.value + EXCLUDED.value
                        """,
                        (attempt.amount,),
                    )
            return True
        except Exception:
            return False

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(apply, valid))

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(apply, invalid))

        with connect() as con:
            ledger_rows = con.execute(f"SELECT COUNT(*) FROM {events}").fetchone()[0]
            state_row = con.execute(
                f"SELECT value FROM {state} WHERE state_key = 'total'"
            ).fetchone()
            state_total = 0 if state_row is None else state_row[0]
    finally:
        with connect() as con:
            con.execute(f"DROP TABLE IF EXISTS {state}")
            con.execute(f"DROP TABLE IF EXISTS {events}")

    expected_state_total = sum(attempt.amount for attempt in valid)

    return {
        "system": "postgres_atp_storage",
        "substrate": "postgres",
        "attempts": len(valid) + len(invalid),
        "committed": ledger_rows,
        "rejected": len(valid) + len(invalid) - ledger_rows,
        "invalid_commits": max(0, ledger_rows - len(valid)),
        "ledger_rows": ledger_rows,
        "state_total": state_total,
        "expected_state_total": expected_state_total,
        "stateview_mismatches": int(state_total != expected_state_total),
        "skipped": False,
        "skip_reason": "",
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ6",
        "name": "Storage-substrate correctness",
        "claim": (
            "Storage-level idempotency, uniqueness, and transactional projection preserve "
            "committed effective state under duplicate, stale, malformed, and concurrent attempts."
        ),
        "success_criteria": [
            "ATP storage invalid_commits = 0",
            "ATP storage stateview_mismatches = 0",
            "Unconstrained baseline invalid_commits > 0",
            "SQLite must run by default",
            "PostgreSQL runs only when MNEMOSYNE_POSTGRES_DATABASE_URL is set",
        ],
        "systems": results,
    }

    (report_dir / "rq6_storage_substrate_correctness_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ6 Storage-Substrate Correctness Report",
        "",
        "Storage-level uniqueness, idempotency, and transactional projection must reject invalid duplicate attempts without corrupting effective state.",
        "",
        "| System | Substrate | Attempts | Committed | Rejected | Invalid commits | State total | Expected total | StateView mismatches | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for result in results:
        status = "skipped: " + result["skip_reason"] if result["skipped"] else "ran"
        lines.append(
            "| {system} | {substrate} | {attempts} | {committed} | {rejected} | "
            "{invalid_commits} | {state_total} | {expected_state_total} | "
            "{stateview_mismatches} | ".format(**result)
            + status
            + " |"
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests storage-substrate correctness for idempotent admission and effective-state projection.",
            "It does not claim learning, regret reduction, or preemptive planning.",
            "PostgreSQL evidence is optional and gated by MNEMOSYNE_POSTGRES_DATABASE_URL so default CI remains PostgreSQL-free.",
            "",
        ]
    )

    (report_dir / "rq6_storage_substrate_correctness_report.md").write_text(
        "\n".join(lines)
    )


def test_rq6_storage_substrate_correctness() -> None:
    valid, invalid = build_attempts()

    results = [
        run_unconstrained_log_baseline(valid, invalid),
        run_sqlite_storage(valid, invalid),
        run_postgres_storage(valid, invalid),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["unconstrained_log_baseline"]["invalid_commits"] > 0
    assert by_system["unconstrained_log_baseline"]["stateview_mismatches"] > 0

    assert by_system["sqlite_atp_storage"]["skipped"] is False
    assert by_system["sqlite_atp_storage"]["committed"] == len(valid)
    assert by_system["sqlite_atp_storage"]["rejected"] == len(invalid)
    assert by_system["sqlite_atp_storage"]["invalid_commits"] == 0
    assert by_system["sqlite_atp_storage"]["stateview_mismatches"] == 0

    if not by_system["postgres_atp_storage"]["skipped"]:
        assert by_system["postgres_atp_storage"]["committed"] == len(valid)
        assert by_system["postgres_atp_storage"]["rejected"] == len(invalid)
        assert by_system["postgres_atp_storage"]["invalid_commits"] == 0
        assert by_system["postgres_atp_storage"]["stateview_mismatches"] == 0

    write_reports(results)
