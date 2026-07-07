"""Failure-injection suite, FI-1..FI-7 (BLUEPRINT.md §6). Each row of that
table is a test here, not a README promise. Skeletons only until the
orchestrator core they assert against lands (Phase 2+, BLUEPRINT.md §9).
"""
import pytest


def test_fi1_budget_turn_cap():
    """FI-1 | Agent budget/turn cap trips mid-task | Task -> FAILED with
    error_class; run completes; zero lost tasks
    """
    pytest.skip("implemented Phase 2+")


def test_fi2_schema_invalid_payload():
    """FI-2 | Agent emits schema-invalid payload (e.g. finding without
    rule_id) | Rejected at boundary -> DEAD_LETTER row with raw payload;
    downstream never sees it
    """
    pytest.skip("implemented Phase 2+")


def test_fi3_orchestrator_killed_and_restarted():
    """FI-3 | Orchestrator killed mid-run, restarted | Resumes from
    ledger; completed tasks not re-run; zero duplicate findings/proposals
    """
    pytest.skip("implemented Phase 2+")


def test_fi4_ruleset_missing_or_corrupt():
    """FI-4 | One jurisdiction's rule set missing/corrupt | Other
    jurisdictions proceed; MISSING_RULESET recorded per affected task;
    aggregation proceeds with explicit gap, not silent success
    """
    pytest.skip("implemented Phase 2+")


def test_fi5_conflicting_findings():
    """FI-5 | Conflicting findings on the same excerpt (checker:
    COMPLIANT; verifier: CONTRADICTED -- or two rules colliding) | Task ->
    ESCALATED, surfaced in human queue with both artifacts -- never
    auto-resolved
    """
    pytest.skip("implemented Phase 2+")


def test_fi6_idempotent_rerun():
    """FI-6 | Full re-run on identical input | Idempotent: zero duplicate
    findings/proposals (dedup on content hash + rule_id)
    """
    pytest.skip("implemented Phase 2+")


def test_fi7_path_escape_and_rule_isolation():
    """FI-7 | Path escape attempt in any agent tool input; checker
    requests another jurisdiction's rule set | Rejected; audit row
    written (extends the verifier's bounds test to all agents +
    rule-isolation check)
    """
    pytest.skip("implemented Phase 2+")
