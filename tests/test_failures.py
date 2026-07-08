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
from contracts.schemas import CheckTask, ComplianceRule, RuleCategory, Severity, Verdict, ViolationFinding
from intake.inventory import RuleAccessDenied, build_check_tasks, read_ruleset
from nodes import verifier_stub
from orchestrator.aggregation import build_adjudication_report
from orchestrator.ledger import create_db
from orchestrator.pipeline import (
    finding_id_for,
    get_adjudications,
    get_confirmed_findings,
    get_findings,
    register_tasks,
    run_check_stage,
    run_verify_stage,
    task_id_for,
)


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


def test_adjudication_log_append_only_no_overwrite(conn):
    """policy/ADJUDICATION_POLICY.md §6: "a finding's assertion status
    changes only through an adjudication row" -- no code path may ever
    update or delete one. Proven directly at the storage layer
    (UNIQUE(finding_id) + INSERT OR IGNORE, orchestrator.pipeline.
    insert_adjudication): a second insert attempt for the same
    finding_id, even carrying a different verdict, is silently ignored
    -- the original row's verdict is what's actually stored. This is
    the same guarantee test_fi5_conflicting_findings exercises through
    a full run_verify_stage re-run; here it's isolated to the single
    storage primitive so a future change to that call site can't hide a
    regression behind the higher-level test's other assertions.
    """
    from datetime import datetime, timezone

    from contracts.schemas import AdjudicationRecord
    from orchestrator.pipeline import get_adjudications, insert_adjudication

    first = AdjudicationRecord(
        finding_id="p01.html::MLT::MLT-BT-01", verdict="CONFIRMED",
        citation="stub: bright-line criterion met, evidence verified",
        model="stub-verifier-v1", timestamp=datetime.now(timezone.utc), run_id="overwrite-test",
    )
    conflicting_second = AdjudicationRecord(
        finding_id="p01.html::MLT::MLT-BT-01", verdict="REJECTED",
        citation="stub: evidence fails the cited bright-line criterion",
        model="stub-verifier-v1", timestamp=datetime.now(timezone.utc), run_id="overwrite-test-2",
    )

    assert insert_adjudication(conn, first) is True
    assert insert_adjudication(conn, conflicting_second) is False  # ignored, not applied

    rows = get_adjudications(conn)
    assert len(rows) == 1  # no second row, no overwritten row
    assert rows[0].verdict.value == "CONFIRMED"  # the original verdict stands
    assert rows[0].run_id == "overwrite-test"


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


