"""D10 development dataset in the runner (evals/run_eval.py --dataset d10),
keyless: selection, pages and final-key cells loaded as committed, the key
files out of the agents' reach, July unchanged, and D10 never gated.
No model call; stub agents only.
"""
from pathlib import Path

import pytest
import yaml

from agents.checker import pages
from evals import run_eval as re_
from intake.inventory import extract_markets, load_rulesets

REPO_ROOT = Path(__file__).resolve().parent.parent
D10_DIR = REPO_ROOT / "evals" / "dataset" / "d10"
RULESETS = load_rulesets(REPO_ROOT / "rulesets")
KEY_FILES = ("key.yaml", "briefs.md", "adjudication.md")


@pytest.fixture(autouse=True)
def _clean():
    yield
    pages.reset_cage()


def _capture_ctx(monkeypatch) -> dict:
    seen = {}

    def run_once(ctx, model):
        seen["ctx"] = ctx
        raise re_.InvalidRun("stop after task building")  # no need to run the stages

    monkeypatch.setattr(re_, "run_once", run_once)
    return seen


def test_d10_series_selects_the_ten_d10_pages(tmp_path):
    result, results, out = re_.run_series("d10", tmp_path, runs=1)
    assert result in (re_.PASS, re_.FAIL)
    assert [r["case_id"] for r in results["per_case"]] == [f"d{n:02d}" for n in range(1, 11)]
    assert out.is_relative_to(tmp_path / "runs" / "d10")
    a3 = [r for r in results["component_a"] if r["check_name"].startswith("a3_")]
    assert len(a3) == 3 and all(r["passed"] is True for r in a3)


def test_d10_pages_and_final_cells_load_as_committed():
    key = yaml.safe_load((D10_DIR / "key.yaml").read_text(encoding="utf-8"))
    dataset = re_.load_d10()
    assert dataset.name == "d10" and dataset.gated is False
    assert dataset.pages_dir == D10_DIR / "pages"
    assert [c.case_id for c in dataset.cases] == sorted(key["pages"])
    assert sum(len(c.cells) for c in dataset.cases) == 112
    for case in dataset.cases:
        entry = key["pages"][case.case_id]
        assert case.page_name == entry["file"] and case.file == D10_DIR / "pages" / entry["file"]
        assert case.cells == entry["cells"] and case.primary == entry["primary"]
        assert sorted(case.targets) == sorted(extract_markets(case.file.read_text(encoding="utf-8")))
    by_id = {c.case_id: c for c in dataset.cases}
    assert by_id["d03"].cells["GBR-PC-02"] == by_id["d09"].cells["GBR-PC-02"] == "NOT_APPLICABLE"  # Kristian, 2026-11-04


def test_d10_key_files_are_outside_the_page_cage():
    dataset = re_.load_d10()
    pages.configure_cage(dataset.pages_dir)
    for name in KEY_FILES:
        assert (D10_DIR / name).is_file()
        with pytest.raises(pages.PathOutsideDatasetError):
            pages.resolve_page_path(f"../{name}")
    for case in dataset.cases:
        pages.read_page(case.page_name)  # every page is readable in the cage


def test_d10_agent_inputs_carry_no_key_material(tmp_path, monkeypatch):
    seen = _capture_ctx(monkeypatch)
    re_.run_series("d10", tmp_path, runs=1)
    ctx = seen["ctx"]
    assert list(ctx.leak_markers) == list(re_.HOLDOUT_FILE_MARKERS)
    # A task is a page name, a market and rule IDs: no verdict, no key field.
    for task in ctx.tasks:
        assert set(task.model_dump()) == {"page_path", "jurisdiction", "ruleset_version", "assigned_rules"}
        assert task.page_path in {c.page_name for c in ctx.dataset.cases}
    # What the reader shows has none of the leak markers, so a real run
    # can only trip them on a true leak.
    pages.configure_cage(ctx.dataset.pages_dir)
    for case in ctx.dataset.cases:
        title, blocks = pages.read_page(case.page_name)
        shown = " ".join([title, *blocks])
        assert not any(m in shown for m in KEY_FILES)


def test_july_unchanged_by_d10(tmp_path, monkeypatch):
    july = re_.load_july()
    assert july.name == "july" and july.pages_dir == re_.JULY_PAGES_DIR
    assert [c.case_id for c in july.cases] == [f"p{n:02d}" for n in range(1, 13)]
    seen = _capture_ctx(monkeypatch)
    re_.run_series("july", tmp_path, runs=1)
    assert seen["ctx"].dataset.name == "july" and seen["ctx"].leak_markers == []
    assert sorted({t.page_path for t in seen["ctx"].tasks}) == [f"p{n:02d}.html" for n in range(1, 13)]


def test_d10_is_development_only(tmp_path):
    with pytest.raises(ValueError, match="never gated"):
        re_.run_series("d10", tmp_path, gated=True)
    with pytest.raises(ValueError, match="--page"):
        re_.run_series("d10", tmp_path, page="d01")
    assert re_.main(["--dataset", "d10", "--gated"]) == re_.EXIT_USAGE
    assert re_.main(["--dataset", "d10", "--real", "--gated", "--holdout-root", str(tmp_path)]) == re_.EXIT_USAGE
    assert not (tmp_path / "runs").exists()
    results_dir = tmp_path / "results"
    _result, _results, out = re_.run_series("d10", tmp_path, runs=1, results_dir=results_dir)
    assert not results_dir.exists() and out.is_relative_to(tmp_path / "runs" / "d10")
