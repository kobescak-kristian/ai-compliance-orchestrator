"""Failure-injection suite, FI-1..FI-7 (BLUEPRINT.md §6). Each row of that
table is a test here, not a README promise. FI-1..FI-4, FI-6, FI-7 run
against the Phase 2 orchestrator core with stub agents; FI-5 needs the
verifier subprocess node and stays skipped until Phase 4
(BLUEPRINT.md §9).
"""
import os
import tempfile

import pytest

from agents.checker import stub as checker_stub
from contracts.schemas import CheckTask
from intake.inventory import RuleAccessDenied, build_check_tasks, read_ruleset
from orchestrator.ledger import create_db
from orchestrator.pipeline import get_findings, register_tasks, run_check_stage, task_id_for


@pytest.fixture
def conn():
    checker_stub.reset_failures()
    db_path = tempfile.mktemp(suffix=".db")
    connection = create_db(db_path)
    yield connection
    connection.close()
    os.remove(db_path)


def _latest_state(conn, task_id, stage="check"):
    row = conn.execute(
        "SELECT state, error_class FROM task_ledger WHERE task_id = ? AND stage = ? "
        "ORDER BY id DESC LIMIT 1",
        (task_id, stage),
    ).fetchone()
    return row


def test_fi1_budget_turn_cap(conn):
    """FI-1 | Agent budget/turn cap trips mid-task | Task -> FAILED with
    error_class; run completes; zero lost tasks
    """
    tasks = [
        CheckTask(page_path="p01.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-BT-01"]),
        CheckTask(page_path="p05.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-RG-01"]),
    ]
    checker_stub.configure_failure("p01.html", "MLT", "budget")

    run_check_stage(tasks, checker_stub.stub_checker, conn)

    tripped = _latest_state(conn, task_id_for(tasks[0]))
    assert tripped == ("FAILED", "BUDGET_EXCEEDED")

    # run completes: the other task still reaches its own terminal state
    other = _latest_state(conn, task_id_for(tasks[1]))
    assert other[0] == "DONE"

    # zero lost tasks: every task registered has a terminal ledger row
    terminal = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM task_ledger WHERE stage='check' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchone()[0]
    assert terminal == len(tasks)


def test_fi2_schema_invalid_payload(conn):
    """FI-2 | Agent emits schema-invalid payload (e.g. finding without
    rule_id) | Rejected at boundary -> DEAD_LETTER row with raw payload;
    downstream never sees it
    """
    tasks = [
        CheckTask(
            page_path="p01.html", jurisdiction="MLT", ruleset_version="v1.0",
            assigned_rules=["MLT-BT-01", "MLT-BT-02"],
        )
    ]
    checker_stub.configure_failure("p01.html", "MLT", "malformed")

    run_check_stage(tasks, checker_stub.stub_checker, conn)

    tid = task_id_for(tasks[0])
    assert _latest_state(conn, tid) == ("DEAD_LETTER", "SCHEMA_INVALID")

    dead_letters = conn.execute(
        "SELECT task_id, raw_payload FROM dead_letter WHERE task_id = ?", (tid,)
    ).fetchall()
    assert len(dead_letters) == 1
    assert "rule_id" not in dead_letters[0][1] or '"rule_id"' not in dead_letters[0][1]

    # downstream never sees it: no findings reached storage for this task
    findings = [f for f in get_findings(conn) if f.task_id == tid]
    assert findings == []