def test_fi5_conflicting_findings(conn):
    """FI-5 | Conflicting findings on the same excerpt (checker:
    COMPLIANT; verifier: CONTRADICTED -- or two rules colliding) | Task ->
    ESCALATED, surfaced in human queue with both artifacts -- never
    auto-resolved

    SUPERSEDED (policy/ADJUDICATION_POLICY.md §7): BLUEPRINT.md §6's
    original FI-5 wording predates the adjudication policy and describes
    a checker-vs-checker/verifier tie the orchestrator itself referees.
    Under the policy, the "conflict" is the verifier adjudicating a
    checker VIOLATION finding to REJECTED or DISPUTED. This test scripts
    one of each, on two different tasks, to prove both halves of the
    TaskState mapping (policy §11) in one pass: rejected-only -> DONE,
    any DISPUTED -> ESCALATED -- never auto-resolved to a single verdict,
    both positions retained in the ledger.
    """
    verifier_stub.reset_failures()

    rejected_finding = ViolationFinding(
        page_path="p01.html", jurisdiction="MLT", rule_id="MLT-BT-01",
        ruleset_version="v1.0", verdict=Verdict.VIOLATION,
        evidence_excerpt="wagering text not adjacent to offer",
        rationale="stub fixture rationale: adjacency check",
        task_id="p01.html::MLT",
    )
    disputed_finding = ViolationFinding(
        page_path="p06.html", jurisdiction="MLT", rule_id="MLT-PC-01",
        ruleset_version="v1.0", verdict=Verdict.VIOLATION,
        evidence_excerpt="guarantee-adjacent wording",
        rationale="stub fixture rationale: prohibited-claims check",
        task_id="p06.html::MLT",
    )
    rules_by_id = {
        "MLT-BT-01": ComplianceRule(
            jurisdiction="MLT", rule_id="MLT-BT-01", category=RuleCategory.BONUS_TERMS,
            severity=Severity.MAJOR, rule_text="Wagering requirements must be adjacent to the offer.",
            ruleset_version="v1.0",
        ),
        "MLT-PC-01": ComplianceRule(
            jurisdiction="MLT", rule_id="MLT-PC-01", category=RuleCategory.PROHIBITED_CLAIMS,
            severity=Severity.CRITICAL, rule_text="No guaranteed-win language.",
            ruleset_version="v1.0",
        ),
    }
    findings = [rejected_finding, disputed_finding]

    verifier_stub.configure_verdict(finding_id_for(rejected_finding), "REJECTED")
    verifier_stub.configure_verdict(finding_id_for(disputed_finding), "DISPUTED")

    run_verify_stage(findings, rules_by_id, verifier_stub.stub_verifier, conn, run_id="fi5-test")

    # both positions in ledger, each citing its verdict (no naked rejection)
    adjs = {a.finding_id: a for a in get_adjudications(conn)}
    assert adjs[finding_id_for(rejected_finding)].verdict.value == "REJECTED"
    assert adjs[finding_id_for(disputed_finding)].verdict.value == "DISPUTED"
    assert adjs[finding_id_for(rejected_finding)].citation
    assert adjs[finding_id_for(disputed_finding)].citation

    # disputed row in the report's disputed section
    report = build_adjudication_report(get_adjudications(conn))
    assert finding_id_for(disputed_finding) in [r.finding_id for r in report["disputed"]]
    assert finding_id_for(rejected_finding) in [r.finding_id for r in report["rejected"]]
    assert finding_id_for(rejected_finding) not in [r.finding_id for r in report["disputed"]]
    assert finding_id_for(disputed_finding) not in [r.finding_id for r in report["rejected"]]

    # rejected row excluded from assertions; disputed is too (policy §5)
    confirmed_ids = {finding_id_for(f) for f in get_confirmed_findings(conn)}
    assert finding_id_for(rejected_finding) not in confirmed_ids
    assert finding_id_for(disputed_finding) not in confirmed_ids

    # task ESCALATED per (iii): rejected-only -> DONE, any DISPUTED -> ESCALATED
    def _verify_state(task_id):
        row = conn.execute(
            "SELECT state FROM task_ledger WHERE task_id = ? AND stage = 'verify' ORDER BY id DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return row[0]

    assert _verify_state(rejected_finding.task_id) == "DONE"
    assert _verify_state(disputed_finding.task_id) == "ESCALATED"

    # idempotent re-run (including force=True, FI-6 style): nothing overwritten
    run_verify_stage(findings, rules_by_id, verifier_stub.stub_verifier, conn, run_id="fi5-test", force=True)

    adjs_after = get_adjudications(conn)
    assert len(adjs_after) == 2  # no duplicate rows
    adjs_after_by_id = {a.finding_id: a for a in adjs_after}
    assert adjs_after_by_id[finding_id_for(rejected_finding)].verdict.value == "REJECTED"
    assert adjs_after_by_id[finding_id_for(disputed_finding)].verdict.value == "DISPUTED"

    terminal_attempts = conn.execute(
        "SELECT COUNT(*) FROM task_ledger WHERE stage='verify' AND state IN ('DONE','ESCALATED')"
    ).fetchone()[0]
    assert terminal_attempts == 4  # 2 tasks x 2 terminal attempts each -- ledger honestly logs both runs
