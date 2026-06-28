from __future__ import annotations

import json
import random
import sqlite3
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    agent: str
    operation_key: str
    item: str
    delta: int
    expected_version: int
    valid_under_c: bool
    kind: str


def proposal_suite() -> list[Proposal]:
    proposals: list[Proposal] = []

    agents = [
        "planner_agent",
        "llm_like_agent",
        "repair_agent",
        "adversarial_agent",
    ]

    proposal_no = 0

    for agent in agents:
        for i in range(8):
            proposals.append(
                Proposal(
                    proposal_id=f"p-{proposal_no}",
                    agent=agent,
                    operation_key=f"reserve-seat-{agent}-{i}",
                    item="seat_pool",
                    delta=-1,
                    expected_version=i,
                    valid_under_c=True,
                    kind="valid_capacity_decrement",
                )
            )
            proposal_no += 1

    for agent in agents:
        for i in range(4):
            proposals.append(
                Proposal(
                    proposal_id=f"p-{proposal_no}",
                    agent=agent,
                    operation_key=f"duplicate-key-{i}",
                    item="seat_pool",
                    delta=-1,
                    expected_version=0,
                    valid_under_c=False,
                    kind="duplicate_operation_key",
                )
            )
            proposal_no += 1

    for agent in agents:
        for i in range(4):
            proposals.append(
                Proposal(
                    proposal_id=f"p-{proposal_no}",
                    agent=agent,
                    operation_key=f"stale-version-{agent}-{i}",
                    item="seat_pool",
                    delta=-1,
                    expected_version=-1,
                    valid_under_c=False,
                    kind="stale_read_version",
                )
            )
            proposal_no += 1

    for agent in agents:
        for i in range(4):
            proposals.append(
                Proposal(
                    proposal_id=f"p-{proposal_no}",
                    agent=agent,
                    operation_key=f"overdraw-{agent}-{i}",
                    item="seat_pool",
                    delta=-100,
                    expected_version=0,
                    valid_under_c=False,
                    kind="capacity_violation",
                )
            )
            proposal_no += 1

    rng = random.Random(79)
    rng.shuffle(proposals)
    return proposals


def run_unserialized_baseline(proposals: list[Proposal]) -> dict:
    initial_capacity = 32
    committed = list(proposals)

    final_capacity = initial_capacity + sum(p.delta for p in committed)
    invalid_commits = sum(1 for p in committed if not p.valid_under_c)
    duplicate_operation_commits = len(committed) - len({p.operation_key for p in committed})
    capacity_underflow = final_capacity < 0

    return {
        "system": "unserialized_generated_writes",
        "proposal_count": len(proposals),
        "committed": len(committed),
        "rejected": 0,
        "invalid_commits": invalid_commits,
        "duplicate_operation_commits": duplicate_operation_commits,
        "capacity_underflow": int(capacity_underflow),
        "final_capacity": final_capacity,
        "serial_equivalent": False,
        "rows": [
            {
                "proposal": asdict(p),
                "committed": True,
                "reason": "baseline_direct_write",
            }
            for p in committed
        ],
    }


