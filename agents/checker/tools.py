"""The 3 in-process MCP tools available to the checker agent (BLUEPRINT.md
§4): fetch_page, read_ruleset (own jurisdiction only), emit_finding.
Built fresh per CheckTask via build_tools() so each run is bound to
exactly one page/jurisdiction -- there is no way for a tool call to name
a different task's data.

Read-only by construction, matching the shipped verifier's tools.py
pattern: fetch_page and read_ruleset only ever read local files;
emit_finding only ever appends to an in-memory list. None can write,
edit, execute shell commands, or reach beyond their bound scope.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from claude_agent_sdk import tool
from pydantic import ValidationError

from contracts.schemas import CheckTask, ViolationFinding
from intake.inventory import RuleAccessDenied, read_ruleset

from . import pages
from .config import MAX_TOOL_CALLS, RULESETS_DIR

# Populated by emit_finding during a run; harness.py reads it after
# query() completes. Reset by reset_run_state() before each run -- safe
# as module state because CheckTasks are processed sequentially, never
# concurrently (same rationale as the shipped verifier's tools.py).
findings: list[dict] = []

_tool_call_count = 0
_circuit_breaker_tripped_flag = False


def reset_run_state() -> None:
    """Call before each CheckTask run: clears findings and the
    circuit-breaker counter/flag."""
    global _tool_call_count, _circuit_breaker_tripped_flag
    findings.clear()
    _tool_call_count = 0
    _circuit_breaker_tripped_flag = False


def circuit_breaker_tripped() -> bool:
    """Read after a run completes: True if MAX_TOOL_CALLS was hit during
    it. harness.py uses this to raise BudgetExceededError (FI-1)."""
    return _circuit_breaker_tripped_flag


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "is_error": True}


def _check_circuit_breaker() -> dict | None:
    """Hard backstop on total tool calls for this run, independent of
    max_turns (BLUEPRINT.md §3: "call-count circuit breaker")."""
    global _tool_call_count, _circuit_breaker_tripped_flag
    _tool_call_count += 1
    if _tool_call_count > MAX_TOOL_CALLS:
        _circuit_breaker_tripped_flag = True
        return _error(
            f"Circuit breaker tripped: tool-call ceiling ({MAX_TOOL_CALLS}) "
            "reached for this run. No further tool calls will be served."
        )
    return None


def _log_path_access(ledger_conn: sqlite3.Connection, requested_path: str, allowed: bool, reason: str | None) -> None:
    """Deterministic audit write for fetch_page, mirroring read_ruleset's
    audit_log pattern (FI-7 extended to path-taking tools): written
    synchronously inside the tool call, before the caller can act on any
    result, so it is testable without a live agent run.
    """
    ledger_conn.execute(
        "INSERT INTO path_access_log (tool_name, requested_path, allowed, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("fetch_page", requested_path, int(allowed), reason, datetime.now(timezone.utc).isoformat()),
    )
    ledger_conn.commit()


def build_tools(task: CheckTask, ledger_conn: sqlite3.Connection):
    """Build the 3 tools bound to one CheckTask. own_jurisdiction is
    fixed to task.jurisdiction -- read_ruleset can never be pointed at a
    different jurisdiction, whatever the agent asks for (rule-isolation
    bound, FI-7).
    """
    own_jurisdiction = task.jurisdiction
    task_id = f"{task.page_path}::{task.jurisdiction}"

    @tool(
        "fetch_page",
        "Fetch the local HTML page you have been assigned, by its relative "
        "path (e.g. 'p01.html'). Returns the page title and its paragraphs. "
        "Rejects any path outside evals/dataset/pages/.",
        {"path": str},
    )
    async def fetch_page(args):
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped
        requested_path = args["path"]
        try:
            title, paragraphs = pages.read_page(requested_path)
        except pages.PathOutsideDatasetError as e:
            _log_path_access(ledger_conn, requested_path, allowed=False, reason=str(e))
            return _error(str(e))
        except FileNotFoundError as e:
            _log_path_access(ledger_conn, requested_path, allowed=False, reason=str(e))
            return _error(str(e))
        _log_path_access(ledger_conn, requested_path, allowed=True, reason=None)
        body = "\n".join(f"- {p}" for p in paragraphs)
        return {"content": [{"type": "text", "text": f"# {title}\n\n{body}"}]}

    @tool(
        "read_ruleset",
        f"Read your assigned jurisdiction's ({own_jurisdiction}) rule set. "
        "The jurisdiction argument must equal your own jurisdiction -- "
        "requesting any other jurisdiction's rule set is rejected and "
        "logged.",
        {"jurisdiction": str},
    )
    async def read_ruleset_tool(args):
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped
        try:
            rules = read_ruleset(own_jurisdiction, args["jurisdiction"], RULESETS_DIR, ledger_conn)
        except RuleAccessDenied as e:
            return _error(str(e))
        except FileNotFoundError as e:
            return _error(str(e))
        lines = [
            f"{r.rule_id} | {r.category.value} | {r.severity.value} | {r.rule_text}"
            for r in rules
        ]
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    @tool(
        "emit_finding",
        "Record your verdict for one rule against your assigned page. "
        "verdict must be exactly one of COMPLIANT, VIOLATION, "
        "NOT_APPLICABLE. Call this once per rule in your rule set.",
        {"rule_id": str, "verdict": str, "evidence_excerpt": str, "rationale": str},
    )
    async def emit_finding(args):
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped

        raw = {
            "page_path": task.page_path,
            "jurisdiction": task.jurisdiction,
            "rule_id": args.get("rule_id"),
            "ruleset_version": task.ruleset_version,
            "verdict": args.get("verdict"),
            "evidence_excerpt": args.get("evidence_excerpt"),
            "rationale": args.get("rationale"),
            "task_id": task_id,
        }
        try:
            finding = ViolationFinding(**raw)
        except ValidationError as e:
            # Tool-boundary validation (BLUEPRINT.md §3): reject immediately
            # so the agent can retry within its turn budget. The orchestrator
            # re-validates independently and atomically dead-letters the
            # whole task if a bad payload reaches it anyway (SPEC.md
            # amendment: DEAD_LETTER is task-atomic).
            return _error(f"Invalid finding, not recorded: {e}")

        findings.append(finding.model_dump(mode="json"))
        return {
            "content": [
                {"type": "text", "text": f"Recorded: {finding.verdict.value} — {finding.rule_id}"}
            ]
        }

    return [fetch_page, read_ruleset_tool, emit_finding]
