"""Per-agent cage checks (BLUEPRINT.md §3, §4) and the rule-isolation
check (FI-7 companion, BLUEPRINT.md §6). Extends the
ai-claim-verification-agent bounds-test pattern to every agent in this
system. test_checker_cage and test_rule_isolation_checker_cross_
jurisdiction exercise the real checker agent's tools directly (Phase 3);
verifier/planner cage tests stay skipped until their agents land
(BLUEPRINT.md §9).

Both implemented tests call tool handlers directly rather than through a
live query() -- matching the shipped verifier's own bounds-test pattern
(tests/test_bounds.py there also calls .handler() directly for the
rejection checks). The audit writes under test here (path_access_log,
audit_log) happen synchronously inside the tool call itself, not only
via the SDK's PreToolUse/PostToolUse hooks, so they are exercised
identically whether the call comes from a live model or a test.
"""
import asyncio
import os
import tempfile

import pytest

from agents.checker.tools import build_tools
from contracts.schemas import CheckTask
from orchestrator.ledger import create_db


@pytest.fixture
def conn():
    db_path = tempfile.mktemp(suffix=".db")
    connection = create_db(db_path)
    yield connection
    connection.close()
    os.remove(db_path)


def test_checker_cage(conn):
    """Checker (x3) | LLM agent | Tools: fetch_page, read_ruleset (own
    jurisdiction only), emit_finding | May never: see other
    jurisdictions' rules, write files, network. (BLUEPRINT.md §4) Caged
    per §3: allowed_tools whitelist, max_turns cap, per-run budget
    ceiling + call-count circuit breaker, PreToolUse/PostToolUse hooks ->
    audit.db before results are used.

    Here: a path-escape attempt through fetch_page is rejected, and the
    rejection is audited (path_access_log) -- with the audit write
    happening synchronously before the tool returns, so no caller can
    ever observe a result without a preceding audit row for that call.
    """
    task = CheckTask(page_path="p01.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-BT-01"])
    fetch_page, _read_ruleset, _emit_finding = build_tools(task, conn)

    escape_attempts = ["../../../etc/passwd", "..\\..\\SPEC.md", "/etc/passwd"]
    for escape_path in escape_attempts:
        result = asyncio.run(fetch_page.handler({"path": escape_path}))
        assert result.get("is_error") is True
        text = result["content"][0]["text"]
        assert "outside" in text.lower() or "rejected" in text.lower()

        # audited: a row exists recording the rejection for this exact path
        row = conn.execute(
            "SELECT allowed, reason FROM path_access_log WHERE requested_path = ? "
            "ORDER BY id DESC LIMIT 1",
            (escape_path,),
        ).fetchone()
        assert row is not None, f"no audit row written for rejected path {escape_path!r}"
        assert row[0] == 0  # allowed=False
        assert row[1] == text  # audited reason matches what the caller was actually told

    # legitimate read is allowed and also audited -- proves the write is
    # unconditional, not just a rejection-path side effect
    ok_result = asyncio.run(fetch_page.handler({"path": "p01.html"}))
    assert ok_result.get("is_error") is None
    ok_row = conn.execute(
        "SELECT allowed FROM path_access_log WHERE requested_path = 'p01.html' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert ok_row == (1,)

    # audit rows precede result use: every escape attempt's audit row was
    # already committed and readable before this test ever inspected the
    # tool's own return value above -- ordering is enforced by the tool's
    # own control flow (audit write, then return), not by test timing.
    total_rejections = conn.execute(
        "SELECT COUNT(*) FROM path_access_log WHERE allowed = 0"
    ).fetchone()[0]
    assert total_rejections == len(escape_attempts)


def test_verifier_cage():
    """Verifier | LLM agent (shipped) | Tools: its existing 4 read-only
    tools | May never: anything outside its dataset dir (existing bounds
    suite). (BLUEPRINT.md §4) Reused, not forked: subprocess node with
    JSON stdin/stdout contract; the shipped repo stays untouched (§3).
    """
    pytest.skip("implemented Phase 4 (verifier subprocess node)")


def test_planner_cage():
    """Planner | LLM agent | Tools: read_finding, read_rule,
    emit_proposal | May never: fetch pages, write files, approve its own
    proposal. (BLUEPRINT.md §4)
    """
    pytest.skip("implemented Phase 5 (real planner agent)")


def test_rule_isolation_checker_cross_jurisdiction(conn):
    """FI-7 | Path escape attempt in any agent tool input; checker
    requests another jurisdiction's rule set | Rejected; audit row
    written (extends the verifier's bounds test to all agents +
    rule-isolation check)

    Here: a checker bound to MLT calling read_ruleset for GBR (or any
    non-MLT jurisdiction) is rejected and audited via
    intake.inventory.read_ruleset's audit_log write -- the same
    deterministic mechanism FI-7 already proved in Phase 2, now exercised
    through the real agent's tool wrapper instead of the bare function.
    """
    task = CheckTask(page_path="p01.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-BT-01"])
    _fetch_page, read_ruleset_tool, _emit_finding = build_tools(task, conn)

    for other in ("GBR", "DEU"):
        result = asyncio.run(read_ruleset_tool.handler({"jurisdiction": other}))
        assert result.get("is_error") is True
        assert "may not read" in result["content"][0]["text"]

    rows = conn.execute(
        "SELECT requesting_jurisdiction, requested_jurisdiction, allowed FROM audit_log ORDER BY id"
    ).fetchall()
    assert rows == [("MLT", "GBR", 0), ("MLT", "DEU", 0)]

    # own jurisdiction is allowed and also audited
    ok = asyncio.run(read_ruleset_tool.handler({"jurisdiction": "MLT"}))
    assert ok.get("is_error") is None
    last_row = conn.execute(
        "SELECT requesting_jurisdiction, requested_jurisdiction, allowed FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert last_row == ("MLT", "MLT", 1)