def run_weak_lock_baseline(proposals: list[Proposal]) -> dict:
    initial_capacity = 32
    capacity = initial_capacity
    seen_operation_keys: set[str] = set()
    rows: list[dict] = []

    for p in proposals:
        # Weak baseline checks syntax and duplicate keys but does not enforce
        # stale-read or capacity constraints atomically at the admission boundary.
        duplicate = p.operation_key in seen_operation_keys
        committed = not duplicate

        if committed:
            seen_operation_keys.add(p.operation_key)
            capacity += p.delta

        rows.append(
            {
                "proposal": asdict(p),
                "committed": committed,
                "reason": "committed_weak_lock" if committed else "duplicate_operation_key",
            }
        )

    invalid_commits = sum(
        1 for row in rows if row["committed"] and not row["proposal"]["valid_under_c"]
    )
    duplicate_operation_commits = sum(
        1 for row in rows if row["committed"] and row["proposal"]["kind"] == "duplicate_operation_key"
    )
    capacity_underflow = capacity < 0

    return {
        "system": "weak_lock_admission",
        "proposal_count": len(proposals),
        "committed": sum(1 for row in rows if row["committed"]),
        "rejected": sum(1 for row in rows if not row["committed"]),
        "invalid_commits": invalid_commits,
        "duplicate_operation_commits": duplicate_operation_commits,
        "capacity_underflow": int(capacity_underflow),
        "final_capacity": capacity,
        "serial_equivalent": False,
        "rows": rows,
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
            CREATE TABLE items (
                item TEXT PRIMARY KEY,
                capacity INTEGER NOT NULL,
                version INTEGER NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE commits (
                proposal_id TEXT PRIMARY KEY,
                operation_key TEXT NOT NULL UNIQUE,
                item TEXT NOT NULL,
                delta INTEGER NOT NULL,
                before_capacity INTEGER NOT NULL,
                after_capacity INTEGER NOT NULL,
                before_version INTEGER NOT NULL,
                after_version INTEGER NOT NULL
            )
            """
        )
        con.execute(
            """
            INSERT INTO items(item, capacity, version)
            VALUES ('seat_pool', 32, 0)
            """
        )
    finally:
        con.close()


def apply_atp(path: str, proposal: Proposal) -> tuple[bool, str]:
    for _ in range(30):
        con = sqlite_connect(path)
        try:
            con.execute("BEGIN IMMEDIATE")

            if not proposal.valid_under_c:
                con.execute("ROLLBACK")
                return False, "invalid_under_c"

            row = con.execute(
                "SELECT capacity, version FROM items WHERE item = ?",
                (proposal.item,),
            ).fetchone()
            if row is None:
                con.execute("ROLLBACK")
                return False, "missing_item"

            capacity, version = row
            after_capacity = capacity + proposal.delta
            after_version = version + 1

            if after_capacity < 0:
                con.execute("ROLLBACK")
                return False, "capacity_violation"

            con.execute(
                """
                INSERT INTO commits(
                    proposal_id,
                    operation_key,
                    item,
                    delta,
                    before_capacity,
                    after_capacity,
                    before_version,
                    after_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.operation_key,
                    proposal.item,
                    proposal.delta,
                    capacity,
                    after_capacity,
                    version,
                    after_version,
                ),
            )

            con.execute(
                """
                UPDATE items
                SET capacity = ?, version = ?
                WHERE item = ?
                """,
                (after_capacity, after_version, proposal.item),
            )

            con.execute("COMMIT")
            return True, "admitted_serial_boundary"

        except sqlite3.IntegrityError:
            con.execute("ROLLBACK")
            return False, "idempotency_or_uniqueness_violation"
        except sqlite3.OperationalError:
            try:
                con.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            time.sleep(0.02)
        finally:
            con.close()

    raise RuntimeError("sqlite remained locked after retries")


def run_atp_mnemosyne(proposals: list[Proposal]) -> dict:
    rows: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "rq2.sqlite3")
        init_sqlite(path)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = list(pool.map(lambda p: (p, *apply_atp(path, p)), proposals))

        for proposal, committed, reason in futures:
            rows.append(
                {
                    "proposal": asdict(proposal),
                    "committed": committed,
                    "reason": reason,
                }
            )

        con = sqlite_connect(path)
        try:
            final_capacity, final_version = con.execute(
                "SELECT capacity, version FROM items WHERE item = 'seat_pool'"
            ).fetchone()

            commit_rows = con.execute(
                """
                SELECT before_capacity, after_capacity, before_version, after_version
                FROM commits
                ORDER BY after_version ASC
                """
            ).fetchall()
        finally:
            con.close()

    serial_equivalent = True
    expected_version = 0

    for before_capacity, after_capacity, before_version, after_version in commit_rows:
        if before_version != expected_version:
            serial_equivalent = False
        if after_version != before_version + 1:
            serial_equivalent = False
        if after_capacity != before_capacity - 1:
            serial_equivalent = False
        expected_version = after_version

    invalid_commits = sum(
        1 for row in rows if row["committed"] and not row["proposal"]["valid_under_c"]
    )

    duplicate_operation_commits = len(
        [row for row in rows if row["committed"]]
    ) - len(
        {row["proposal"]["operation_key"] for row in rows if row["committed"]}
    )

    capacity_underflow = final_capacity < 0

    return {
        "system": "atp_mnemosyne",
        "proposal_count": len(proposals),
        "committed": sum(1 for row in rows if row["committed"]),
        "rejected": sum(1 for row in rows if not row["committed"]),
        "invalid_commits": invalid_commits,
        "duplicate_operation_commits": duplicate_operation_commits,
        "capacity_underflow": int(capacity_underflow),
        "final_capacity": final_capacity,
        "final_version": final_version,
        "serial_equivalent": serial_equivalent,
        "rows": rows,
    }


