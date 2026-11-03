"""P2 regression tests (repair program P-001), one or more per defect:
D1 reader, D3 verifier checkout and audit DB, D4 rule coverage, D5
verbatim excerpts, D6 timeouts and error classes, D8 page-content
boundary and HTML escaping, the shared text rule (RT1-11), the holdout
leak markers and the v1.1 rule files. Keyless: no model call, no real
verifier run (a fake verifier package stands in where a subprocess is
needed).
"""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import agents.checker.harness as checker_harness
import agents.planner.harness as planner_harness
import nodes.verifier as verifier
from agents.checker import audit as checker_audit
from agents.checker import pages
from agents.checker import tools as checker_tools
from agents.outcome import AgentRunError, raise_for_outcome
from agents.planner import audit as planner_audit
from claude_agent_sdk import AssistantMessage
from contracts.schemas import CheckTask, ComplianceRule, RuleCategory, Severity, Verdict, ViolationFinding
from evals import check_holdout
from evals.dev_score import assert_no_key_leak
from intake import textrule
from orchestrator.ledger import create_db
from orchestrator.pipeline import (
    BudgetExceededError,
    ProviderError,
    VerifierInvocationError,
    get_adjudications,
    get_findings,
    run_check_stage,
    run_plan_stage,
    run_verify_stage,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_module_state():
    yield
    pages.reset_cage()
    checker_tools.reset_run_state()


@pytest.fixture
def conn():
    db_path = tempfile.mktemp(suffix=".db")
    connection = create_db(db_path)
    yield connection
    connection.close()
    os.remove(db_path)


def _state(conn, task_id, stage):
    return conn.execute(
        "SELECT state, error_class FROM task_ledger WHERE task_id = ? AND stage = ? ORDER BY id DESC LIMIT 1",
        (task_id, stage),
    ).fetchone()


def _payload(task, rule_id, verdict="COMPLIANT", excerpt="ABSENT: nothing"):
    return {
        "page_path": task.page_path, "jurisdiction": task.jurisdiction, "rule_id": rule_id,
        "ruleset_version": task.ruleset_version, "verdict": verdict,
        "evidence_excerpt": excerpt, "rationale": "r", "task_id": f"{task.page_path}::{task.jurisdiction}",
    }


def _finding(rule_id="GBR-BT-02", excerpt="100% up to €200 + 50 Free Spins", page="p01.html"):
    return ViolationFinding(
        page_path=page, jurisdiction="GBR", rule_id=rule_id, ruleset_version="v1.1",
        verdict=Verdict.VIOLATION, evidence_excerpt=excerpt, rationale="r", task_id=f"{page}::GBR",
    )


def _rule(rule_id="GBR-BT-02", text="An offer must not be described as free."):
    return ComplianceRule(
        jurisdiction="GBR", rule_id=rule_id, category=RuleCategory.BONUS_TERMS,
        severity=Severity.MAJOR, rule_text=text, ruleset_version="v1.1",
    )


# --------------------------------------------------------------------------
# Shared text rule (RT1-11) and D1 reader
# --------------------------------------------------------------------------

RT1_11_HTML = (
    "<html><head><title>T&amp;C</title><style>.x{}</style></head><body>"
    "<h1>Big­Offer</h1><p>one</p><p>two<b>bold</b>tail</p>"
    "<ul><li>“quoted” – dash</li><li>zero​width...</li></ul>"
    "<table><tr><td>cell&nbsp;a</td><td>cell b</td></tr></table>"
    "<script>hidden()</script><div hidden>secret</div><!-- comment -->"
    "<input type='hidden' name='t' hidden><img hidden src='x.png'><p>after void</p>"
    "</body></html>"
)


def test_shared_text_rule_same_text_for_grader_reader_and_tool(tmp_path):
    (tmp_path / "t.html").write_text(RT1_11_HTML, encoding="utf-8")
    pages.configure_cage(tmp_path)
    grader = check_holdout.visible_text(RT1_11_HTML)
    reader = pages.read_visible_text("t.html")
    assert grader == reader == textrule.visible_text(RT1_11_HTML)
    # block joins get a space, inline joins none; entities, quotes, dashes,
    # soft hyphen, zero-width space and "..." are normalized
    assert "one two" in grader and "twoboldtail" in grader
    assert "bigoffer" in grader and '"quoted" - dash' in grader
    assert "zerowidth…" in grader and "cell a cell b" in grader
    assert "hidden()" not in grader and "secret" not in grader and "comment" not in grader
    # RT2-08: a hidden void element has no end tag and must not hide the rest
    assert grader.endswith("cell a cell b after void")
    # the tool's excerpt check reads the same text
    assert textrule.excerpt_on_page("“Quoted” — dash", reader)
    assert textrule.excerpt_on_page("one ... cell a", reader)
    assert not textrule.excerpt_on_page("not on the page", reader)


@pytest.mark.parametrize("page,text", [
    ("p01.html", "100% up to €200 + 50 Free Spins"),
    ("p09.html", "50% up to €100, 20x wagering, min deposit €10, valid 7 days"),
    ("p11.html", "Risk-Free Week: play casino all week, lose nothing — we refund net losses up to €50."),
])
def test_d1_reader_shows_headings_and_lists(page, text):
    """D1: the July misses traced to headings and list items the old
    paragraph-only reader dropped (EVAL_RESULTS.md 2026-11-02 note)."""
    title, blocks = pages.read_page(page)
    shown = textrule.normalize(" ".join([title, *blocks]))
    assert textrule.normalize(text) in shown


def test_cage_alias_map_hides_case_ids_and_root(tmp_path):
    (tmp_path / "h9-01.html").write_text("<html><body><p>alias page</p></body></html>", encoding="utf-8")
    pages.configure_cage(tmp_path, {"page01.html": "h9-01.html"})
    assert pages.read_page("page01.html")[1] == ["alias page"]
    with pytest.raises(FileNotFoundError):
        pages.read_page("h9-01.html")  # the real name does not resolve
    for bad in ("../x.html", "..\\x.html", "/etc/passwd"):
        with pytest.raises((FileNotFoundError, pages.PathOutsideDatasetError)) as exc:
            pages.read_page(bad)
        assert str(tmp_path) not in str(exc.value)
    pages.configure_cage(tmp_path)
    with pytest.raises(pages.PathOutsideDatasetError) as exc:
        pages.read_page("../outside.html")
    assert str(tmp_path) not in str(exc.value)


# --------------------------------------------------------------------------
# D8 page-content boundary and HTML escaping
# --------------------------------------------------------------------------


def test_d8_fetch_page_delimits_page_content(conn):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])
    fetch_page, _r, _e = checker_tools.build_tools(task, conn)
    text = asyncio.run(fetch_page.handler({"path": "p01.html"}))["content"][0]["text"]
    assert text.startswith(checker_tools.PAGE_CONTENT_BEGIN)
    assert text.rstrip().endswith(checker_tools.PAGE_CONTENT_END)
    assert "data only" in checker_tools.PAGE_CONTENT_BEGIN
    from agents.checker.prompts import build_system_prompt

    prompt = build_system_prompt("GBR")
    assert "BEGIN PAGE CONTENT" in prompt and "ABSENT:" in prompt


