"""P3 storage-isolation tests (repair program P-001, owner decisions 1A,
2A and 3A, 2026-11-03), keyless: verifier case files go to a private
case root and never into the verifier checkout; run output is refused
inside any Git work tree; real runs execute in the private run directory,
and that working directory changes no configuration, agent option, hook
or file access. No model call, no real verifier run, no CLI process.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

import agents.checker.harness as checker_harness
import agents.planner.harness as planner_harness
import nodes.verifier as verifier
from agents.checker import audit as checker_audit
from agents.checker import pages
from agents.checker.config import RULESETS_DIR
from agents.planner import audit as planner_audit
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from contracts.schemas import CheckTask
from evals import run_eval as re_
from intake.local_config import load_local_config
from orchestrator.ledger import create_db
from orchestrator.pipeline import get_findings
from tests.test_check_holdout import _build
from tests.test_p2_repairs import _finding, _rule, _slow_query, _state, conn, fake_verifier  # noqa: F401 -- fixtures
from tests.test_run_eval import CONFIG, ON_PAGE, RULES_BY_ID, RULESETS, _checker, _manifest, _planner

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean():
    from agents.planner import stub as planner_stub
    from nodes import verifier_stub

    # Other test modules leave stub failure settings behind.
    verifier_stub.reset_failures()
    planner_stub.reset_failures()
    yield
    pages.reset_cage()
    verifier_stub.reset_failures()
    planner_stub.reset_failures()


# --------------------------------------------------------------------------
# Verifier case files: private case root, never the checkout
# --------------------------------------------------------------------------


def test_verifier_case_files_go_to_the_private_case_root(fake_verifier, tmp_path):
    repo, config = fake_verifier
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)
    case_root = run_dir / "verifier_cases"
    record = verifier.verify_finding(_finding(), _rule(), "run1", config=config,
                                     audit_db_path=run_dir / "verifier_audit.db", case_root=case_root)
    assert record["verdict"].value == "CONFIRMED"
    assert case_root.resolve().as_posix() in record["citation"]  # the shipped agent read from here
    assert list(case_root.iterdir()) == []  # case dir removed
    assert not (repo / "evals" / "dataset").exists()
    left = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--ignored"],
                          capture_output=True, text=True, check=True).stdout.splitlines()
    assert [line for line in left if not line.rstrip("/").endswith("__pycache__")] == []


def test_relative_verifier_repo_path_resolves_against_the_repo(monkeypatch, tmp_path):
    monkeypatch.delenv(verifier.REPO_PATH_ENV, raising=False)
    monkeypatch.setattr(verifier, "load_local_config", lambda: {})
    monkeypatch.chdir(tmp_path)
    assert verifier.resolve_repo_path({"repo_path": "../some-checkout"}) == (REPO_ROOT / "../some-checkout").resolve()


# --------------------------------------------------------------------------
# Storage guard: no run output inside any Git work tree
# --------------------------------------------------------------------------


def test_storage_guard_refuses_a_git_work_tree(tmp_path):
    tree = tmp_path / "some-repo"
    subprocess.run(["git", "init", "-q", str(tree)], check=True)
    holdout_root = tree / "private"
    with pytest.raises(re_.StorageError, match="Git work tree"):
        re_.guard_output_path(holdout_root / "runs" / "H9" / "s1", holdout_root, [])
    outside = tmp_path / "private"
    assert re_.guard_output_path(outside / "runs" / "H9" / "s1", outside, []).is_relative_to(outside.resolve())


# --------------------------------------------------------------------------
# Working directory (decision 2A): nothing depends on it
# --------------------------------------------------------------------------


def _paths_seen() -> dict:
    cfg = verifier.load_verifier_config()
    return {
        "local_config": load_local_config(),
        "verifier_config": cfg,
        "verifier_repo": verifier.resolve_repo_path(cfg),
        "runner_script": verifier.RUNNER_SCRIPT,
        "page": pages.resolve_page_path("p01.html"),
        "rulesets": RULESETS_DIR,
        "checker_audit": checker_audit.get_audit_db_path(),
        "planner_audit": planner_audit.get_audit_db_path(),
        "eval_config": re_.EVAL_CONFIG_PATH,
    }


def test_configuration_resolves_the_same_from_any_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO_ROOT)
    at_root = _paths_seen()
    monkeypatch.chdir(tmp_path)
    assert _paths_seen() == at_root
    assert all(Path(at_root[k]).is_absolute() for k in ("verifier_repo", "runner_script", "page", "rulesets"))


def test_file_access_cage_holds_from_a_foreign_working_directory(monkeypatch, tmp_path):
    cage = tmp_path / "cage"
    cage.mkdir()
    (cage / "real-01.html").write_text("<p>x</p>", encoding="utf-8")
    (tmp_path / "outside.html").write_text("<p>y</p>", encoding="utf-8")
    pages.configure_cage(cage, {"page01.html": "real-01.html"})
    monkeypatch.chdir(tmp_path)
    assert pages.resolve_page_path("page01.html") == (cage / "real-01.html").resolve()
    for bad in ("real-01.html", "../outside.html", "outside.html"):
        with pytest.raises(FileNotFoundError, match="page cage"):
            pages.resolve_page_path(bad)
    pages.configure_cage(cage)  # no alias map: the escape check itself
    with pytest.raises(pages.PathOutsideDatasetError):
        pages.resolve_page_path("../outside.html")
    assert pages.resolve_page_path("real-01.html") == (cage / "real-01.html").resolve()


def _cli_args(options) -> list[str]:
    transport = SubprocessCLITransport(prompt="x", options=options)
    transport._cli_path = "claude"  # build the command only; no process is started
    return transport._build_command()[1:]


def _agent_options(conn):
    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])
    return [checker_harness.build_options(task, conn), planner_harness.build_options(_finding(), _rule(), "run1")]


def test_agent_options_hooks_and_cli_command_do_not_depend_on_cwd(monkeypatch, tmp_path):
    conn = create_db(str(tmp_path / "ledger.db"))
    try:
        monkeypatch.chdir(REPO_ROOT)
        at_root = [_cli_args(o) for o in _agent_options(conn)]
        monkeypatch.chdir(tmp_path)
        options = _agent_options(conn)
        assert [_cli_args(o) for o in options] == at_root
    finally:
        conn.close()
    for o, args in zip(options, at_root):
        assert o.cwd is None and o.tools == [] and o.setting_sources == [] and o.strict_mcp_config
        assert all(t.startswith("mcp__") for t in o.allowed_tools)
        assert set(o.hooks) == {"PreToolUse", "PostToolUse"}  # the in-process audit hooks
        assert "--setting-sources=" in args and "--strict-mcp-config" in args


# --------------------------------------------------------------------------
# R1 (owner decision 2026-11-03): the verifier session gets the 3A isolation
# --------------------------------------------------------------------------


def _shipped_like_options(model="fake-model", max_budget_usd=0.25):
    """Same option shape as the pinned agent's build_options."""
    from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, create_sdk_mcp_server

    return ClaudeAgentOptions(
        model=model, system_prompt="verify", tools=[],
        mcp_servers={"claimverify": create_sdk_mcp_server(name="claimverify", version="1.0.0", tools=[])},
        allowed_tools=["mcp__claimverify__fetch_page", "mcp__claimverify__compare_source"],
        max_turns=20, max_budget_usd=max_budget_usd,
        hooks={"PreToolUse": [HookMatcher(hooks=[_audit_hook])], "PostToolUse": [HookMatcher(hooks=[_audit_hook])]},
    )


