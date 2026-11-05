"""Runner and grader for gate v2 (evals/run_eval.py; P2, D2 and D9),
keyless: the sanitized-results allowlist, evidence grading, the D2 miss
rule, each A2 check against a planted fault (planner integrity with the
ABSENT rule both ways), A3 both ways, the storage guard, the result
classes and exit codes, and a stub series on a synthetic holdout that
writes only under holdout_root/runs. Also the human-gate round trip.
No model call; stub agents only.
"""
import hashlib
import json
import re
import sqlite3
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from agents.checker import pages
from agents.planner import stub as planner_stub
from contracts.schemas import CheckTask
from evals import check_holdout
from evals import run_eval as re_
from gate.cli import approve_proposal, list_proposals, reject_proposal
from intake.inventory import load_rulesets
from nodes import verifier_stub
from orchestrator.ledger import create_db
from orchestrator.pipeline import get_findings, run_check_stage, run_plan_stage, run_verify_stage
from tests.test_check_holdout import _build

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = re_.load_eval_config()
RULESETS = load_rulesets(REPO_ROOT / "rulesets")
RULES_BY_ID = {r.rule_id: r for rules in RULESETS.values() for r in rules}


@pytest.fixture(autouse=True)
def _clean():
    yield
    pages.reset_cage()
    verifier_stub.reset_failures()
    planner_stub.reset_failures()


# --------------------------------------------------------------------------
# A small July-page scenario (p01, MLT + GBR) driven through the stubs
# --------------------------------------------------------------------------

ON_PAGE = "100% up to €200 + 50 Free Spins"


def _checker(task):
    out = []
    for r in task.assigned_rules:
        verdict, excerpt = "COMPLIANT", "ABSENT: n/a"
        if r == "GBR-BT-02":
            verdict, excerpt = "VIOLATION", ON_PAGE
        if r == "MLT-BT-01":
            verdict, excerpt = "VIOLATION", "ABSENT: wagering requirement"
        out.append({"page_path": task.page_path, "jurisdiction": task.jurisdiction, "rule_id": r,
                    "ruleset_version": task.ruleset_version, "verdict": verdict, "evidence_excerpt": excerpt,
                    "rationale": "r", "task_id": f"{task.page_path}::{task.jurisdiction}"})
    return out


def _planner(finding):
    payload = planner_stub.stub_planner(finding)
    payload["proposed_text"] = "Add the missing term." if finding.evidence_excerpt.startswith("ABSENT:") else "Paid offer."
    return payload


def _scenario(tmp_path, checker=_checker, planner=_planner):
    july = re_.load_july()
    dataset = replace(july, cases=[c for c in july.cases if c.case_id == "p01"])
    tasks = re_.build_tasks(dataset, RULESETS)
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "ledger.db"
    conn = create_db(str(db_path))
    run_id = "run-test"
    run_check_stage(tasks, checker, conn)
    findings = get_findings(conn)
    run_verify_stage(findings, RULES_BY_ID, verifier_stub.stub_verifier, conn, run_id)
    run_plan_stage(re_._confirmed(conn, findings), planner, conn)
    ctx = re_.RunContext(dataset, CONFIG, 1, run_id, tmp_path, db_path, tmp_path / "audit.db", conn, tasks,
                         RULESETS, RULES_BY_ID, False, False, [])
    return ctx


def _a2(ctx) -> dict[str, dict]:
    return {r["check_name"]: r for r in re_.a2_checks(ctx)}


def test_a2_clean_scenario_passes(tmp_path):
    rows = _a2(_scenario(tmp_path))
    failed = [n for n, r in rows.items() if r["passed"] is False]
    assert failed == []
    assert rows["no_key_or_holdout_marker"]["passed"] is None  # audit-based: not run in stub mode


def _fail(ctx, name):
    row = _a2(ctx)[name]
    assert row["passed"] is False, (name, row)