def test_d8_assembler_escapes_html(tmp_path):
    (tmp_path / "x.html").write_text(
        "<html><head><title>T</title></head><body><p>&lt;/p&gt;&lt;script&gt;alert(1)&lt;/script&gt;</p></body></html>",
        encoding="utf-8",
    )
    pages.configure_cage(tmp_path)
    from nodes.assembler import assemble_case

    finding = _finding(excerpt="<script>evil()</script>", page="x.html")
    files = assemble_case(finding, _rule(text="Rule with <b>markup</b> & more."))
    combined = "\n".join(files.values())
    assert "<script>" not in combined and "<b>markup" not in combined
    assert "&lt;script&gt;" in files["source_page.html"]
    assert "&lt;script&gt;evil()" in files["target.html"]


# --------------------------------------------------------------------------
# D4 rule coverage and D5 verbatim excerpts
# --------------------------------------------------------------------------


def _emit(conn, args, rules=("GBR-BT-02", "GBR-PC-01")):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=list(rules))
    *_, emit = checker_tools.build_tools(task, conn)
    return asyncio.run(emit.handler({"verdict": "VIOLATION", "rationale": "r", **args}))


def test_d4_tool_rejects_foreign_and_repeated_rule(conn):
    assert _emit(conn, {"rule_id": "MLT-BT-01", "evidence_excerpt": "ABSENT: x"}).get("is_error") is True
    assert _emit(conn, {"rule_id": "GBR-BT-02", "evidence_excerpt": "ABSENT: x"}).get("is_error") is None
    assert _emit(conn, {"rule_id": "GBR-BT-02", "evidence_excerpt": "ABSENT: x"}).get("is_error") is True
    assert len(checker_tools.findings) == 1