def test_fi3_orchestrator_killed_and_restarted(conn):
    """FI-3 | Orchestrator killed mid-run, restarted | Resumes from
    ledger; completed tasks not re-run; zero duplicate findings/proposals
    """
    tasks = [
        CheckTask(page_path="p01.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-BT-01"]),
        CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.0", assigned_rules=["GBR-GE-01"]),
        CheckTask(page_path="p05.html", jurisdiction="MLT", ruleset_version="v1.0", assigned_rules=["MLT-RG-01"]),
    ]

    call_log = []

    def counting_checker(task):
        call_log.append(task_id_for(task))
        return checker_stub.stub_checker(task)

    # Simulate a crash: a stray RUNNING row with no terminal follow-up for task 3
    register_tasks([task_id_for(t) for t in tasks], conn, "check")
    conn.execute(
        "INSERT INTO task_ledger (task_id, stage, state, attempt, started_at) "
        "VALUES (?, 'check', 'RUNNING', 1, 'x')",
        (task_id_for(tasks[2]),),
    )
    conn.commit()

    # Partial run before the simulated kill: only task 1
    run_check_stage(tasks[:1], counting_checker, conn)
    # Restart: resubmit the full task list
    run_check_stage(tasks, counting_checker, conn)

    # completed tasks not re-run
    assert call_log.count(task_id_for(tasks[0])) == 1
    # the interrupted task (stray RUNNING, no terminal row) IS retried
    assert call_log.count(task_id_for(tasks[2])) == 1

    terminal_rows = conn.execute(
        "SELECT task_id, attempt FROM task_ledger WHERE stage='check' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchall()
    # zero lost tasks, and each has exactly one terminal row (no duplicates)
    assert len(terminal_rows) == len(tasks)
    assert len({tid for tid, _ in terminal_rows}) == len(tasks)

    t3_attempt = [a for tid, a in terminal_rows if tid == task_id_for(tasks[2])][0]
    assert t3_attempt == 2  # retried after the interrupted attempt 1

    # zero duplicate findings
    findings = get_findings(conn)
    keys = [(f.task_id, f.rule_id) for f in findings]
    assert len(keys) == len(set(keys))


def test_fi4_ruleset_missing_or_corrupt(conn):
    """FI-4 | One jurisdiction's rule set missing/corrupt | Other
    jurisdictions proceed; MISSING_RULESET recorded per affected task;
    aggregation proceeds with explicit gap, not silent success
    """
    tasks, _ = build_check_tasks("evals/dataset/pages", "rulesets")
    simulated_missing = {"DEU"}

    run_check_stage(tasks, checker_stub.stub_checker, conn, missing_rulesets=simulated_missing)

    deu_task_ids = [task_id_for(t) for t in tasks if t.jurisdiction == "DEU"]
    other_task_ids = [task_id_for(t) for t in tasks if t.jurisdiction != "DEU"]
    assert deu_task_ids, "fixture expected at least one DEU-targeting task"

    for tid in deu_task_ids:
        assert _latest_state(conn, tid) == ("FAILED", "MISSING_RULESET")

    for tid in other_task_ids:
        state, _ = _latest_state(conn, tid)
        assert state == "DONE"  # other jurisdictions proceed

    findings = get_findings(conn)
    assert not any(f.jurisdiction == "DEU" for f in findings)  # gap is explicit, not silently filled
    assert findings  # aggregation still proceeds using what did complete


def test_fi6_idempotent_rerun(conn):
    """FI-6 | Full re-run on identical input | Idempotent: zero duplicate
    findings/proposals (dedup on content hash + rule_id)
    """
    tasks = [
        CheckTask(
            page_path="p06.html", jurisdiction="MLT", ruleset_version="v1.0",
            assigned_rules=["MLT-PC-01", "MLT-BT-01"],
        )
    ]

    run_check_stage(tasks, checker_stub.stub_checker, conn)
    findings_after_first = get_findings(conn)

    # force=True bypasses resume-skip: proves dedup happens at the storage
    # layer (content_hash + rule_id), not merely because resume skipped it
    run_check_stage(tasks, checker_stub.stub_checker, conn, force=True)
    findings_after_second = get_findings(conn)

    assert len(findings_after_first) == len(findings_after_second) > 0

    done_attempts = conn.execute(
        "SELECT COUNT(*) FROM task_ledger WHERE stage='check' AND state='DONE'"
    ).fetchone()[0]
    assert done_attempts == 2  # ledger honestly logs both attempts happened


def test_fi7_path_escape_and_rule_isolation(conn):
    """FI-7 | Path escape attempt in any agent tool input; checker
    requests another jurisdiction's rule set | Rejected; audit row
    written (extends the verifier's bounds test to all agents +
    rule-isolation check)
    """
    # legitimate same-jurisdiction read is allowed and audited
    rules = read_ruleset("MLT", "MLT", "rulesets", conn)
    assert len(rules) == 8

    with pytest.raises(RuleAccessDenied):
        read_ruleset("MLT", "GBR", "rulesets", conn)  # rule-isolation

    with pytest.raises(RuleAccessDenied):
        read_ruleset("MLT", "../../etc/passwd", "rulesets", conn)  # path escape

    audit_rows = conn.execute(
        "SELECT requesting_jurisdiction, requested_jurisdiction, allowed FROM audit_log ORDER BY id"
    ).fetchall()
    assert audit_rows == [
        ("MLT", "MLT", 1),
        ("MLT", "GBR", 0),
        ("MLT", "../../etc/passwd", 0),
    ]


def test_fi5_conflicting_findings():
    """FI-5 | Conflicting findings on the same excerpt (checker:
    COMPLIANT; verifier: CONTRADICTED -- or two rules colliding) | Task ->
    ESCALATED, surfaced in human queue with both artifacts -- never
    auto-resolved
    """
    pytest.skip("implemented Phase 4 (verifier subprocess node required)")
