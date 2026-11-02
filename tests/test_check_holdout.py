"""Generator self-check (eval-gate build check b): evals/check_holdout.py
must accept a valid holdout and stop, writing nothing, on each planted
mistake (evals/v2/SCENARIO_SPEC.md §5). Keyless; the fixture is a
synthetic 30-case holdout built here from the committed rule sets, never
a real holdout. Also checks evals/v2/july_primaries.yaml against the
July pages and the frozen v1.0 key.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from evals.check_holdout import (
    ELLIPSIS, check_holdout, extract, main, normalize, visible_text,
)
from intake.inventory import load_rulesets

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES = {j: [r.rule_id for r in rs] for j, rs in load_rulesets(REPO_ROOT / "rulesets").items()}
# 30 primaries within every mix rule: MLT-GE-01 and DEU-PC-02 left out
# (rule families of 3 allow 2 cases), 8 rules used twice.
REPEATS = ["MLT-BT-01", "MLT-BT-02", "MLT-RG-01", "MLT-PC-02", "DEU-BT-01", "DEU-RG-01", "DEU-PC-03", "GBR-RG-02"]
CASE_RULES = [r for j in ("MLT", "GBR", "DEU") for r in RULES[j] if r not in ("MLT-GE-01", "DEU-PC-02")] + REPEATS
FILLER = " ".join(f"word{n}" for n in range(180))


def _trigger(i: int) -> str:
    return f"alpha{i} bravo{i} charlie{i} delta{i}"


def _case(i: int, rid: str, variant: int | None = None, cls: str | None = None) -> tuple[dict, str]:
    variant = i if variant is None else variant
    cls = f"t{i}" if cls is None else cls
    market = rid.split("-")[0]
    expected = "VIOLATION" if i < 15 else "COMPLIANT" if i < 27 else "NOT_APPLICABLE"
    etype = "none"
    layout = ["p", "heading", "list", "table"][variant % 4]
    if expected == "VIOLATION":
        etype = "absent" if i in (0, 1) else "missing_term" if i == 2 else "text"
    if etype == "absent":
        layout = "none"
    trigger = _trigger(i)
    holder = {
        "p": f"<p>{trigger}</p>",
        "heading": f"<h3>{trigger}</h3>",
        "list": f"<ul><li>{trigger}</li></ul>",
        "table": f"<table><tr><td>{trigger}</td></tr></table>",
        "none": "",
    }[layout]
    page = (
        f"<html><head><title>Page {i}</title></head><body>"
        f"<h1 class='{cls}'>Heading {i}</h1>{holder}<ul><li>item {i}</li></ul>{'<b>x</b>' * variant}"
        f"<p>{FILLER}</p><footer><p>Markets: {market}</p></footer></body></html>"
    )
    cells = {r: "COMPLIANT" for r in RULES[market]}
    cells[rid] = expected
    primary = {
        "rule_id": rid, "expected": expected, "evidence_type": etype,
        "trigger": f"missing notice {i}" if etype == "absent" else trigger,
        "layout": layout, "injection": i in (3, 20),
    }
    if etype in ("text", "missing_term"):
        primary["spans"] = [trigger]
    if etype == "absent":
        primary["required_content"] = [f"required notice {i}"]
        primary["absent_tokens"] = [f"token{i}"]
    case_id = f"h9-{i + 1:02d}"
    return {"file": f"{case_id}.html", "targets": [market], "cells": cells, "primary": primary}, page


def _build(tmp_path: Path, mutate=None) -> Path:
    root = tmp_path / "H9"
    (root / "pages").mkdir(parents=True)
    key = {"holdout": "H9", "pages": {}}
    for i, rid in enumerate(CASE_RULES):
        entry, page = _case(i, rid)
        key["pages"][Path(entry["file"]).stem] = entry
        (root / "pages" / entry["file"]).write_text(page, encoding="utf-8")
    if mutate:
        mutate(root, key)
    (root / "key.yaml").write_text(yaml.safe_dump(key, allow_unicode=True), encoding="utf-8")
    return root


def _page(root: Path, case_id: str) -> Path:
    return root / "pages" / f"{case_id}.html"


def _edit_page(root: Path, case_id: str, old: str, new: str) -> None:
    p = _page(root, case_id)
    p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_valid_fixture_passes_and_writes_manifest(tmp_path):
    root = _build(tmp_path)
    errors, summary = check_holdout(root)
    assert errors == []
    assert summary["cases"] == 30 and summary["violation"] == 15
    assert summary["max_cases_per_family"] == 2
    manifest = tmp_path / "H9.sha256"
    assert main([str(root), "--write-manifest", str(manifest), "--pages-only"]) == 0
    assert len(manifest.read_text(encoding="utf-8").splitlines()) == 30
    assert main([str(root), "--verify-manifest", str(manifest)]) == 0
    _edit_page(root, "h9-05", "</html>", "</html> ")
    assert main([str(root), "--verify-manifest", str(manifest)]) == 1


def _drop_page(root, key):
    _page(root, "h9-04").unlink()


def _rename_file(root, key):
    key["pages"]["h9-04"]["file"] = "h9-05.html"


def _bad_markets(root, key):
    market = key["pages"]["h9-04"]["targets"][0]
    _edit_page(root, "h9-04", f"Markets: {market}", "Markets: ZZZ")


def _missing_cell(root, key):
    cells = key["pages"]["h9-04"]["cells"]
    cells.pop(next(r for r in cells if r != key["pages"]["h9-04"]["primary"]["rule_id"]))


def _bad_verdict(root, key):
    cells = key["pages"]["h9-04"]["cells"]
    cells[next(iter(cells))] = "MAYBE"


def _primary_outside_targets(root, key):
    key["pages"]["h9-04"]["primary"]["rule_id"] = "GBR-GE-01"  # h9-04 targets MLT only


def _primary_differs(root, key):
    key["pages"]["h9-05"]["primary"]["expected"] = "COMPLIANT"


def _span_off_page(root, key):
    key["pages"]["h9-05"]["primary"]["spans"] = ["text that is not on the page at all"]


def _span_twice(root, key):
    _edit_page(root, "h9-05", "</footer>", f"</footer><p>{_trigger(4)}</p>")


def _absent_present(root, key):
    _edit_page(root, "h9-01", "</body>", "<p>required notice 0</p></body>")


def _absent_token_present(root, key):
    _edit_page(root, "h9-01", "</body>", "<p>see token0 here</p></body>")


def _rule_three_times(root, key):
    for cid in ("h9-27", "h9-28"):
        entry = key["pages"][cid]
        old = entry["primary"]["rule_id"]
        entry["targets"] = ["DEU"]
        entry["cells"] = {r: "COMPLIANT" for r in RULES["DEU"]}
        entry["cells"]["DEU-PC-01"] = entry["primary"]["expected"]
        entry["primary"]["rule_id"] = "DEU-PC-01"
        _edit_page(root, cid, f"Markets: {old[:3]}", "Markets: DEU")


def _family_three_times(root, key):
    # GBR-GE-01 and DEU-GE-01 are already primaries; add MLT-GE-01.
    entry = key["pages"]["h9-04"]
    entry["cells"]["MLT-GE-01"], entry["cells"][entry["primary"]["rule_id"]] = (
        entry["primary"]["expected"], "COMPLIANT")
    entry["primary"]["rule_id"] = "MLT-GE-01"


def _shared_trigger(root, key):
    key["pages"]["h9-07"]["primary"]["trigger"] = key["pages"]["h9-06"]["primary"]["trigger"]


def _near_duplicate_trigger(root, key):
    near = f"alpha5 bravo5 charlie5 echo6"
    _edit_page(root, "h9-07", _trigger(6), near)
    key["pages"]["h9-07"]["primary"]["trigger"] = near
    key["pages"]["h9-07"]["primary"]["spans"] = [near]


def _shared_template(root, key):
    entry, page = _case(12, CASE_RULES[12], variant=8, cls="t8")
    (_page(root, "h9-13")).write_text(page, encoding="utf-8")
    key["pages"]["h9-13"] = entry


def _same_shape(root, key):
    entry, page = _case(12, CASE_RULES[12], variant=8, cls="other")
    (_page(root, "h9-13")).write_text(page, encoding="utf-8")
    key["pages"]["h9-13"] = entry


def _leak_word(root, key):
    _edit_page(root, "h9-08", "</body>", "<p>see the answer key</p></body>")


def _layout_lie(root, key):
    key["pages"]["h9-05"]["primary"]["layout"] = "heading"  # trigger sits in a <p>


def _too_few_violations(root, key):
    for cid in ("h9-05", "h9-06", "h9-07"):
        entry = key["pages"][cid]
        entry["primary"].update(expected="COMPLIANT", evidence_type="none")
        entry["primary"].pop("spans", None)
        entry["cells"][entry["primary"]["rule_id"]] = "COMPLIANT"


def _no_injection(root, key):
    for entry in key["pages"].values():
        entry["primary"]["injection"] = False


PLANTED = [
    _drop_page, _rename_file, _bad_markets, _missing_cell, _bad_verdict,
    _primary_outside_targets, _primary_differs, _span_off_page, _span_twice,
    _absent_present, _absent_token_present, _rule_three_times, _family_three_times,
    _shared_trigger, _near_duplicate_trigger, _shared_template, _same_shape,
    _leak_word, _layout_lie, _too_few_violations, _no_injection,
]
EXPECTED_ERROR = {
    "_drop_page": "page file missing",
    "_rename_file": "does not match the case ID",
    "_bad_markets": "Markets footer",
    "_missing_cell": "cells are not exactly",
    "_bad_verdict": "invalid verdict",
    "_primary_outside_targets": "primary rule is not a cell",
    "_primary_differs": "differs from its cell",
    "_span_off_page": "span 0 does not occur exactly once",
    "_span_twice": "span 0 does not occur exactly once",
    "_absent_present": "required_content 0 is present",
    "_absent_token_present": "absent_token 0 is present",
    "_rule_three_times": "DEU-PC-01 is the primary rule of 3",
    "_family_three_times": "rule family",
    "_shared_trigger": "same primary trigger",
    "_near_duplicate_trigger": "nearly the same",
    "_shared_template": "same page template",
    "_same_shape": "same tag sequence",
    "_leak_word": "answer-key wording",
    "_layout_lie": "not inside a heading element",
    "_too_few_violations": "primary violations",
    "_no_injection": "injection cases below spec",
}


@pytest.mark.parametrize("mutate", PLANTED, ids=lambda f: f.__name__.lstrip("_"))
def test_planted_mistake_stops_and_writes_nothing(tmp_path, mutate):
    root = _build(tmp_path, mutate)
    errors, _ = check_holdout(root)
    assert any(EXPECTED_ERROR[mutate.__name__] in e for e in errors), errors
    manifest = tmp_path / "out.sha256"
    assert main([str(root), "--write-manifest", str(manifest)]) == 1
    assert not manifest.exists()


def test_duplicate_case_id_in_key_is_caught(tmp_path):
    root = _build(tmp_path)
    key_text = (root / "key.yaml").read_text(encoding="utf-8")
    first = key_text.index("  h9-01:")
    second = key_text.index("  h9-02:")
    (root / "key.yaml").write_text(key_text + key_text[first:second], encoding="utf-8")
    errors, _ = check_holdout(root)
    assert errors and "duplicate key" in errors[0]


def test_visible_text_follows_the_shared_text_rule():
    html = ("<html><head><title>T</title><style>.x{}</style></head><body>"
            "<h2>50 Free&nbsp;Spins</h2><ul><li>Min deposit &pound;10</li><li>B</li></ul>"
            "<!-- hidden note --><table><tr><td>valid 7 days</td></tr></table>"
            "<div hidden><p>secret <b>bold</b></p></div><template><p>tpl</p></template>"
            "<p>in<b>line</b> T&amp;Cs</p><script>var s='nope';</script></body></html>")
    text = visible_text(html)
    assert text.startswith("t ")
    assert "50 free spins" in text and "min deposit £10 b" in text and "valid 7 days" in text
    assert "inline t&cs" in text
    for gone in ("hidden note", "nope", "secret", "bold", "tpl"):
        assert gone not in text
    assert extract(html).elements["list"] == ["min deposit £10", "b"]


def test_normalize_maps_quotes_dashes_and_format_characters():
    raw = ("Risk" + chr(0x2011) + "free " + chr(0x201E) + "Woche" + chr(0x201C)
           + " soft" + chr(0x00AD) + "hyphen zero" + chr(0x200B) + "width " + chr(0x2026) + " ...")
    assert normalize(raw) == f'risk-free "woche" softhyphen zerowidth {ELLIPSIS} {ELLIPSIS}'


def test_july_primaries_match_pages_and_frozen_key():
    primaries = yaml.safe_load((REPO_ROOT / "evals/v2/july_primaries.yaml").read_text(encoding="utf-8"))["primaries"]
    key = yaml.safe_load((REPO_ROOT / "evals/answer_key.yaml").read_text(encoding="utf-8"))["answer_key"]["pages"]
    assert sorted(primaries) == sorted(key) and len(primaries) == 12
    for page_id, prim in primaries.items():
        assert key[page_id]["cells"][prim["rule_id"]] == prim["expected"], page_id
        html = (REPO_ROOT / "evals/dataset/pages" / f"{page_id}.html").read_text(encoding="utf-8")
        parsed = extract(html)
        text = normalize("".join(parsed.chunks))
        for span in prim.get("spans", []):
            assert text.count(normalize(span)) == 1, (page_id, span)
        if prim["evidence_type"] == "absent":
            for item in prim["required_content"] + prim["absent_tokens"]:
                assert normalize(item) not in text, (page_id, item)
        else:
            trigger = normalize(prim["trigger"])
            assert trigger in text, page_id
            if prim["layout"] != "p":
                assert any(trigger in el for el in parsed.elements[prim["layout"]]), page_id