async def _audit_hook(*_a):
    return {}


def test_r1_verifier_options_get_only_the_settings_isolation():
    from dataclasses import fields

    from nodes.verifier_runner import isolate_settings

    shipped = _shipped_like_options()
    isolated = isolate_settings(_shipped_like_options)(model="fake-model", max_budget_usd=0.25)
    assert shipped.setting_sources is None and not shipped.strict_mcp_config  # what the pinned agent sets
    assert isolated.setting_sources == [] and isolated.strict_mcp_config is True
    changed = {f.name for f in fields(shipped) if getattr(shipped, f.name) != getattr(isolated, f.name)}
    # Each build creates its own in-process server object; same name and type.
    assert changed == {"setting_sources", "strict_mcp_config", "mcp_servers"}  # whitelist, budget, turns, hooks, model kept
    assert {k: v["type"] for k, v in isolated.mcp_servers.items()} == {k: v["type"] for k, v in shipped.mcp_servers.items()}
    plain, args = _cli_args(shipped), _cli_args(isolated)
    assert "--setting-sources=" in args and "--strict-mcp-config" in args
    assert "--setting-sources=" not in plain and "--strict-mcp-config" not in plain
    assert [a for a in args if a not in ("--setting-sources=", "--strict-mcp-config")] == plain