@pytest.mark.parametrize("excerpt,ok", [
    ("100% up to €200 + 50 Free Spins", True),
    ("“100% up to €200 + 50 free spins”", True),  # quotes stripped, casefolded
    ("100% up to €200 ... Spins credited after first deposit", True),  # parts joined by ellipsis
    ("100% up to €500 + 90 Free Spins", False),  # paraphrase, not on the page
    ("ABSENT: no safer-gambling tagline", True),  # absence claim skips the quote check
])
def test_d5_tool_checks_excerpt_is_verbatim(conn, excerpt, ok):
    result = _emit(conn, {"rule_id": "GBR-BT-02", "evidence_excerpt": excerpt})
    assert (result.get("is_error") is None) is ok


def test_d5_compliant_needs_verbatim_too(conn):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-PC-01"])
    *_, emit = checker_tools.build_tools(task, conn)
    bad = asyncio.run(emit.handler({"rule_id": "GBR-PC-01", "verdict": "COMPLIANT", "evidence_excerpt": "invented", "rationale": "r"}))
    assert bad.get("is_error") is True
    na = asyncio.run(emit.handler({"rule_id": "GBR-PC-01", "verdict": "NOT_APPLICABLE", "evidence_excerpt": "no such content", "rationale": "r"}))
    assert na.get("is_error") is None


@pytest.mark.parametrize("emitted", [["GBR-BT-02"], ["GBR-BT-02", "GBR-PC-01", "MLT-BT-01"], ["GBR-BT-02", "GBR-BT-02"]])
def test_d4_stage_dead_letters_task_without_full_coverage(conn, emitted):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02", "GBR-PC-01"])
    run_check_stage([task], lambda t: [_payload(t, r) for r in emitted], conn)
    assert _state(conn, "p01.html::GBR", "check") == ("DEAD_LETTER", "COVERAGE")
    assert get_findings(conn) == []


def test_unknown_rule_ends_verify_task_in_failed(conn):
    run_verify_stage([_finding(rule_id="GBR-XX-99")], {}, lambda *a: {}, conn, "run")
    assert _state(conn, "p01.html::GBR", "verify") == ("FAILED", "UNKNOWN_RULE")
    assert get_adjudications(conn) == []


# --------------------------------------------------------------------------
# D6 timeouts and error classes
# --------------------------------------------------------------------------


@pytest.mark.parametrize("exc,error_class", [
    (BudgetExceededError("b"), "BUDGET_EXCEEDED"),
    (ProviderError("p"), "PROVIDER_ERROR"),
    (TimeoutError("t"), "TIMEOUT"),
    (RuntimeError("x"), "AGENT_ERROR"),
])
def test_d6_check_and_plan_stage_map_errors_to_failed(conn, exc, error_class):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])

    def boom(*_a):
        raise exc

    run_check_stage([task], boom, conn)
    assert _state(conn, "p01.html::GBR", "check") == ("FAILED", error_class)
    run_plan_stage([_finding()], boom, conn)
    assert _state(conn, "p01.html::GBR::GBR-BT-02", "plan") == ("FAILED", error_class)


