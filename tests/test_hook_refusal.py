"""Gate v2.1 (2026-11-04): an agent tool call refused by the machine-policy
record hook and not recovered makes the series INVALID RUN; a recovered
refusal leaves the run valid and scored as usual. Keyless: fake CLI
transcripts in a temporary config folder and a synthetic refusal marker (the
real marker is not kept in this repository); no model call, stub agents.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from agents.checker import pages
from evals import run_eval as re_

REPO_ROOT = Path(__file__).resolve().parent.parent
MARK = "SYNTHETIC-RECORD-REFUSAL"
TOOL = "mcp__compliancecheck__fetch_page"
REFUSAL = (f"<tool_use_error>PreToolUse:{TOOL} hook error: [record hook]: "
           f"{MARK}: external action refused because its record could not be written (record lock busy)")


@pytest.fixture(autouse=True)
def _clean():
    yield
    pages.reset_cage()


def _use(use_id: str, page: str = "d01.html", tool: str = TOOL) -> str:
    block = {"type": "tool_use", "id": use_id, "name": tool, "input": {"page": page}}
    return json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [block]}})


def _result(use_id: str, *, error: bool = False, refused: bool = False) -> str:
    content = REFUSAL if refused else ("tool failed" if error else "page text")
    block = {"type": "tool_result", "tool_use_id": use_id, "is_error": error or refused, "content": content}
    return json.dumps({"type": "user", "message": {"role": "user", "content": [block]}})


def _write(folder: Path, *lines: str, name: str = "session.jsonl") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


# The approved scenarios, at the transcript level: (lines, expected (refusals, not recovered)).
SCENARIOS = {
    "refusal then identical retry that succeeds: recovered": (
        [_use("a"), _result("a", refused=True), _use("b"), _result("b")], (1, 0)),
    "refusal without retry: not recovered": (
        [_use("a"), _result("a", refused=True)], (1, 1)),
    "retry with different input: not recovered": (
        [_use("a"), _result("a", refused=True), _use("b", page="d02.html"), _result("b")], (1, 1)),
    "retry with another tool: not recovered": (
        [_use("a"), _result("a", refused=True), _use("b", tool="mcp__compliancecheck__read_ruleset"), _result("b")], (1, 1)),
    "retry refused again: not recovered": (
        [_use("a"), _result("a", refused=True), _use("b"), _result("b", refused=True)], (2, 2)),
    "retry allowed but the tool fails: not recovered": (
        [_use("a"), _result("a", refused=True), _use("b"), _result("b", error=True)], (1, 1)),
    "retry with no result recorded: not recovered": (
        [_use("a"), _result("a", refused=True), _use("b")], (1, 1)),
    "identical call before the refusal does not count": (
        [_use("a"), _result("a"), _use("b"), _result("b", refused=True)], (1, 1)),
    "refused call missing from the session: not recovered": (
        [_result("a", refused=True)], (1, 1)),
    "unreadable line with the refusal text: not recovered": (
        [f"not json {MARK}"], (1, 1)),
    "refusal text in page content or the model's words: no refusal": (
        [_use("a"), json.dumps({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "a", "is_error": False, "content": f"{MARK} on a page"}]}}),
         json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": MARK}]}})],
        (0, 0)),
}


@pytest.mark.parametrize("name", SCENARIOS)
def test_recovery_rule(tmp_path, name):
    lines, expected = SCENARIOS[name]
    _write(tmp_path, *lines)
    assert re_.hook_refusals(tmp_path, MARK) == expected


def test_retry_must_be_in_the_same_session(tmp_path):
    _write(tmp_path, _use("a"), _result("a", refused=True), name="one.jsonl")
    _write(tmp_path / "one" / "subagents", _use("b"), _result("b"), name="two.jsonl")
    assert re_.hook_refusals(tmp_path, MARK) == (1, 1)


def test_transcript_dir_follows_the_cli_folder_naming(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    run_dir = Path("holdouts") / "runs" / "H2" / "H2-2026-11-05-abc123" / "run1"
    assert re_.cli_transcript_dir(run_dir) == tmp_path / "projects" / "holdouts-runs-H2-H2-2026-11-05-abc123-run1"


def _series(tmp_path, monkeypatch, lines, crash=False):
    """One real-mode d10 run: stub agents decide the cells (so primaries are wrong,
    not technical failures) and a fake CLI transcript is written; lines None = no folder."""
    import nodes.verifier

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cli-config"))
    monkeypatch.setenv(re_.HOOK_MARK_ENV, MARK)
    monkeypatch.setattr(nodes.verifier, "check_verifier_checkout", lambda: None)
    monkeypatch.setattr(re_, "a2_checks", lambda ctx: [])  # A2 reads real agents' audit rows; not under test here
    stub_run_once = re_.run_once

    def run_once(ctx, model):
        if lines is not None:
            _write(re_.cli_transcript_dir(ctx.run_dir), *lines)
        if crash:
            raise RuntimeError("system code failed")  # raised outside evals/: a system exception
        ctx.real = False  # stub agents only; no model call
        try:
            return stub_run_once(ctx, None)
        finally:
            ctx.real = True

    monkeypatch.setattr(re_, "run_once", run_once)
    return re_.run_series("d10", tmp_path / "root", runs=1, real=True, results_dir=tmp_path / "results")


def test_no_refusal_and_wrong_decisions_is_normal_scoring(tmp_path, monkeypatch):
    result, results, _out = _series(tmp_path, monkeypatch, [_use("a"), _result("a")])
    assert result == re_.FAIL and results["series"]["exit_code"] == re_.EXIT_COMPLETED
    assert results["aggregates"]["cases_failed"] > 0  # stub checkers miss the D10 violations


def test_recovered_refusal_keeps_the_run_valid(tmp_path, monkeypatch):
    lines = [_use("a"), _result("a", refused=True), _use("b"), _result("b")]
    result, results, _out = _series(tmp_path, monkeypatch, lines)
    assert result == re_.FAIL and results["per_case"]  # scored as usual, not INVALID RUN


@pytest.mark.parametrize("name", [n for n, (_l, (_r, u)) in SCENARIOS.items() if u])
def test_unrecovered_refusal_makes_the_series_invalid_before_scoring(tmp_path, monkeypatch, name):
    result, results, _out = _series(tmp_path, monkeypatch, SCENARIOS[name][0])
    assert result == re_.INVALID_RUN and results["series"]["exit_code"] == re_.EXIT_INVALID_RUN
    assert results["per_case"] == [] and results["aggregates"] == {}  # decided before any score


def test_missing_transcript_folder_is_invalid(tmp_path, monkeypatch):
    result, _results, _out = _series(tmp_path, monkeypatch, None)
    assert result == re_.INVALID_RUN


def test_unrecovered_refusal_after_a_system_crash_is_invalid(tmp_path, monkeypatch):
    result, _results, _out = _series(tmp_path, monkeypatch, [_use("a"), _result("a", refused=True)], crash=True)
    assert result == re_.INVALID_RUN


def test_stub_runs_need_no_transcripts(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cli-config"))
    result, _results, _out = re_.run_series("d10", tmp_path / "root", runs=1)
    assert result in (re_.PASS, re_.FAIL)


def test_check_is_skipped_only_for_stub_contexts(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    re_._raise_for_hook_refusals(SimpleNamespace(real=False, run_index=1, run_dir=tmp_path / "none"), None)
    with pytest.raises(re_.InvalidRun):
        re_._raise_for_hook_refusals(SimpleNamespace(real=True, run_index=1, run_dir=tmp_path / "none"), MARK)


def test_real_context_without_a_marker_is_a_runner_failure(tmp_path):
    _write(tmp_path / "projects" / "x", _use("a"), _result("a"))
    with pytest.raises(re_.InvalidRun, match="no refusal marker"):
        re_._raise_for_hook_refusals(SimpleNamespace(real=True, run_index=1, run_dir=tmp_path / "x"), None)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_marker_comes_from_the_environment_and_blank_is_missing(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(re_.HOOK_MARK_ENV, raising=False)
    else:
        monkeypatch.setenv(re_.HOOK_MARK_ENV, value)
    assert re_.hook_refusal_mark(re_.os.environ) is None
    monkeypatch.setenv(re_.HOOK_MARK_ENV, f"  {MARK} ")
    assert re_.hook_refusal_mark(re_.os.environ) == MARK


@pytest.mark.parametrize("dataset, gated", [("H2", True), ("d10", False)])
@pytest.mark.parametrize("value", [None, "  "])
def test_real_run_without_the_marker_stops_before_it_starts(tmp_path, monkeypatch, dataset, gated, value):
    if value is None:
        monkeypatch.delenv(re_.HOOK_MARK_ENV, raising=False)
    else:
        monkeypatch.setenv(re_.HOOK_MARK_ENV, value)
    monkeypatch.setattr(re_, "run_once", lambda ctx, model: pytest.fail("a run started without the marker"))
    with pytest.raises(ValueError, match=re_.HOOK_MARK_ENV):
        re_.run_series(dataset, tmp_path / "root", runs=3, real=True, gated=gated, results_dir=tmp_path / "results")
    assert not (tmp_path / "root").exists() and not (tmp_path / "results").exists()  # nothing recorded


def test_stub_runs_need_no_marker(tmp_path, monkeypatch):
    monkeypatch.delenv(re_.HOOK_MARK_ENV, raising=False)
    result, _results, _out = re_.run_series("d10", tmp_path / "root", runs=1)
    assert result in (re_.PASS, re_.FAIL)



def test_gate_v2_1_adds_the_rule_and_keeps_the_frozen_items():
    config = yaml.safe_load((REPO_ROOT / "evals" / "eval_config.yaml").read_text(encoding="utf-8"))
    assert config["version"] == "2.1"
    assert any(re_.HOOK_MARK_ENV in w and "recovered" in w for w in config["result_rules"]["INVALID_RUN"]["when"])
    claim = config["component_b"]["claim"]
    assert (claim["min_cases"], claim["allowed_failing_cases"], claim["runs_per_case"]) == (30, 2, 3)
    assert config["component_b"]["off_target_guardrail"]["max_unclean_pages"] == 6
