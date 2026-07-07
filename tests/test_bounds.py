"""Per-agent cage checks (BLUEPRINT.md §3, §4) and the rule-isolation
check (FI-7 companion, BLUEPRINT.md §6). Extends the
ai-claim-verification-agent bounds-test pattern to every agent in this
system. Skeletons only until each agent lands (BLUEPRINT.md §9).
"""
import pytest


def test_checker_cage():
    """Checker (x3) | LLM agent | Tools: fetch_page, read_ruleset (own
    jurisdiction only), emit_finding | May never: see other
    jurisdictions' rules, write files, network. (BLUEPRINT.md §4) Caged
    per §3: allowed_tools whitelist, max_turns cap, per-run budget
    ceiling + call-count circuit breaker, PreToolUse/PostToolUse hooks ->
    audit.db before results are used.
    """
    pytest.skip("implemented Phase 2+")


def test_verifier_cage():
    """Verifier | LLM agent (shipped) | Tools: its existing 4 read-only
    tools | May never: anything outside its dataset dir (existing bounds
    suite). (BLUEPRINT.md §4) Reused, not forked: subprocess node with
    JSON stdin/stdout contract; the shipped repo stays untouched (§3).
    """
    pytest.skip("implemented Phase 2+")


def test_planner_cage():
    """Planner | LLM agent | Tools: read_finding, read_rule,
    emit_proposal | May never: fetch pages, write files, approve its own
    proposal. (BLUEPRINT.md §4)
    """
    pytest.skip("implemented Phase 2+")


def test_rule_isolation_checker_cross_jurisdiction():
    """FI-7 | Path escape attempt in any agent tool input; checker
    requests another jurisdiction's rule set | Rejected; audit row
    written (extends the verifier's bounds test to all agents +
    rule-isolation check)
    """
    pytest.skip("implemented Phase 2+")