def test_r1_verifier_subprocess_runs_with_the_isolation(fake_verifier, tmp_path):
    _repo, config = fake_verifier
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)
    record = verifier.verify_finding(_finding(), _rule(), "run1", config=config,
                                     audit_db_path=run_dir / "verifier_audit.db", case_root=run_dir / "verifier_cases")
    assert record["verdict"].value == "CONFIRMED"
    # The fake shipped agent reports the options its own build_options returned.
    assert "| options [] True fake-model 0.01 [] ['mcp__claimverify__fetch_page']" in record["citation"]


def _fresh_ctx(tmp_path, real: bool) -> re_.RunContext:
    from dataclasses import replace

    july = re_.load_july()
    dataset = replace(july, cases=[c for c in july.cases if c.case_id == "p01"])
    run_dir = tmp_path / "run1"
    run_dir.mkdir(parents=True)
    conn = create_db(str(run_dir / "ledger.db"))
    return re_.RunContext(dataset, CONFIG, 1, "run-cwd", run_dir, run_dir / "ledger.db", run_dir / "audit.db", conn,
                          re_.build_tasks(dataset, RULESETS), RULESETS, RULES_BY_ID, real, False, [])


def _recording_agent_fns(seen: list):
    from nodes import verifier_stub

    def checker(task):
        seen.append(os.getcwd())
        return _checker(task)

    def verify(finding, rule, run_id):
        seen.append(os.getcwd())
        return verifier_stub.stub_verifier(finding, rule, run_id)

    def plan(finding):
        seen.append(os.getcwd())
        return _planner(finding)

    return lambda ctx, model: (checker, verify, plan, {"cost_usd": 0.0, "turns": 0})


@pytest.mark.parametrize("real", [True, False])
def test_real_runs_execute_in_the_private_run_dir(monkeypatch, tmp_path, real):
    seen: list[str] = []
    monkeypatch.setattr(re_, "_agent_fns", _recording_agent_fns(seen))
    monkeypatch.chdir(REPO_ROOT)
    ctx = _fresh_ctx(tmp_path, real)
    try:
        re_.run_once(ctx, None)
        assert get_findings(ctx.conn)  # the stages ran
    finally:
        ctx.conn.close()
    expected = str(ctx.run_dir) if real else str(REPO_ROOT)
    assert seen and {Path(s).resolve() for s in seen} == {Path(expected).resolve()}
    assert Path(os.getcwd()).resolve() == REPO_ROOT.resolve()  # restored