def test_a2_planted_proposal_for_disputed_finding(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.conn.execute("UPDATE adjudication_log SET verdict = 'DISPUTED' WHERE finding_id LIKE '%GBR-BT-02'")
    ctx.conn.commit()
    _fail(ctx, "planner_proposal_resolves_to_confirmed_finding")


def test_a2_planted_non_pending_status_and_missing_proposal(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.conn.execute("UPDATE proposals SET status = 'APPROVED' WHERE rule_id = 'GBR-BT-02'")
    ctx.conn.commit()
    _fail(ctx, "planner_one_pending_proposal_per_confirmed")
    ctx2 = _scenario(tmp_path / "b")
    ctx2.conn.execute("DELETE FROM proposals WHERE rule_id = 'MLT-BT-01'")
    ctx2.conn.commit()
    _fail(ctx2, "planner_one_pending_proposal_per_confirmed")


def test_a2_planted_offending_text_mismatch(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.conn.execute("UPDATE proposals SET offending_text = 'something else' WHERE rule_id = 'GBR-BT-02'")
    ctx.conn.commit()
    _fail(ctx, "planner_offending_text_equals_excerpt")


def test_a2_absent_rule_both_ways(tmp_path):
    """An ABSENT finding's proposal is an insertion and passes the on-page
    check; a text finding quoting off the page fails it."""
    rows = _a2(_scenario(tmp_path))
    assert rows["planner_offending_text_on_page"]["passed"] is True  # includes the ABSENT insertion

    def off_page_checker(task):
        out = _checker(task)
        for p in out:
            if p["rule_id"] == "GBR-BT-02":
                p["evidence_excerpt"] = "an invented quote that is not on the page"
        return out

    _fail(_scenario(tmp_path / "b", off_page_checker), "planner_offending_text_on_page")


def test_a2_planted_empty_or_unchanged_proposed_text(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.conn.execute("UPDATE proposals SET proposed_text = offending_text WHERE rule_id = 'GBR-BT-02'")
    ctx.conn.commit()
    _fail(ctx, "planner_proposed_text_valid")


def test_a2_planted_uncovered_rule_and_bad_citation(tmp_path):
    ctx = _scenario(tmp_path)
    t0 = ctx.tasks[0]
    ctx.tasks[0] = CheckTask(page_path=t0.page_path, jurisdiction=t0.jurisdiction,
                             ruleset_version=t0.ruleset_version, assigned_rules=t0.assigned_rules[1:])
    _fail(ctx, "coverage_each_rule_in_one_task")
    ctx2 = _scenario(tmp_path / "b")
    ctx2.conn.execute("UPDATE findings SET ruleset_version = 'v1.0' WHERE rule_id = 'GBR-PC-01'")
    ctx2.conn.commit()
    _fail(ctx2, "finding_cites_own_ruleset_and_version")


def test_a2_planted_stuck_and_lost_tasks(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.conn.execute("DELETE FROM task_ledger WHERE task_id = 'p01.html::MLT' AND stage = 'check'")
    ctx.conn.commit()
    rows = _a2(ctx)
    assert rows["every_task_terminal_zero_lost"]["passed"] is False
    assert rows["resume_zero_calls_zero_rows"]["passed"] is False  # the resume rerun had to call the checker
    ctx2 = _scenario(tmp_path / "b")
    ctx2.conn.execute(
        "INSERT INTO task_ledger (task_id, stage, state, attempt) VALUES ('p01.html::GBR', 'plan', 'RUNNING', 2)"
    )
    ctx2.conn.commit()
    _fail(ctx2, "every_task_terminal_zero_lost")


def test_a2_planted_ruleset_hash_mismatch(tmp_path):
    ctx = _scenario(tmp_path)
    ctx.config = {**CONFIG, "datasets": {**CONFIG["datasets"], "ruleset_sha256": {"rulesets/deu-v1.json": "0" * 64}}}
    _fail(ctx, "ruleset_sha256_matches_gate")


def test_a2_audit_checks_in_real_mode(tmp_path, monkeypatch):
    """Audit-based checks (real mode only) catch a missing model call, a
    foreign tool name and a holdout marker; the verifier check is faked."""
    import nodes.verifier as verifier

    monkeypatch.setattr(verifier, "check_verifier_checkout", lambda *a, **k: None)
    ctx = _scenario(tmp_path)
    ctx.real = True
    audit = sqlite3.connect(ctx.audit_db)
    audit.execute("CREATE TABLE tool_calls (id INTEGER PRIMARY KEY, run_id TEXT, task_id TEXT, tool_name TEXT, payload TEXT)")
    audit.execute("INSERT INTO tool_calls (run_id, task_id, tool_name, payload) VALUES (?, 'p01.html::GBR', ?, ?)",
                  (ctx.run_id, "mcp__compliancecheck__fetch_page", json.dumps({"r": "see h7-04"})))
    audit.execute("INSERT INTO tool_calls (run_id, task_id, tool_name, payload) VALUES (?, 'p01.html::GBR', 'Bash', '{}')",
                  (ctx.run_id,))
    audit.commit()
    audit.close()
    rows = _a2(ctx)
    assert rows["independence_model_call_per_task"]["count"] == 1  # p01.html::MLT has no model call
    assert rows["audit_tools_whitelisted"]["passed"] is False
    assert rows["no_key_or_holdout_marker"]["passed"] is False
    assert rows["verifier_pinned_and_clean_after_run"]["passed"] is True


def test_a2_leak_check_also_reads_the_verifier_audit_db(tmp_path, monkeypatch):
    import nodes.verifier as verifier

    monkeypatch.setattr(verifier, "check_verifier_checkout", lambda *a, **k: None)
    ctx = _scenario(tmp_path)
    ctx.real = True
    ctx.leak_markers = ["key.yaml"]
    for db, text in ((ctx.audit_db, "clean"), (tmp_path / "verifier_audit.db", "read key.yaml")):
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE tool_calls (id INTEGER PRIMARY KEY, run_id TEXT, task_id TEXT, tool_name TEXT, payload TEXT)")
        conn.execute("INSERT INTO tool_calls (run_id, task_id, tool_name, payload) VALUES (?, 'p01.html::GBR', "
                     "'mcp__compliancecheck__fetch_page', ?)", (ctx.run_id, json.dumps({"r": text})))
        conn.commit()
        conn.close()
    assert _a2(ctx)["no_key_or_holdout_marker"]["passed"] is False


# --------------------------------------------------------------------------
# RT2-06 clarification (2026-11-03): an A2 line that needs an
# artifact of a task applies to DONE tasks; FAILED tasks (and DEAD_LETTER
# check tasks) are counted as diagnostics instead
# --------------------------------------------------------------------------

def _audit_rows(db, run_id, task_ids):
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tool_calls (id INTEGER PRIMARY KEY, run_id TEXT, task_id TEXT, tool_name TEXT, payload TEXT)")
    for task_id in task_ids:
        conn.execute("INSERT INTO tool_calls (run_id, task_id, tool_name, payload) VALUES (?, ?, "
                     "'mcp__compliancecheck__fetch_page', '{}')", (run_id, task_id))
    conn.commit()
    conn.close()


def _real(ctx, monkeypatch):
    import nodes.verifier as verifier

    monkeypatch.setattr(verifier, "check_verifier_checkout", lambda *a, **k: None)
    ctx.real = True
    return ctx


def _planner_failing_on(rule_id):
    def planner(finding):
        if finding.rule_id == rule_id:
            raise TimeoutError("planner timed out")
        return _planner(finding)
    return planner


def test_rt2_06_failed_plan_task_needs_zero_proposals_and_is_counted(tmp_path):
    rows = _a2(_scenario(tmp_path, planner=_planner_failing_on("MLT-BT-01")))
    assert [n for n, r in rows.items() if r["passed"] is False] == []
    assert rows["planner_one_pending_proposal_per_confirmed"]["count"] == 0
    assert rows["diagnostic_plan_tasks_failed"] == {
        "check_name": "diagnostic_plan_tasks_failed", "run_index": 1, "passed": None, "count": 1}
    assert rows["diagnostic_check_tasks_failed_or_dead_letter"]["count"] == 0


def test_rt2_06_failed_plan_task_with_a_stored_proposal_still_fails(tmp_path):
    ctx = _scenario(tmp_path, planner=_planner_failing_on("MLT-BT-01"))
    ctx.conn.execute(
        "INSERT INTO proposals (content_hash, rule_id, task_id, page_path, offending_text, proposed_text, status, "
        "created_by_run_id, created_at) SELECT 'planted', 'MLT-BT-01', 'p01.html::MLT-BT-01', page_path, "
        "'ABSENT: wagering requirement', 'Add the missing term.', 'PENDING', created_by_run_id, created_at "
        "FROM proposals LIMIT 1")
    ctx.conn.commit()
    _fail(ctx, "planner_one_pending_proposal_per_confirmed")


@pytest.mark.parametrize("planner_result", [None, {}])  # DONE with no proposal; schema DEAD_LETTER
def test_rt2_06_done_or_dead_letter_plan_task_without_proposal_still_fails(tmp_path, planner_result):
    def planner(finding):
        return planner_result if finding.rule_id == "MLT-BT-01" else _planner(finding)

    ctx = _scenario(tmp_path, planner=planner)
    _fail(ctx, "planner_one_pending_proposal_per_confirmed")
    assert _a2(ctx)["diagnostic_plan_tasks_failed"]["count"] == 0


@pytest.mark.parametrize("bad_checker_output", ["raise", "short"])  # FAILED; COVERAGE DEAD_LETTER
def test_rt2_06_independence_skips_failed_check_task_without_audit_rows(tmp_path, monkeypatch, bad_checker_output):
    def checker(task):
        if task.jurisdiction == "MLT":
            if bad_checker_output == "raise":
                raise TimeoutError("checker timed out")
            return _checker(task)[:1]  # one rule short: COVERAGE dead-letter
        return _checker(task)

    ctx = _real(_scenario(tmp_path, checker=checker), monkeypatch)
    _audit_rows(ctx.audit_db, ctx.run_id, ["p01.html::GBR"])
    _audit_rows(tmp_path / "verifier_audit.db", ctx.run_id, ["p01.html::GBR::GBR-BT-02"])
    rows = _a2(ctx)
    assert rows["independence_model_call_per_task"]["passed"] is True
    assert rows["no_key_or_holdout_marker"]["passed"] is True
    assert rows["diagnostic_check_tasks_failed_or_dead_letter"]["count"] == 1


def test_rt2_06_done_check_task_without_audit_rows_still_fails_independence(tmp_path, monkeypatch):
    ctx = _real(_scenario(tmp_path), monkeypatch)
    _audit_rows(ctx.audit_db, ctx.run_id, ["p01.html::GBR"])  # p01.html::MLT is DONE with no audit row
    _audit_rows(tmp_path / "verifier_audit.db", ctx.run_id, ["p01.html::GBR::GBR-BT-02"])
    _fail(ctx, "independence_model_call_per_task")


def test_rt2_06_missing_audit_trail_fails_only_when_a_done_task_should_have_one(tmp_path, monkeypatch):
    # verify tasks are DONE but the verifier audit DB is missing: an audit gap
    ctx = _real(_scenario(tmp_path / "a"), monkeypatch)
    _audit_rows(ctx.audit_db, ctx.run_id, ["p01.html::GBR", "p01.html::MLT"])
    _fail(ctx, "no_key_or_holdout_marker")
    # the verifier DB exists but holds no rows for this run, with DONE verify tasks: also a gap
    _audit_rows(tmp_path / "a" / "verifier_audit.db", ctx.run_id, [])
    _fail(ctx, "no_key_or_holdout_marker")

    # no VIOLATION, so no verify task ran: a missing verifier DB is not a gap
    def compliant(task):
        return [{**p, "verdict": "COMPLIANT", "evidence_excerpt": "ABSENT: n/a"} for p in _checker(task)]

    ctx2 = _real(_scenario(tmp_path / "b", checker=compliant), monkeypatch)
    _audit_rows(ctx2.audit_db, ctx2.run_id, ["p01.html::GBR", "p01.html::MLT"])
    assert _a2(ctx2)["no_key_or_holdout_marker"]["passed"] is True

    # DONE check tasks but no checker/planner audit rows at all: a gap
    ctx3 = _real(_scenario(tmp_path / "c", checker=compliant), monkeypatch)
    _audit_rows(ctx3.audit_db, ctx3.run_id, [])
    _fail(ctx3, "no_key_or_holdout_marker")


# --------------------------------------------------------------------------
# D1 decision (2026-11-03): real runs use the subscription login only
# --------------------------------------------------------------------------

SUBSCRIPTION = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "max"}


def test_d1_subscription_guard():
    def problem(env, status):
        return re_.subscription_auth(env, auth_status=lambda: status)[0]

    assert re_.subscription_auth({}, auth_status=lambda: {**SUBSCRIPTION, "email": "someone@example.invalid"}) == (
        None, {"auth_method": "claude.ai", "api_provider": "firstParty", "subscription_type": "max"})  # never the email
    refused = problem({"ANTHROPIC_API_KEY": "placeholder-value"}, SUBSCRIPTION)
    assert "ANTHROPIC_API_KEY" in refused and "placeholder-value" not in refused
    assert problem({"CLAUDE_CODE_USE_VERTEX": "1"}, SUBSCRIPTION)
    for method in ("api_key", "api_key_helper", "oauth_token", "third_party", "none"):
        assert problem({}, {**SUBSCRIPTION, "authMethod": method})
    assert problem({}, {**SUBSCRIPTION, "apiProvider": "bedrock"})
    assert problem({}, {**SUBSCRIPTION, "loggedIn": False})

    def broken():
        raise FileNotFoundError("no CLI")
    assert "not confirmed" in re_.subscription_auth({}, auth_status=broken)[0]


def test_d1_auth_facts_recorded_privately_beside_the_results(tmp_path):
    root = _build(tmp_path)
    mdir = _manifest(tmp_path, root)
    page = root / "pages" / "h9-05.html"
    page.write_text(page.read_text(encoding="utf-8") + " ", encoding="utf-8")  # fast path: INVALID RUN
    facts = {"auth_method": "claude.ai", "api_provider": "firstParty", "subscription_type": "max"}
    _result, results, out = re_.run_series("H9", tmp_path, runs=1, manifest_dir=mdir,
                                           results_dir=tmp_path / "results", auth=facts)
    assert json.loads((out.parent / "auth.json").read_text(encoding="utf-8")) == facts
    assert out.parent.is_relative_to(tmp_path / "runs")  # private run directory, never Git
    assert "auth_method" not in results["series"]  # the frozen results allowlist is unchanged


def test_d1_real_run_refused_before_any_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-value")
    assert re_.main(["--dataset", "july", "--real", "--holdout-root", str(tmp_path)]) == re_.EXIT_USAGE
    out = capsys.readouterr().out
    assert "REFUSED" in out and "placeholder-value" not in out
    assert not (tmp_path / "runs").exists()


# --------------------------------------------------------------------------
# --page (2026-11-03): one July development page, never gated or a holdout
# --------------------------------------------------------------------------

def test_page_selects_exactly_one_july_page(tmp_path):
    result, results, out = re_.run_series("july", tmp_path, runs=1, page="p01")
    assert result in (re_.PASS, re_.FAIL)
    assert {r["case_id"] for r in results["per_case"]} == {"p01"}
    assert {r["case_id"] for r in results["per_page_off_target"]} == {"p01"}
    assert out.is_relative_to(tmp_path / "runs" / "july")
    ledger = sqlite3.connect(next((tmp_path / "runs").rglob("ledger.db")))
    try:
        checked = {r[0] for r in ledger.execute("SELECT DISTINCT task_id FROM task_ledger WHERE stage = 'check'")}
    finally:
        ledger.close()
    assert checked == {"p01.html::GBR", "p01.html::MLT"}  # only p01's markets ran


@pytest.mark.parametrize("dataset,gated", [("H9", False), ("H2", False), ("H9", True), ("july", True)])
def test_page_refused_with_gated_or_a_holdout(tmp_path, dataset, gated):
    with pytest.raises(ValueError, match="--page|never gated"):
        re_.run_series(dataset, tmp_path, page="p01", gated=gated)
    assert not (tmp_path / "runs").exists()


def test_page_unknown_id_refused(tmp_path):
    with pytest.raises(ValueError, match="unknown July page"):
        re_.run_series("july", tmp_path, page="p99")
    assert re_.main(["--dataset", "july", "--page", "h2-01", "--holdout-root", str(tmp_path)]) == re_.EXIT_USAGE
    assert re_.main(["--dataset", "H2", "--page", "p01", "--holdout-root", str(tmp_path)]) == re_.EXIT_USAGE
    assert not (tmp_path / "runs").exists()


def test_page_omitted_keeps_all_july_pages(tmp_path, monkeypatch):
    seen = {}

    def run_once(ctx, model):
        seen["pages"] = sorted({t.page_path for t in ctx.tasks})
        raise re_.InvalidRun("stop after task building")  # no need to run the stages

    monkeypatch.setattr(re_, "run_once", run_once)
    re_.run_series("july", tmp_path, runs=1)
    assert seen["pages"] == sorted(c.page_name for c in re_.load_july().cases) and len(seen["pages"]) == 12


# --------------------------------------------------------------------------
# B: evidence grading, primary decision, D2 miss rule
# --------------------------------------------------------------------------

PAGE = re_.normalize("Welcome. 100% up to €200 + 50 Free Spins. Spins credited after first deposit. Footer text.")
CORE = "100% up to €200 + 50 Free Spins"


@pytest.mark.parametrize("excerpt,expected", [
    ("100% up to €200 + 50 Free Spins", None),
    ("“€200 + 50 Free Spins” ... Spins credited after first deposit", None),
    ("“50 Free Spins” ... Spins credited after first deposit", "NO_OVERLAP"),  # 13 shared chars < 15
    ("not on this page", "OFF_PAGE"),
    ("Spins credited after first deposit", "NO_OVERLAP"),
    ("ABSENT: deposit condition", "ABSENT_ON_TEXT"),
])
def test_grade_evidence_categories(excerpt, expected):
    assert re_.grade_evidence(excerpt, CORE, PAGE) == expected


def test_grade_evidence_too_long():
    page = re_.normalize("x " * 300 + CORE)
    assert re_.grade_evidence(re_.normalize("x " * 120 + CORE), CORE, page) == "TOO_LONG"


def _case(etype, expected="VIOLATION"):
    primary = {"rule_id": "GBR-BT-02", "expected": expected, "evidence_type": etype, "spans": [CORE]}
    return re_.Case("c1", "page01.html", Path("x"), ["GBR"], {"GBR-BT-02": expected}, primary)


@pytest.mark.parametrize("case,cell,expected", [
    (_case("text"), None, "NOT_DECIDED"),
    (_case("text"), re_.CellOutcome(False, False, None, None, None), "NOT_DECIDED"),
    (_case("text"), re_.CellOutcome(True, False, "VIOLATION", "DISPUTED", CORE), "DISPUTED"),
    (_case("text"), re_.CellOutcome(True, False, "COMPLIANT", None, CORE), "NOT_ASSERTED"),
    (_case("text"), re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", CORE), None),
    (_case("text"), re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", "ABSENT: x"), "ABSENT_ON_TEXT"),
    (_case("missing_term"), re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", "ABSENT: expiry"), None),
    (_case("absent"), re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", "anything"), None),
    (_case("none", "COMPLIANT"), re_.CellOutcome(True, False, "COMPLIANT", None, "x"), None),
    (_case("none", "NOT_APPLICABLE"), re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", "x"), "ASSERTED_ON_NON_VIOLATION"),
])
def test_primary_decision(case, cell, expected):
    assert re_.primary_miss(case, cell, PAGE) == expected


def test_d2_failed_or_missing_cells_count_as_misses(tmp_path):
    """D2: a FAILED check task leaves its cells undecided; the primary is
    a miss and every key violation there counts as FN, never 'unscored'."""
    def boom(_task):
        raise TimeoutError("t")

    ctx = _scenario(tmp_path, checker=boom)
    cells = re_.cell_outcomes(ctx.conn, ctx.tasks)
    assert all(not c.decided for c in cells.values())
    scored = re_.score_series(ctx.dataset, [{"cells": cells, "cost_usd": 0, "turns": 0, "wall_clock_s": 0}] * 3, CONFIG)
    assert scored["per_case"][0]["miss_category"] == "NOT_DECIDED"
    key_violations = sum(v == "VIOLATION" for v in ctx.dataset.cases[0].cells.values())
    assert scored["aggregates"]["fn"] == 3 * key_violations
    assert scored["per_page_off_target"][0]["undecided_cells"] == len(ctx.dataset.cases[0].cells) - 1


def test_off_target_repeated_vs_one_off(monkeypatch):
    case = _case("text")
    case.cells = {"GBR-BT-02": "VIOLATION", "GBR-PC-01": "COMPLIANT", "GBR-PC-02": "COMPLIANT"}
    ok = re_.CellOutcome(True, False, "COMPLIANT", None, "x")
    alarm = re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", "x")
    primary = re_.CellOutcome(True, True, "VIOLATION", "CONFIRMED", CORE)
    runs = [
        {"cells": {("page01.html", "GBR-BT-02"): primary, ("page01.html", "GBR-PC-01"): alarm, ("page01.html", "GBR-PC-02"): alarm}},
        {"cells": {("page01.html", "GBR-BT-02"): primary, ("page01.html", "GBR-PC-01"): alarm, ("page01.html", "GBR-PC-02"): ok}},
        {"cells": {("page01.html", "GBR-BT-02"): primary, ("page01.html", "GBR-PC-01"): ok, ("page01.html", "GBR-PC-02"): ok}},
    ]
    for r in runs:
        r.update(cost_usd=0, turns=0, wall_clock_s=0)
    case.file = Path(__file__)  # any readable file; the page text is replaced below
    monkeypatch.setattr(re_, "visible_text", lambda _html: PAGE)
    scored = re_.score_series(re_.Dataset("x", True, Path("."), [case]), runs, CONFIG)
    page = scored["per_page_off_target"][0]
    assert page["unclean"] is True and page["false_alarm_cells"] == 1 and page["one_off_error_cells"] == 1
    assert scored["aggregates"]["cases_failed"] == 0


# --------------------------------------------------------------------------
# A3 both ways, on a synthetic holdout
# --------------------------------------------------------------------------


def test_a3_passes_true_absence_and_flags_present_content(tmp_path):
    root = _build(tmp_path)
    dataset = re_.load_holdout(tmp_path, "H9")
    pages.configure_cage(dataset.pages_dir, dataset.aliases)
    assert all(r["passed"] for r in re_.a3_checks(dataset))
    page = root / "pages" / "h9-01.html"  # case 0 is absent-type
    page.write_text(page.read_text(encoding="utf-8").replace("</footer>", "<p>required notice 0</p></footer>"), encoding="utf-8")
    rows = {r["check_name"]: r for r in re_.a3_checks(dataset)}
    assert rows["a3_absent_content_not_in_reader"]["count"] == 1


# --------------------------------------------------------------------------
# Sanitized results allowlist
# --------------------------------------------------------------------------


def _results():
    return {
        "series": {"series_id": "s", "result": "PASS"},
        "component_a": [{"check_name": "x", "run_index": 1, "passed": True, "count": 0}],
        "per_case": [{"case_id": "h9-01", "jurisdiction": "GBR", "rule_id": "GBR-BT-02", "run_index": 1,
                      "passed": False, "miss_category": "OFF_PAGE"}],
        "per_page_off_target": [{"case_id": "h9-01", "unclean": False, "false_alarm_cells": 0, "missed_cells": 0,
                                 "undecided_cells": 0, "one_off_error_cells": 0}],
        "aggregates": {"tp": 1},
    }


def test_sanitized_allowlist_accepts_allowed_fields():
    re_.sanitize(_results(), CONFIG)


@pytest.mark.parametrize("plant", [
    lambda r: r["series"].update(page_text="x"),
    lambda r: r["per_case"][0].update(evidence_excerpt="x"),
    lambda r: r["per_case"][0].update(miss_category="SOMETHING"),
    lambda r: r["per_page_off_target"][0].update(missed_cells=["GBR-PC-01"]),
    lambda r: r["aggregates"].update(rationale="x"),
    lambda r: r.update(pages={}),
])
def test_sanitized_allowlist_rejects_extra_content(plant):
    r = _results()
    plant(r)
    with pytest.raises(ValueError):
        re_.sanitize(r, CONFIG)


# --------------------------------------------------------------------------
# Storage guard, result classes, exit codes, stub holdout series
# --------------------------------------------------------------------------


def test_storage_guard_refuses_repo_holdout_and_outside_runs(tmp_path):
    (tmp_path / "H9").mkdir()
    holdouts = re_.holdout_folders(tmp_path)
    with pytest.raises(re_.StorageError):
        re_.guard_output_path(REPO_ROOT / "runs" / "x", tmp_path, holdouts)
    with pytest.raises(re_.StorageError):
        re_.guard_output_path(tmp_path / "H9" / "runs", tmp_path, holdouts)
    with pytest.raises(re_.StorageError):
        re_.guard_output_path(tmp_path / "elsewhere", tmp_path, holdouts)
    assert re_.guard_output_path(tmp_path / "runs" / "H9" / "s", tmp_path, holdouts)
    with pytest.raises(re_.StorageError):
        re_.run_series("july", REPO_ROOT, runs=1)  # holdout_root inside the repo


def _hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _git_status() -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout


def _manifest(tmp_path, root) -> Path:
    mdir = tmp_path / "manifests"
    mdir.mkdir(exist_ok=True)
    (mdir / "H9.sha256").write_text("\n".join(check_holdout.manifest_lines(root, False)) + "\n", encoding="utf-8")
    return mdir


def test_stub_holdout_series_writes_only_under_runs(tmp_path):
    root = _build(tmp_path)
    mdir = _manifest(tmp_path, root)
    before_holdout, before_git = _hashes(root), _git_status()
    result, results, out = re_.run_series("H9", tmp_path, runs=2, manifest_dir=mdir, results_dir=tmp_path / "results")
    assert result in (re_.PASS, re_.FAIL) and results["series"]["exit_code"] == 0
    assert _hashes(root) == before_holdout  # nothing changed in the holdout
    assert _git_status() == before_git  # nothing new in the repository
    written = [p for p in tmp_path.rglob("*") if p.is_file() and not p.is_relative_to(root) and not p.is_relative_to(mdir)]
    assert written and all(p.is_relative_to(tmp_path / "runs" / "H9") for p in written)
    assert out.is_relative_to(tmp_path / "runs")  # not gated: results stay private
    # agents saw neutral names only: no case ID in any ledger row
    for db in (tmp_path / "runs").rglob("ledger.db"):
        conn = sqlite3.connect(db)
        dump = "\n".join(conn.iterdump())
        conn.close()
        assert not re.search(re_.CASE_ID_PATTERN, dump)
    assert all(r["passed"] for r in results["component_a"] if r["check_name"].startswith("a3_"))


def test_manifest_mismatch_is_invalid_run(tmp_path):
    root = _build(tmp_path)
    mdir = _manifest(tmp_path, root)
    page = root / "pages" / "h9-05.html"
    page.write_text(page.read_text(encoding="utf-8") + " ", encoding="utf-8")
    result, results, _ = re_.run_series("H9", tmp_path, runs=1, manifest_dir=mdir, results_dir=tmp_path / "results")
    assert result == re_.INVALID_RUN and results["series"]["exit_code"] == re_.EXIT_INVALID_RUN != 0


def test_self_check_failure_is_not_enough_cases(tmp_path):
    def drop(root, key):
        key["pages"].pop("h9-30")
        (root / "pages" / "h9-30.html").unlink()

    root = _build(tmp_path, drop)
    mdir = _manifest(tmp_path, root)
    result, results, _ = re_.run_series("H9", tmp_path, runs=1, manifest_dir=mdir, results_dir=tmp_path / "results")
    assert result == re_.NOT_ENOUGH_CASES and results["series"]["exit_code"] == re_.EXIT_NOT_ENOUGH_CASES != 0


def test_cli_usage_errors():
    assert re_.main(["--dataset", "july", "--gated"]) == re_.EXIT_USAGE
    assert re_.main(["--dataset", "nope", "--holdout-root", "x"]) == re_.EXIT_USAGE


# --------------------------------------------------------------------------
# Human gate (A1 must_include): round trip, idempotent, no planner path
# --------------------------------------------------------------------------


def test_human_gate_round_trip_idempotent_and_no_planner_path(tmp_path):
    ctx = _scenario(tmp_path)
    proposals = list_proposals(ctx.conn)
    assert len(proposals) == 2 and {p["status"] for p in proposals} == {"PENDING"}
    first, second = proposals[0]["id"], proposals[1]["id"]
    assert approve_proposal(ctx.conn, first).endswith("APPROVED")
    assert "no-op" in approve_proposal(ctx.conn, first)
    assert "no-op" in reject_proposal(ctx.conn, first)
    assert reject_proposal(ctx.conn, second).endswith("REJECTED")
    statuses = {p["id"]: p["status"] for p in list_proposals(ctx.conn)}
    assert statuses == {first: "APPROVED", second: "REJECTED"}
    rows = _a2(ctx)
    assert rows["planner_no_status_tool"]["passed"] is True
    assert rows["planner_one_pending_proposal_per_confirmed"]["passed"] is False  # decided proposals are not PENDING
