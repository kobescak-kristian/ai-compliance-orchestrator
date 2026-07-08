"""End-to-end acceptance test for the Phase 2 stub pipeline
(BLUEPRINT.md §9 row 2): intake -> check (stub) -> aggregate, producing
SeverityReports, with every task reaching a terminal state and zero
lost. Plan stage (stub) is exercised too, though its acceptance owner is
Phase 5.
"""
import os
import tempfile

import pytest

from agents.checker import stub as checker_stub
from agents.planner import stub as planner_stub
from intake.inventory import build_check_tasks, load_rulesets
from orchestrator.aggregation import build_severity_reports
from orchestrator.ledger import create_db
from orchestrator.pipeline import get_findings, run_check_stage, run_plan_stage


@pytest.fixture
def conn():
    checker_stub.reset_failures()
    planner_stub.reset_failures()
    db_path = tempfile.mktemp(suffix=".db")
    connection = create_db(db_path)
    yield connection
    connection.close()
    os.remove(db_path)


def test_full_pipeline_end_to_end_produces_severity_reports(conn):
    tasks, missing = build_check_tasks("evals/dataset/pages", "rulesets")
    assert missing == set()  # real dataset: no gaps expected
    assert len(tasks) == 23  # 12 pages, one CheckTask per targeted jurisdiction

    run_check_stage(tasks, checker_stub.stub_checker, conn)

    # every task reaches a terminal state; zero lost
    terminal = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM task_ledger WHERE stage='check' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchone()[0]
    assert terminal == len(tasks)
    non_terminal = conn.execute(
        "SELECT COUNT(*) FROM task_ledger t1 WHERE stage='check' AND id = "
        "(SELECT MAX(id) FROM task_ledger t2 WHERE t2.task_id = t1.task_id AND t2.stage = 'check') "
        "AND state NOT IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchone()[0]
    assert non_terminal == 0

    findings = get_findings(conn)
    assert findings  # zero LLM calls, but the stub still produced fixture findings

    rulesets = load_rulesets("rulesets")
    rules_by_id = {r.rule_id: r for rules in rulesets.values() for r in rules}

    findings_by_page = {}
    for f in findings:
        findings_by_page.setdefault(f.page_path, []).append(f)

    reports = build_severity_reports(findings_by_page, rules_by_id)

    assert len(reports) == len(findings_by_page)
    ranks = sorted(r.rank for r in reports)
    assert ranks == list(range(1, len(reports) + 1))  # rank is a dense permutation
    scores = [r.severity_score for r in reports]
    assert scores == sorted(scores, reverse=True)  # ranked descending
    assert all(r.severity_score >= 0 for r in reports)
    assert all(r.findings for r in reports)  # each report carries its findings


def test_plan_stage_drafts_proposals_for_violations(conn):
    tasks, _ = build_check_tasks("evals/dataset/pages", "rulesets")
    run_check_stage(tasks, checker_stub.stub_checker, conn)
    findings = get_findings(conn)
    violations = [f for f in findings if f.verdict.value == "VIOLATION"]
    assert violations  # fixtures include at least one VIOLATION

    run_plan_stage(violations, planner_stub.stub_planner, conn)

    terminal = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM task_ledger WHERE stage='plan' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchone()[0]
    assert terminal == len(violations)

    proposal_count = conn.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
    assert proposal_count == len(violations)