@pytest.mark.parametrize("exc,error_class", [(ProviderError("p"), "PROVIDER_ERROR"), (TimeoutError("t"), "TIMEOUT")])
def test_d6_verify_stage_maps_errors(conn, exc, error_class):
    def boom(*_a):
        raise exc

    run_verify_stage([_finding()], {"GBR-BT-02": _rule()}, boom, conn, "run")
    assert _state(conn, "p01.html::GBR", "verify") == ("FAILED", error_class)


def _result(**kw):
    base = {"is_error": False, "subtype": "success", "api_error_status": None}
    return SimpleNamespace(**{**base, **kw})


@pytest.mark.parametrize("result,errors,expected", [
    (_result(), [], None),
    (None, [], None),
    (_result(is_error=True, subtype="error_max_turns"), [], BudgetExceededError),
    (_result(is_error=True, subtype="error_max_budget_usd"), [], BudgetExceededError),
    (_result(is_error=True, subtype="error_during_execution", api_error_status=429), [], ProviderError),
    (_result(is_error=True, subtype="error_during_execution", api_error_status=529), [], ProviderError),
    (_result(), ["rate_limit"], ProviderError),
    (None, ["authentication_failed"], ProviderError),
    (_result(is_error=True, subtype="error_during_execution", api_error_status=500), [], AgentRunError),
    (None, ["server_error"], AgentRunError),
    # RT2-05 ruling: a subscription usage-limit message is a provider rate limit, only on an error result
    (_result(is_error=True, result="You've hit your weekly limit - resets 3am"), [], ProviderError),
    (_result(is_error=True, errors=["You’ve hit your Sonnet limit"]), [], ProviderError),
    (_result(result="You've hit your session limit"), [], None),
    (_result(is_error=True, result="API Error: 500 server_error"), [], AgentRunError),
])
def test_d6_outcome_mapping(result, errors, expected):
    if expected is None:
        raise_for_outcome("x", result, errors)
    else:
        with pytest.raises(expected):
            raise_for_outcome("x", result, errors)


def test_rt2_05_agent_error_logs_raw_provider_type_and_status():
    """RT2-05: the raw error types and status reach payload_ref, so the
    INVALID RUN decision is made from logged error types."""
    with pytest.raises(AgentRunError, match=r"\['server_error', 'unknown'\]"):
        raise_for_outcome("x", None, ["server_error", "unknown"])
    with pytest.raises(AgentRunError, match="api_error_status=500") as exc:
        raise_for_outcome("x", _result(is_error=True, subtype="success", api_error_status=500,
                                       result="API Error: 500 internal"), ["server_error"])
    assert "['server_error']" in str(exc.value) and "API Error: 500 internal" in str(exc.value)


async def _slow_query(prompt, options):
    import anyio

    await anyio.sleep(30)
    yield None


async def _rate_limited_query(prompt, options):
    yield AssistantMessage(content=[], model="m", error="rate_limit")


def test_d6_checker_harness_timeout_and_provider_error(conn, tmp_path, monkeypatch):
    checker_audit.set_audit_db_path(tmp_path / "audit.db")
    try:
        task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])
        monkeypatch.setattr(checker_harness, "TIMEOUT_S", 0.2)
        monkeypatch.setattr(checker_harness, "query", _slow_query)
        run_check_stage([task], lambda t: checker_harness.real_checker(t, conn, "run"), conn)
        assert _state(conn, "p01.html::GBR", "check") == ("FAILED", "TIMEOUT")
        monkeypatch.setattr(checker_harness, "query", _rate_limited_query)
        with pytest.raises(ProviderError):
            checker_harness.real_checker(task, conn, "run")
    finally:
        checker_audit.set_audit_db_path(checker_audit.AUDIT_DB_PATH)