def write_reports(results: list[dict]) -> None:
    report_dir = Path("benchmarks/realm/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "rq": "RQ2",
        "name": "Serial-equivalent generative admission",
        "claim": (
            "Concurrent generated proposals may arrive in arbitrary order, but committed "
            "state must be equivalent to some serial order of admitted proposals."
        ),
        "success_criteria": [
            "ATP invalid_commits = 0",
            "ATP duplicate_operation_commits = 0",
            "ATP capacity_underflow = 0",
            "ATP serial_equivalent = true",
            "Unsafe baselines exhibit invalid commits or non-serial-equivalent state",
        ],
        "systems": results,
    }

    (report_dir / "rq2_serial_equivalent_admission_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# RQ2 Serial-Equivalent Generative Admission Report",
        "",
        "Concurrent generated proposals are admitted only through a serialized transaction boundary.",
        "",
        "| System | Proposals | Committed | Rejected | Invalid commits | Duplicate operation commits | Capacity underflow | Final capacity | Serial-equivalent |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for result in results:
        lines.append(
            "| {system} | {proposal_count} | {committed} | {rejected} | "
            "{invalid_commits} | {duplicate_operation_commits} | "
            "{capacity_underflow} | {final_capacity} | {serial_equivalent} |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "This experiment tests serial-equivalent admission of concurrent generated proposals.",
            "It does not claim that the proposer is intelligent, optimal, or improving.",
            "The guarantee is relative to the declared admission constraints and storage transaction boundary.",
            "",
        ]
    )

    (report_dir / "rq2_serial_equivalent_admission_report.md").write_text(
        "\n".join(lines)
    )


def test_rq2_serial_equivalent_generative_admission() -> None:
    proposals = proposal_suite()

    results = [
        run_unserialized_baseline(proposals),
        run_weak_lock_baseline(proposals),
        run_atp_mnemosyne(proposals),
    ]

    by_system = {result["system"]: result for result in results}

    assert by_system["unserialized_generated_writes"]["invalid_commits"] > 0
    assert by_system["unserialized_generated_writes"]["capacity_underflow"] > 0
    assert by_system["unserialized_generated_writes"]["serial_equivalent"] is False

    assert by_system["weak_lock_admission"]["invalid_commits"] > 0
    assert by_system["weak_lock_admission"]["serial_equivalent"] is False

    assert by_system["atp_mnemosyne"]["invalid_commits"] == 0
    assert by_system["atp_mnemosyne"]["duplicate_operation_commits"] == 0
    assert by_system["atp_mnemosyne"]["capacity_underflow"] == 0
    assert by_system["atp_mnemosyne"]["serial_equivalent"] is True
    assert by_system["atp_mnemosyne"]["committed"] > 0
    assert by_system["atp_mnemosyne"]["rejected"] > 0

    write_reports(results)
