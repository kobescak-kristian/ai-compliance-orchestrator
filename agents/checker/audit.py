"""SQLite audit trail (BLUEPRINT.md §3: PreToolUse/PostToolUse hooks ->
audit.db before results are used). Reused directly from
ai-claim-verification-agent's agent/audit.py pattern (SPEC.md
non-negotiable: "Reuse agent/audit.py pattern directly").

Shared across a run: each row is keyed by run_id (one per dev/eval-leg
invocation) and task_id (the CheckTask that invocation was scoped to).
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import AUDIT_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    task_id TEXT,
    session_id TEXT,
    tool_use_id TEXT,
    tool_name TEXT,
    event_type TEXT,
    timestamp TEXT,
    payload TEXT
)
"""

# Set via set_run_context() before each fresh agent invocation. The hook
# callback signature is fixed by the SDK (input_data, tool_use_id, context),
# so it can't take run_id/task_id as arguments directly -- module-level
# state is safe here because invocations run sequentially, never
# concurrently (same rationale as the shipped verifier's audit.py).
_current_run_id: str | None = None
_current_task_id: str | None = None

# Where this agent's audit rows go. Default is the repo-root audit.db
# (unchanged); the eval runner sets a fresh DB per run under the private
# run directory (P2 storage requirement; gate overall.runs_independent).
_audit_db_path: Path = AUDIT_DB_PATH


def set_audit_db_path(path) -> None:
    global _audit_db_path
    _audit_db_path = Path(path)


def get_audit_db_path() -> Path:
    return _audit_db_path


def set_run_context(run_id: str, task_id: str) -> None:
    global _current_run_id, _current_task_id
    _current_run_id = run_id
    _current_task_id = task_id


def init_audit_db() -> None:
    conn = sqlite3.connect(_audit_db_path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _insert(session_id, tool_use_id, tool_name, event_type, payload: dict) -> None:
    conn = sqlite3.connect(_audit_db_path)
    try:
        conn.execute(
            "INSERT INTO tool_calls (run_id, task_id, session_id, tool_use_id, "
            "tool_name, event_type, timestamp, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _current_run_id,
                _current_task_id,
                session_id,
                tool_use_id,
                tool_name,
                event_type,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(payload, default=str),
            ),
        )
        conn.commit()
    finally:
        conn.close()


async def audit_hook(input_data, tool_use_id, context):
    """Registered on both PreToolUse and PostToolUse. Writes to SQLite
    before the result is used by the model -- that write happens here,
    synchronously, before this hook returns control to the SDK."""
    event = input_data.get("hook_event_name")
    if event == "PreToolUse":
        _insert(
            input_data.get("session_id"), tool_use_id, input_data.get("tool_name"),
            "PreToolUse", {"tool_input": input_data.get("tool_input")},
        )
    elif event == "PostToolUse":
        _insert(
            input_data.get("session_id"), tool_use_id, input_data.get("tool_name"),
            "PostToolUse",
            {
                "tool_input": input_data.get("tool_input"),
                "tool_response": input_data.get("tool_response"),
            },
        )
    return {}