def test_working_directory_is_restored_after_an_exception(monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise RuntimeError("stage failed")

    monkeypatch.setattr(re_, "_agent_fns", _recording_agent_fns([]))
    monkeypatch.setattr(re_, "run_check_stage", boom)
    monkeypatch.chdir(REPO_ROOT)
    ctx = _fresh_ctx(tmp_path, True)
    try:
        with pytest.raises(RuntimeError):
            re_.run_once(ctx, None)
    finally:
        ctx.conn.close()
    assert Path(os.getcwd()).resolve() == REPO_ROOT.resolve()


# --------------------------------------------------------------------------
# Red team 2 fixes (evals/v2/RED_TEAM_2.md)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("runs", [0, -1])
def test_rt2_01_run_count_below_one_is_refused(tmp_path, runs):
    with pytest.raises(ValueError, match="at least 1"):
        re_.run_series("july", tmp_path, runs=runs)
    assert re_.main(["--dataset", "july", "--runs", str(runs), "--holdout-root", str(tmp_path)]) == re_.EXIT_USAGE


@pytest.mark.parametrize("runs", [1, 2, 4])
def test_rt2_01_gated_series_needs_exactly_the_gate_run_count(tmp_path, runs):
    with pytest.raises(ValueError, match="exactly 3 runs"):
        re_.run_series("H9", tmp_path, runs=runs, gated=True)


def test_rt2_02_gated_series_needs_a_clean_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(re_, "_git_dirty", lambda: True)
    with pytest.raises(ValueError, match="clean working tree"):
        re_.run_series("H9", tmp_path, gated=True)


def test_rt2_03_retired_holdout_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(re_, "_git_dirty", lambda: False)
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "H9-2026-11-03-abcdef.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="retired"):
        re_.run_series("H9", tmp_path, gated=True, results_dir=results_dir)


def test_rt2_03_gated_series_needs_the_full_manifest(tmp_path, monkeypatch):
    from evals import check_holdout

    monkeypatch.setattr(re_, "_git_dirty", lambda: False)
    root = _build(tmp_path)
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    (mdir / "H9.sha256").write_text("\n".join(check_holdout.manifest_lines(root, True)) + "\n", encoding="utf-8")
    result, _results, _ = re_.run_series("H9", tmp_path, gated=True, run_a1=False, manifest_dir=mdir,
                                         results_dir=tmp_path / "results")
    assert result == re_.INVALID_RUN
    assert not (tmp_path / "results").exists()  # no official result file


def _crash_in_system_code():
    from orchestrator.pipeline import run_check_stage

    run_check_stage(None, None, None)  # TypeError raised inside orchestrator/pipeline.py


def test_rt2_04_resume_crash_in_system_code_is_scored_not_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(re_, "resume_check", lambda *a, **k: _crash_in_system_code())
    result, results, _ = re_.run_series("july", tmp_path, runs=1)
    assert result == re_.FAIL
    row = next(r for r in results["component_a"] if r["check_name"] == "resume_zero_calls_zero_rows")
    assert row["passed"] is False


def test_rt2_04_provider_error_then_system_crash_is_invalid_run(tmp_path, monkeypatch):
    from orchestrator.pipeline import ProviderError, run_check_stage

    def run_once(ctx, model):
        def provider_down(task):
            raise ProviderError("rate limited")

        run_check_stage(ctx.tasks[:1], provider_down, ctx.conn)
        _crash_in_system_code()

    monkeypatch.setattr(re_, "run_once", run_once)
    result, _results, _ = re_.run_series("july", tmp_path, runs=1)
    assert result == re_.INVALID_RUN


def test_rt2_09_verifier_page_copy_carries_the_page_title():
    from nodes.assembler import assemble_case

    title, blocks = pages.read_page("p01.html")
    page_html = assemble_case(_finding(), _rule())["source_page.html"]
    import html as html_mod

    body = page_html.split("<body>", 1)[1]
    assert f"<p>{html_mod.escape(title, quote=False)}</p>" in body
    assert all(f"<p>{html_mod.escape(b, quote=False)}</p>" in body for b in blocks)


def test_rt2_10_checker_reads_only_its_own_page(conn):
    import asyncio

    from agents.checker import tools as checker_tools

    task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])
    fetch_page, _r, _e = checker_tools.build_tools(task, conn)
    other = asyncio.run(fetch_page.handler({"path": "p02.html"}))
    assert other.get("is_error") and "not the page assigned" in other["content"][0]["text"]
    assert conn.execute("SELECT allowed FROM path_access_log WHERE requested_path = 'p02.html'").fetchone()[0] == 0
    assert not asyncio.run(fetch_page.handler({"path": "p01.html"})).get("is_error")


def test_rt2_11_timed_out_session_reports_no_stale_cost(conn, tmp_path, monkeypatch):
    from types import SimpleNamespace

    checker_audit.set_audit_db_path(tmp_path / "audit.db")
    try:
        monkeypatch.setattr(checker_harness, "TIMEOUT_S", 0.2)
        monkeypatch.setattr(checker_harness, "query", _slow_query)
        checker_harness.last_result = SimpleNamespace(total_cost_usd=9.0, num_turns=9)  # an earlier session
        task = CheckTask(page_path="p01.html", jurisdiction="GBR", ruleset_version="v1.1", assigned_rules=["GBR-BT-02"])
        with pytest.raises(TimeoutError):
            checker_harness.real_checker(task, conn, "run")
        assert checker_harness.last_result is None
    finally:
        checker_audit.set_audit_db_path(checker_audit.AUDIT_DB_PATH)


def test_rt2_11_verifier_cost_and_turns_are_counted(tmp_path, monkeypatch):
    def fake_verify(finding, rule, run_id, **_kw):
        verifier.run_stats.append({"finding_id": "x", "cost_usd": 0.25, "num_turns": 4})
        return {}

    monkeypatch.setattr(verifier, "verify_finding", fake_verify)
    verifier.reset_run_stats()
    ctx = _fresh_ctx(tmp_path, True)
    try:
        _checker_fn, verifier_fn, _planner_fn, stats = re_._agent_fns(ctx, "fake-model")
        verifier_fn(_finding(), _rule(), "run")
        assert stats == {"cost_usd": 0.25, "turns": 4, "cost_usd_estimated": 0.0, "estimated_sessions": 0}
    finally:
        ctx.conn.close()
        verifier.reset_run_stats()


