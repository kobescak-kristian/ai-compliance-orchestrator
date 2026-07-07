"""SQLite DDL for the task ledger and dead-letter table (BLUEPRINT.md §5,
§3). Schema + create_db() only -- state-machine logic (transitions,
resume-from-ledger, dedup) lands Phase 2 (BLUEPRINT.md §9).

task_ledger holds one row per (task_id, stage, attempt): every task,
every stage, mirroring contracts.schemas.LedgerRow column-for-column.
dead_letter holds payloads that failed contract validation at a boundary
(FI-2): the raw payload is preserved, downstream never sees it.
"""
import sqlite3

TASK_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS task_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'QUEUED', 'RUNNING', 'DONE', 'FAILED', 'DEAD_LETTER', 'ESCALATED'
    )),
    attempt INTEGER NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    exit_code INTEGER,
    error_class TEXT,
    payload_ref TEXT
);
"""

DEAD_LETTER_DDL = """
CREATE TABLE IF NOT EXISTS dead_letter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    stage TEXT,
    raw_payload TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def create_db(db_path: str) -> sqlite3.Connection:
    """Create task_ledger and dead_letter at db_path if absent; return an
    open connection. No state-machine logic here.
    """
    conn = sqlite3.connect(db_path)
    conn.execute(TASK_LEDGER_DDL)
    conn.execute(DEAD_LETTER_DDL)
    conn.commit()
    return conn