def test_d6_planner_harness_timeout(conn, tmp_path, monkeypatch):
    planner_audit.set_audit_db_path(tmp_path / "audit.db")
    try:
        monkeypatch.setattr(planner_harness, "TIMEOUT_S", 0.2)
        monkeypatch.setattr(planner_harness, "query", _slow_query)
        planner_fn = lambda f: planner_harness.real_planner(f, conn, "run", {"GBR-BT-02": _rule()})  # noqa: E731
        run_plan_stage([_finding()], planner_fn, conn)
        assert _state(conn, "p01.html::GBR::GBR-BT-02", "plan") == ("FAILED", "TIMEOUT")
    finally:
        planner_audit.set_audit_db_path(planner_audit.AUDIT_DB_PATH)


# --------------------------------------------------------------------------
# D3 verifier checkout: path override, pin, clean tree, audit-DB redirect
# --------------------------------------------------------------------------

FAKE_AGENT = {
    "agent/__init__.py": "",
    "agent/config.py": textwrap.dedent("""\
        from pathlib import Path
        REPO_ROOT = Path(__file__).resolve().parent.parent
        DATASET_ROOT = (REPO_ROOT / "evals" / "dataset").resolve()
        AUDIT_DB_PATH = REPO_ROOT / "audit.db"
        """),
    # Same import shapes as the pinned shipped agent: each name is copied
    # into the importing module, so only patching that module reaches it.
    "agent/pages.py": textwrap.dedent("""\
        from .config import DATASET_ROOT

        def read_page(rel_path):
            candidate = (DATASET_ROOT / rel_path).resolve()
            if not candidate.is_relative_to(DATASET_ROOT):
                raise ValueError("outside the dataset")
            return candidate.read_text(encoding="utf-8")
        """),
    "agent/audit.py": textwrap.dedent("""\
        import sqlite3
        from .config import AUDIT_DB_PATH

        def init_audit_db():
            conn = sqlite3.connect(AUDIT_DB_PATH)
            conn.execute("CREATE TABLE IF NOT EXISTS tool_calls (id INTEGER)")
            conn.commit()
            conn.close()
        """),
    "agent/harness.py": textwrap.dedent("""\
        import os
        import time
        from types import SimpleNamespace
        from . import pages
        from .audit import init_audit_db
        from .config import DATASET_ROOT

        def build_options(model, max_budget_usd):
            # The shipped build_options sets neither isolation option.
            return SimpleNamespace(model=model, max_budget_usd=max_budget_usd, tools=[],
                                   allowed_tools=["mcp__claimverify__fetch_page"],
                                   setting_sources=None, strict_mcp_config=False)

        async def run_case_result(case_id, run_id, model, max_budget_usd):
            o = build_options(model=model, max_budget_usd=max_budget_usd)
            mode = os.environ.get("FAKE_VERIFIER_MODE", "")
            if mode == "sleep":
                time.sleep(30)
            init_audit_db()
            if mode == "rate_limit":
                return SimpleNamespace(is_error=True, subtype="error_during_execution",
                                       api_error_status=429, total_cost_usd=0, num_turns=0), []
            if mode == "subscription_limit":
                return SimpleNamespace(is_error=True, subtype="success", api_error_status=None,
                                       result="You've hit your session limit", total_cost_usd=0, num_turns=0), []
            if mode == "server_error":
                return SimpleNamespace(is_error=True, subtype="success", api_error_status=500,
                                       result="API Error: 500", total_cost_usd=0, num_turns=0), []
            for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK"):
                if os.environ.get(name):
                    raise RuntimeError("non-subscription auth variable reached the verifier: " + name)
            if not (DATASET_ROOT / case_id).is_dir():
                raise FileNotFoundError("no such case under the dataset root")
            pages.read_page(f"{case_id}/source_page.html")
            finding = {"verdict": "SUPPORTED", "evidence_source": "source_page.html",
                       "evidence_note": f"seen under {DATASET_ROOT.as_posix()} | options "
                                        f"{o.setting_sources} {o.strict_mcp_config} {o.model} {o.max_budget_usd} "
                                        f"{o.tools} {o.allowed_tools}"}
            return SimpleNamespace(is_error=False, total_cost_usd=0.0, num_turns=1), [finding]
        """),
    ".gitignore": "__pycache__/\n",
}


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


