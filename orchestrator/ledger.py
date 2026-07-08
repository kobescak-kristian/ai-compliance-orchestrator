"""SQLite DDL for the task ledger and its companion tables (BLUEPRINT.md
§5, §3). Schema + create_db() only -- state-machine logic (transitions,
resume-from-ledger, dedup) lives in orchestrator/pipeline.py (Phase 2).

task_ledger holds one row per (task_id, stage, attempt): every task,
every stage, mirroring contracts.schemas.LedgerRow column-for-column.
dead_letter holds payloads that failed contract validation at a boundary
(FI-2): the raw payload is preserved, downstream never sees it.
findings/proposals hold validated ViolationFinding/RemediationProposal
rows, each with a UNIQUE(content_hash, rule_id) constraint so a forced
re-run cannot create duplicates (FI-6) even if ledger-resume is bypassed.
audit_log records every rule-set access attempt, allowed or rejected
(FI-7) -- the deterministic analogue of the shipped verifier's
PreToolUse/PostToolUse audit hooks, for boundaries that exist before any
real agent does. path_access_log is the same pattern for path-taking
tools (fetch_page, Phase 3): written synchronously inside the tool call
itself, so it is testable without a live agent run and unconditionally
precedes any use of the tool's result.
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

FINDINGS_DDL = """
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    page_path TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    verdict TEXT NOT NULL,
    evidence_excerpt TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (content_hash, rule_id)
);
"""

PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    page_path TEXT NOT NULL,
    offending_text TEXT NOT NULL,
    proposed_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by_run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (content_hash, rule_id)
);
"""

AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requesting_jurisdiction TEXT NOT NULL,
    requested_jurisdiction TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);
"""

PATH_ACCESS_LOG_DDL = """
CREATE TABLE IF NOT EXISTS path_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    requested_path TEXT NOT NULL,
    allowed INTEGER NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);
"""


def create_db(db_path: str) -> sqlite3.Connection:
    """Create every table at db_path if absent; return an open connection.
    No state-machine logic here.
    """
    conn = sqlite3.connect(db_path)
    conn.execute(TASK_LEDGER_DDL)
    conn.execute(DEAD_LETTER_DDL)
    conn.execute(FINDINGS_DDL)
    conn.execute(PROPOSALS_DDL)
    conn.execute(AUDIT_LOG_DDL)
    conn.execute(PATH_ACCESS_LOG_DDL)
    conn.commit()
    return conn
