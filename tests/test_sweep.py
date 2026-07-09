"""Permanent, machine-checkable form of the pre-blind filler sweep
(evals/provenance/SWEEP_REPORT.md). Converts the one-off manual grep that
caught the P12 free/deposit collision (fixed at commit fa5d6a1) into a
committed test: every hit of the full trigger pattern on every committed
page must fall inside a spec-specified verbatim string -- an injection,
a distractor, or present furniture (evals/check_pages.py's PAGE_SPECS/
FURNITURE, the single source of truth for what's on a page on purpose).

A hit outside a specified string means either a real residual collision
or a gap in PAGE_SPECS/FURNITURE -- that's Kristian's ruling, not a code
fix. Do not edit a page or PAGE_SPECS to make this test pass; report the
hit instead. 8 such hits were adjudicated 2026-07-09 into
evals/provenance/SWEEP_ALLOWLIST.md rather than folded into PAGE_SPECS --
spec strings stay exactly what was specified at construction time; this
test also treats an allowlist match as coverage, with a staleness guard
so a future page edit that removes the adjudicated content is caught
rather than silently masked.

Lives under tests/, not evals/: this repo's convention is that pytest-
collected tests live under tests/ (test_bounds.py, test_failures.py,
test_pipeline.py), while evals/ hosts eval-dataset tooling invoked
separately, on its own exit-code CLI contract (check_pages.py's own
main(), dev_score.py). This test imports check_pages.py's PAGE_SPECS,
FURNITURE, and extract_text rather than duplicating the per-page
verbatim-string lists, so there is exactly one source of truth for
"what's specified" between the conformance check and the sweep.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from evals.check_pages import FURNITURE, PAGE_SPECS, PAGES_DIR, extract_text

# Full trigger pattern (evals/provenance/SWEEP_REPORT.md "Live sweep"
# section): the historical pre-blind sweep logged only 6 of these terms
# verbatim, with the rest acknowledged but unrecovered from committed
# record (the log entry ends "|..."). This is the full pattern, committed
# as code from this commit forward -- every future page edit is checked
# against it automatically.
SWEEP_PATTERN = re.compile(
    r"guarant|risk[- ]?free|lose nothing|free|last chance|ends (soon|in)|"
    r"hurry|countdown|income|get rich|can'?t lose|no risk",
    re.IGNORECASE,
)

# Adjudicated residuals (evals/provenance/SWEEP_ALLOWLIST.md, Kristian,
# 2026-07-09): hits outside PAGE_SPECS/FURNITURE that are not new rule
# surfaces -- elaboration of an already-adjudicated offer, or content on
# a cell that's already NOT_APPLICABLE. Matched by (page, text) substring
# containment, never by offset (offsets rot as pages change). Spec
# strings themselves are never extended for these -- see that file for
# the per-entry rationale and the hard check against the frozen key.
ALLOWLIST_PATH = Path(__file__).resolve().parent.parent / "evals" / "provenance" / "SWEEP_ALLOWLIST.md"
_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)


def _load_allowlist() -> list[dict]:
    content = ALLOWLIST_PATH.read_text(encoding="utf-8")
    match = _YAML_BLOCK_RE.search(content)
    assert match is not None, f"no ```yaml block found in {ALLOWLIST_PATH}"
    data = yaml.safe_load(match.group(1))
    return data["entries"]


def _specified_strings(page_name: str) -> list[str]:
    """Every verbatim string this page is allowed to contain on purpose:
    injection/distractor strings plus whichever furniture blocks the
    page brief says are present (check_pages.py's PAGE_SPECS/FURNITURE).
    """
    spec = PAGE_SPECS[page_name]
    strings = list(spec["strings"])
    strings.extend(FURNITURE[key] for key in spec["present"])
    return strings


def _covered_spans(text: str, specified: list[str]) -> list[tuple[int, int]]:
    """Every (start, end) span in text where a specified string actually
    occurs -- a string can appear more than once, so find all of them."""
    spans = []
    for s in specified:
        start = 0
        while True:
            idx = text.find(s, start)
            if idx == -1:
                break
            spans.append((idx, idx + len(s)))
            start = idx + 1
    return spans


def _line_around(text: str, start: int, end: int) -> str:
    """A readable slice of text around a hit, bounded by sentence-ish
    stops, for the failure report -- not used for any assertion logic."""
    line_start = text.rfind(".", 0, start)
    line_start = 0 if line_start == -1 else line_start + 1
    line_end = text.find(".", end)
    line_end = len(text) if line_end == -1 else line_end + 1
    return text[line_start:line_end].strip()


def test_sweep_all_hits_inside_specified_strings():
    """Every trigger-pattern hit on every committed page falls inside a
    spec-specified verbatim string (injection/distractor/furniture) OR a
    Kristian-adjudicated allowlist entry (evals/provenance/
    SWEEP_ALLOWLIST.md). Any hit in neither is printed with the page, the
    exact hit, and its surrounding line -- fail loudly, change nothing
    automatically. Allowlist entries are also checked for staleness: an
    entry whose text no longer occurs on its page fails too, so a future
    page edit that removes the adjudicated content doesn't leave a dead
    allowlist entry silently masking coverage.
    """
    allowlist = _load_allowlist()
    unexplained: list[str] = []
    stale_entries: list[str] = []

    texts_by_page = {
        page_name: extract_text((PAGES_DIR / page_name).read_text(encoding="utf-8")) for page_name in PAGE_SPECS
    }

    for entry in allowlist:
        page_text = texts_by_page.get(entry["page"], "")
        if entry["text"] not in page_text:
            stale_entries.append(f"{entry['page']}: allowlist text {entry['text']!r} no longer found on page")

    for page_name, text in texts_by_page.items():
        covered = _covered_spans(text, _specified_strings(page_name))
        covered += _covered_spans(text, [e["text"] for e in allowlist if e["page"] == page_name])

        for match in SWEEP_PATTERN.finditer(text):
            inside_covered = any(c_start <= match.start() and match.end() <= c_end for c_start, c_end in covered)
            if not inside_covered:
                line = _line_around(text, match.start(), match.end())
                unexplained.append(
                    f"{page_name}: hit {match.group(0)!r} at [{match.start()}:{match.end()}] -- {line!r}"
                )

    assert not stale_entries, (
        "stale allowlist entries (text no longer found on page) -- update "
        "or remove from SWEEP_ALLOWLIST.md:\n" + "\n".join(stale_entries)
    )
    assert not unexplained, (
        "unexplained sweep hit(s) -- outside any spec-specified string and "
        "outside the adjudicated allowlist; do not edit the page to fix "
        "this, report to Kristian:\n" + "\n".join(unexplained)
    )