@pytest.fixture
def fake_verifier(tmp_path, monkeypatch):
    repo = tmp_path / "verifier"
    for rel, content in FAKE_AGENT.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fake verifier")
    monkeypatch.setenv(verifier.REPO_PATH_ENV, str(repo))
    config = {
        "repo_path": "unused-because-env-override",
        "pinned_commit": _git(repo, "rev-parse", "HEAD"),
        "models": {"dev": "fake-model"},
        "max_budget_usd": {"dev": 0.01},
    }
    return repo, config


def test_d3_verifier_audit_db_goes_to_run_dir(fake_verifier, tmp_path):
    repo, config = fake_verifier
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)
    record = verifier.verify_finding(_finding(), _rule(), "run1", config=config, audit_db_path=run_dir / "verifier_audit.db")
    assert record["verdict"].value == "CONFIRMED"
    assert (run_dir / "verifier_audit.db").is_file()
    assert not (repo / "audit.db").exists()
    assert _git(repo, "status", "--porcelain") == ""  # case dir removed, nothing left behind


def test_d3_pin_mismatch_and_dirty_tree_refused(fake_verifier):
    repo, config = fake_verifier
    with pytest.raises(verifier.VerifierConfigError):
        verifier.check_verifier_checkout({**config, "pinned_commit": "0" * 40})
    (repo / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(verifier.VerifierConfigError):
        verifier.check_verifier_checkout(config)


def test_d6_verifier_timeout_and_provider_error(fake_verifier, monkeypatch):
    repo, config = fake_verifier
    monkeypatch.setattr(verifier, "TIMEOUT_S", 2)
    monkeypatch.setenv("FAKE_VERIFIER_MODE", "sleep")
    with pytest.raises(TimeoutError):
        verifier.verify_finding(_finding(), _rule(), "run1", config=config)
    assert not list((repo / "evals" / "dataset").glob("*"))  # case dir removed
    monkeypatch.setenv("FAKE_VERIFIER_MODE", "rate_limit")
    with pytest.raises(ProviderError):
        verifier.verify_finding(_finding(), _rule(), "run1", config=config)


def test_rt2_05_verifier_subscription_limit_is_provider_error(fake_verifier, tmp_path, monkeypatch):
    _repo, config = fake_verifier
    audit_db = tmp_path / "verifier_audit.db"
    monkeypatch.setenv("FAKE_VERIFIER_MODE", "subscription_limit")
    with pytest.raises(ProviderError):
        verifier.verify_finding(_finding(), _rule(), "run1", config=config, audit_db_path=audit_db)
    monkeypatch.setenv("FAKE_VERIFIER_MODE", "server_error")  # no provider status: stays an agent-side failure, logged raw
    with pytest.raises(VerifierInvocationError, match="api_error_status=500") as exc:
        verifier.verify_finding(_finding(), _rule(), "run1", config=config, audit_db_path=audit_db)
    assert not isinstance(exc.value, ProviderError)


def test_d1_verifier_subprocess_gets_no_api_key_and_loads_no_dotenv(fake_verifier, monkeypatch):
    """Owner decision D1: subscription login only. A key in the parent
    environment never reaches the verifier, and the runner loads no
    dotenv file (load_dotenv searched upward, outside the repository)."""
    _repo, config = fake_verifier
    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-not-a-key")
    monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")
    record = verifier.verify_finding(_finding(), _rule(), "run1", config=config)
    assert record["verdict"].value == "CONFIRMED"
    runner_code = verifier.RUNNER_SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from dotenv\b|import dotenv\b|load_dotenv\()", runner_code, re.MULTILINE)


# --------------------------------------------------------------------------
# Holdout leak markers (gate component_a.holdout_markers)
# --------------------------------------------------------------------------


def _audit_db(tmp_path, payload):
    db = tmp_path / "audit.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tool_calls (id INTEGER PRIMARY KEY, run_id TEXT, payload TEXT)")
    conn.execute("INSERT INTO tool_calls (run_id, payload) VALUES ('r', ?)", (json.dumps(payload),))
    conn.commit()
    conn.close()
    return db