def test_r2_budget_stop_is_counted_as_an_estimate_apart_from_measured(tmp_path, monkeypatch):
    from orchestrator.pipeline import VerifierInvocationError

    def fake_verify(finding, rule, run_id, **_kw):
        verifier.run_stats.append({"finding_id": "x", "cost_usd": None, "cost_usd_estimated": 0.25, "num_turns": None})
        raise VerifierInvocationError("budget stop")

    monkeypatch.setattr(verifier, "verify_finding", fake_verify)
    verifier.reset_run_stats()
    ctx = _fresh_ctx(tmp_path, True)
    try:
        _checker_fn, verifier_fn, _planner_fn, stats = re_._agent_fns(ctx, "fake-model")
        with pytest.raises(VerifierInvocationError):
            verifier_fn(_finding(), _rule(), "run")
        assert stats == {"cost_usd": 0.0, "turns": 0, "cost_usd_estimated": 0.25, "estimated_sessions": 1}
    finally:
        ctx.conn.close()
        verifier.reset_run_stats()


def test_r2_console_shows_verify_failures_and_the_estimate_apart(tmp_path, monkeypatch, capsys):
    from orchestrator.pipeline import VerifierInvocationError

    def agent_fns(ctx, model):
        stats = {"cost_usd": 0.0, "turns": 0, "cost_usd_estimated": 0.0, "estimated_sessions": 0}

        def verify(finding, rule, run_id):
            stats["cost_usd_estimated"] += 0.25
            stats["estimated_sessions"] += 1
            raise VerifierInvocationError("budget stop")

        return _checker, verify, _planner, stats

    monkeypatch.setattr(re_, "_agent_fns", agent_fns)
    assert re_.main(["--dataset", "july", "--page", "p01", "--runs", "1", "--holdout-root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    # _checker raises one VIOLATION in each of the 2 p01 tasks: 2 verify tasks, both stopped.
    assert "failed tasks (diagnostic): check 0, verify 2, plan 0" in out
    assert "measured 0.0 USD, 0 turns; estimated 0.5 USD for 2 verifier budget stops" in out
    results = json.loads(next(tmp_path.glob("runs/july/*/results.json")).read_text(encoding="utf-8"))
    assert results["aggregates"]["cost_usd"] == 0.0  # results keep the measured value only; the allowlist is frozen
    assert set(results["aggregates"]) == set(CONFIG["sanitized_results_allowlist"]["aggregates"])


# --------------------------------------------------------------------------
# Interaction sweep rows that needed a keyless test (RED_TEAM_2.md)
# --------------------------------------------------------------------------


def test_sweep_one_sentence_triggers_rules_in_two_markets(tmp_path):
    from nodes import verifier_stub
    from orchestrator.pipeline import run_check_stage, run_plan_stage, run_verify_stage

    def checker(task):
        out = _checker(task)
        for f in out:  # the same on-page sentence violates one rule in each market
            if f["rule_id"] in ("GBR-BT-02", "MLT-BT-01"):
                f["verdict"], f["evidence_excerpt"] = "VIOLATION", ON_PAGE
        return out

    ctx = _fresh_ctx(tmp_path, False)
    try:
        run_check_stage(ctx.tasks, checker, ctx.conn)
        findings = get_findings(ctx.conn)
        run_verify_stage(findings, RULES_BY_ID, verifier_stub.stub_verifier, ctx.conn, ctx.run_id)
        confirmed = re_._confirmed(ctx.conn, findings)
        run_plan_stage(confirmed, _planner, ctx.conn)
        hits = {(f.jurisdiction, f.rule_id) for f in confirmed if f.evidence_excerpt == ON_PAGE}
        assert hits == {("GBR", "GBR-BT-02"), ("MLT", "MLT-BT-01")}
        integrity = dict(re_.planner_integrity(ctx.conn, ctx.run_id, ctx.page_text))
        assert all(v == 0 for v in integrity.values()), integrity
    finally:
        ctx.conn.close()


def test_sweep_verifier_failure_on_one_of_two_findings_fails_the_whole_task(conn):
    from orchestrator.pipeline import VerifierInvocationError, get_adjudications, run_verify_stage

    first = _finding()
    second = _finding(rule_id="GBR-PC-01", excerpt="other text")
    calls = []

    def verify(finding, rule, run_id):
        calls.append(finding.rule_id)
        if finding.rule_id == "GBR-PC-01":
            raise VerifierInvocationError("verifier failed")
        return {"finding_id": f"{finding.task_id}::{finding.rule_id}", "verdict": "CONFIRMED", "citation": "c",
                "model": "m", "timestamp": "2026-11-03T00:00:00+00:00", "run_id": run_id}

    rules = {"GBR-BT-02": _rule(), "GBR-PC-01": _rule(rule_id="GBR-PC-01")}
    run_verify_stage([first, second], rules, verify, conn, "run")
    assert _state(conn, "p01.html::GBR", "verify")[0] == "FAILED"
    assert get_adjudications(conn) == []  # task-atomic: neither finding is asserted