@pytest.mark.parametrize("leak", ["see h7-07 for details", "open key.yaml", "briefs.md", "adjudication.md", "PRIVATE_ROOT_X"])
def test_holdout_markers_are_caught(tmp_path, leak):
    db = _audit_db(tmp_path, {"tool_response": leak})
    with pytest.raises(AssertionError):
        assert_no_key_leak(
            "r", db_path=db, extra_markers=["key.yaml", "briefs.md", "adjudication.md", "PRIVATE_ROOT_X"],
            patterns=[r"\bh\d+-\d\d\b"],
        )


def test_windows_holdout_root_path_is_caught_in_json_payload(tmp_path):
    """The audit payload is JSON, so a backslash path is stored escaped;
    the check must still find it (review finding, P2 round 1)."""
    root = "D:\\private\\holdouts"
    db = _audit_db(tmp_path, {"tool_response": f"file at {root}\\H9\\pages"})
    conn = sqlite3.connect(db)
    stored = conn.execute("SELECT payload FROM tool_calls").fetchone()[0]
    conn.close()
    assert root not in stored and "\\\\" in stored  # stored escaped: a plain search would miss it
    with pytest.raises(AssertionError):
        assert_no_key_leak("r", db_path=db, extra_markers=[root])


def test_clean_audit_row_passes(tmp_path):
    db = _audit_db(tmp_path, {"tool_response": "page01.html text"})
    assert_no_key_leak("r", db_path=db, extra_markers=["key.yaml"], patterns=[r"\bh\d+-\d\d\b"])


# --------------------------------------------------------------------------
# Ruleset v1.1 (D7 text written in P2) and its recorded hashes
# --------------------------------------------------------------------------


def _signed_texts() -> dict[str, str]:
    md = (REPO_ROOT / "evals" / "v2" / "RULESET_V1_1.md").read_text(encoding="utf-8")
    section = md.split("## Proposed rule_text, exact strings", 1)[1].split("## July key check", 1)[0]
    lines = section.splitlines()
    texts = {}
    for i, line in enumerate(lines):
        ids = re.findall(r"\*\*([A-Z]{3}-[A-Z]{2}-\d\d)\*\*", line) if line.startswith("**") else []
        if ids:
            quote = next(item for item in lines[i + 1:] if item.startswith("> "))
            texts.update({rid: quote[2:] for rid in ids})
    return texts


def test_rule_files_carry_the_signed_v1_1_text():
    signed = _signed_texts()
    assert len(signed) == 14
    rules = [r for f in sorted((REPO_ROOT / "rulesets").glob("*.json")) for r in json.loads(f.read_text(encoding="utf-8"))]
    assert len(rules) == 24
    for r in rules:
        assert r["ruleset_version"] == "v1.1"
        if r["rule_id"] in signed:
            assert r["rule_text"] == signed[r["rule_id"]]
        else:
            assert "Interpretation (v1.1):" not in r["rule_text"]


def test_rule_file_hashes_match_the_gate():
    gate = yaml.safe_load((REPO_ROOT / "evals" / "eval_config.yaml").read_text(encoding="utf-8"))
    recorded = gate["datasets"]["ruleset_sha256"]
    assert set(recorded) == {"rulesets/deu-v1.json", "rulesets/gbr-v1.json", "rulesets/mlt-v1.json"}
    for rel, digest in recorded.items():
        content = (REPO_ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == digest

