"""Generator self-check for a private holdout drawn under
evals/v2/SCENARIO_SPEC.md (eval-gate build check b). Checks the whole
holdout every time: key structure, page/key agreement, the mix rules
(spec §2) and the two independence rules (spec §3). On any failure it
exits 1 and writes nothing.

Prints IDs and counts only, never page text: the holdout stays private
(eval-gate exception, owner, 2026-11-02). Visible text comes from the
shared text rule in intake/textrule.py, which the system's page reader
(agents/checker/pages.py) also uses (RT1-11, P2); check A3 in
evals/run_eval.py compares the reader's output against this text and the
key.

Usage (from the repo root):
  python evals/check_holdout.py HOLDOUT_DIR
  python evals/check_holdout.py HOLDOUT_DIR --write-manifest PATH [--pages-only]
  python evals/check_holdout.py HOLDOUT_DIR --verify-manifest PATH
Exit codes: 0 all checks pass; 1 a check failed; 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intake.inventory import KNOWN_JURISDICTIONS, extract_markets, load_rulesets  # noqa: E402
# Shared text rule (RT1-11): imported, and re-exported for existing callers.
from intake.textrule import (  # noqa: E402,F401
    BLOCK_TAGS,
    ELLIPSIS,
    LAYOUT_TAGS,
    SKIP_TAGS,
    extract,
    normalize,
    visible_text,
)

RULESETS_DIR = REPO_ROOT / "rulesets"

VERDICTS = {"VIOLATION", "COMPLIANT", "NOT_APPLICABLE"}
EVIDENCE_TYPES = {"text", "missing_term", "absent", "none"}
LAYOUTS = {"p", "heading", "list", "table", "none"}
PAGE_ID_RE = re.compile(r"^h\d+-\d{2}$")

# Frozen mix (evals/v2/SCENARIO_SPEC.md §2).
CASES = 30
VIOLATIONS_MIN, VIOLATIONS_MAX = 13, 17
COMPLIANT_MIN = 10
NOT_APPLICABLE_MIN = 3
PER_MARKET_MIN = 8
NARROW_TARGET_PAGES_MIN = 20
PER_CATEGORY_MIN = {"BONUS_TERMS": 5, "PROHIBITED_CLAIMS": 5, "RG_MESSAGING": 5, "GEO_ELIGIBILITY": 2}
PER_RULE_MAX = 2
PER_FAMILY_MAX = 2
TRIGGER_OVERLAP_MAX = 0.6
ABSENT_MIN = 2
NON_P_LAYOUT_MIN = 6
INJECTION_MIN = 2
WORDS_MIN, WORDS_MAX = 150, 450
LEAK_WORDS = ("answer key", "answer_key", "holdout", "primary decision", "expected verdict")


class CheckFailed(Exception):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (plain safe_load
    keeps the last one silently, which would hide a duplicate case ID)."""


def _construct_mapping(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise CheckFailed(f"duplicate key in key file: {key!r}")
        keys.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_rules(rulesets_dir: Path) -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    """({jurisdiction: [rule_id]}, {rule_id: category}, {rule_id: family}).
    A family is the rule's v1.0 sentence (the text before any v1.1 note)
    with the market code removed: rules with the same check in different
    markets share one family. A missing rule set is an error."""
    loaded = load_rulesets(rulesets_dir)
    ids, category, family = {}, {}, {}
    for j in KNOWN_JURISDICTIONS:
        if loaded[j] is None:
            raise CheckFailed(f"rule set for {j} missing or invalid in {rulesets_dir}")
        ids[j] = [r.rule_id for r in loaded[j]]
        for r in loaded[j]:
            category[r.rule_id] = getattr(r.category, "value", r.category)
            first = r.rule_text.split(" Interpretation (v1.1):")[0]
            family[r.rule_id] = normalize(re.sub(r"\b(?:an? )?(?:DEU|GBR|MLT)\b", "X", first))
    return ids, category, family


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text))


def check_holdout(holdout_dir: Path, rulesets_dir: Path = RULESETS_DIR) -> tuple[list[str], dict]:
    """Return (errors, counts). Errors name case IDs and checks only."""
    holdout_dir = Path(holdout_dir)
    errors: list[str] = []
    key_path = holdout_dir / "key.yaml"
    pages_dir = holdout_dir / "pages"
    if not key_path.is_file() or not pages_dir.is_dir():
        return [f"{holdout_dir}: needs key.yaml and pages/"], {}
    try:
        raw = yaml.load(key_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except CheckFailed as exc:
        return [str(exc)], {}
    rules, category_of, family_of = _load_rules(rulesets_dir)

    pages = (raw or {}).get("pages") or {}
    if len(pages) != CASES:
        errors.append(f"case count {len(pages)}, spec requires exactly {CASES}")

    page_files = sorted(p.name for p in pages_dir.glob("*.html"))
    listed_files = [str(entry.get("file", "")) for entry in pages.values()]
    for name in sorted(set(page_files) - set(listed_files)):
        errors.append(f"page file {name} has no key entry")

    counts = Counter()
    per_rule = Counter()
    per_family = Counter()
    per_market = Counter()
    per_category = Counter()
    triggers: dict[str, str] = {}
    templates: dict[tuple, str] = {}
    shapes: dict[tuple, str] = {}

    for case_id, entry in pages.items():
        case_id = str(case_id)
        if not PAGE_ID_RE.match(case_id):
            errors.append(f"{case_id}: case ID does not match h<n>-NN")
        fname = str(entry.get("file", ""))
        if Path(fname).stem != case_id:
            errors.append(f"{case_id}: file {fname!r} does not match the case ID")
        page_path = pages_dir / fname
        if not page_path.is_file():
            errors.append(f"{case_id}: page file missing")
            continue
        html_text = page_path.read_text(encoding="utf-8")
        parsed = extract(html_text)
        text = normalize("".join(parsed.chunks))

        targets = list(entry.get("targets") or [])
        if not targets or len(set(targets)) != len(targets) or not set(targets) <= set(KNOWN_JURISDICTIONS):
            errors.append(f"{case_id}: targets must be 1-3 distinct known markets")
        if len(targets) > 3:
            errors.append(f"{case_id}: more than 3 targets")
        if len(targets) <= 2:
            counts["narrow_target_pages"] += 1
        if sorted(extract_markets(html_text)) != sorted(targets):
            errors.append(f"{case_id}: Markets footer does not match key targets")

        cells = entry.get("cells") or {}
        expected_cells = {rid for j in targets if j in rules for rid in rules[j]}
        if set(cells) != expected_cells:
            errors.append(f"{case_id}: cells are not exactly the 8 rules of each target market")
        for rid, verdict in cells.items():
            if verdict not in VERDICTS:
                errors.append(f"{case_id}: cell {rid} has invalid verdict")

        if not any(parsed.elements["heading"]):
            errors.append(f"{case_id}: page has no heading")
        if not parsed.elements["list"]:
            errors.append(f"{case_id}: page has no list")
        words = len(text.split())
        if not WORDS_MIN <= words <= WORDS_MAX:
            errors.append(f"{case_id}: {words} visible words, spec allows {WORDS_MIN}-{WORDS_MAX}")
        for word in LEAK_WORDS:
            if word in text:
                errors.append(f"{case_id}: page contains answer-key wording")
                break

        signature = tuple(parsed.body_signature)
        shape = tuple(item.split(".", 1)[0] for item in signature)
        if signature in templates:
            errors.append(f"{case_id}: same page template as {templates[signature]}")
        elif shape in shapes:
            errors.append(f"{case_id}: same tag sequence as {shapes[shape]} (classes aside)")
        templates[signature] = case_id
        shapes[shape] = case_id

        primary = entry.get("primary") or {}
        rid = primary.get("rule_id")
        expected = primary.get("expected")
        etype = primary.get("evidence_type")
        layout = primary.get("layout")
        trigger = normalize(str(primary.get("trigger") or ""))
        if rid not in expected_cells:
            errors.append(f"{case_id}: primary rule is not a cell of a target market")
            continue
        if expected not in VERDICTS or cells.get(rid) != expected:
            errors.append(f"{case_id}: primary verdict missing or differs from its cell")
        if etype not in EVIDENCE_TYPES or layout not in LAYOUTS:
            errors.append(f"{case_id}: invalid evidence_type or layout")
        if expected == "VIOLATION" and etype not in ("text", "missing_term", "absent"):
            errors.append(f"{case_id}: a primary violation needs evidence_type text, missing_term or absent")
        if expected != "VIOLATION" and etype != "none":
            errors.append(f"{case_id}: a non-violation primary has evidence_type none")
        if (etype == "absent") != (layout == "none"):
            errors.append(f"{case_id}: layout none is for absent evidence only")

        if not trigger:
            errors.append(f"{case_id}: primary trigger missing")
        elif trigger in triggers:
            errors.append(f"{case_id}: same primary trigger as {triggers[trigger]}")
        else:
            for other, other_id in triggers.items():
                a, b = _words(trigger), _words(other)
                if a and b and len(a & b) / len(a | b) >= TRIGGER_OVERLAP_MAX:
                    errors.append(f"{case_id}: primary trigger nearly the same as {other_id}")
                    break
            triggers[trigger] = case_id
        if etype != "absent" and trigger and trigger not in text:
            errors.append(f"{case_id}: primary trigger not in visible text")
        if layout in LAYOUT_TAGS and trigger and not any(trigger in el for el in parsed.elements[layout]):
            errors.append(f"{case_id}: primary trigger not inside a {layout} element")

        if etype in ("text", "missing_term"):
            spans = [normalize(str(s)) for s in (primary.get("spans") or [])]
            if not spans or not all(spans):
                errors.append(f"{case_id}: {etype} evidence needs at least one span")
            for i, span in enumerate(spans):
                if span and text.count(span) != 1:
                    errors.append(f"{case_id}: span {i} does not occur exactly once in visible text")
        if etype == "absent":
            required = [normalize(str(s)) for s in (primary.get("required_content") or [])]
            if not required or not all(required):
                errors.append(f"{case_id}: absent evidence needs required_content")
            for i, req in enumerate(required):
                if req and req in text:
                    errors.append(f"{case_id}: required_content {i} is present on the page")
            tokens = [normalize(str(s)) for s in (primary.get("absent_tokens") or [])]
            if not tokens or not all(tokens):
                errors.append(f"{case_id}: absent evidence needs absent_tokens")
            for i, tok in enumerate(tokens):
                if tok and tok in text:
                    errors.append(f"{case_id}: absent_token {i} is present on the page")
            counts["absent"] += etype == "absent" and expected == "VIOLATION"

        counts[expected] += 1
        per_rule[rid] += 1
        per_family[family_of[rid]] += 1
        per_market[rid.split("-")[0]] += 1
        per_category[category_of[rid]] += 1
        if layout in ("heading", "list", "table"):
            counts["non_p_layout"] += 1
        if primary.get("injection") is True:
            counts["injection"] += 1
            if expected == "VIOLATION":
                counts["injection_hiding_violation"] += 1

    if not VIOLATIONS_MIN <= counts["VIOLATION"] <= VIOLATIONS_MAX:
        errors.append(f"mix: {counts['VIOLATION']} primary violations, spec {VIOLATIONS_MIN}-{VIOLATIONS_MAX}")
    if counts["COMPLIANT"] < COMPLIANT_MIN:
        errors.append(f"mix: {counts['COMPLIANT']} compliant primaries, spec >= {COMPLIANT_MIN}")
    if counts["NOT_APPLICABLE"] < NOT_APPLICABLE_MIN:
        errors.append(f"mix: {counts['NOT_APPLICABLE']} N/A primaries, spec >= {NOT_APPLICABLE_MIN}")
    for j in KNOWN_JURISDICTIONS:
        if per_market[j] < PER_MARKET_MIN:
            errors.append(f"mix: {j} is primary market of {per_market[j]} cases, spec >= {PER_MARKET_MIN}")
    if counts["narrow_target_pages"] < NARROW_TARGET_PAGES_MIN:
        errors.append(f"mix: {counts['narrow_target_pages']} pages with 1-2 targets, spec >= {NARROW_TARGET_PAGES_MIN}")
    for cat, minimum in PER_CATEGORY_MIN.items():
        if per_category[cat] < minimum:
            errors.append(f"mix: category {cat} has {per_category[cat]} primaries, spec >= {minimum}")
    for rid, n in sorted(per_rule.items()):
        if n > PER_RULE_MAX:
            errors.append(f"independence: {rid} is the primary rule of {n} cases, spec <= {PER_RULE_MAX}")
    for fam, n in per_family.items():
        if n > PER_FAMILY_MAX:
            members = sorted(r for r, f in family_of.items() if f == fam)
            errors.append(f"independence: rule family {'/'.join(members)} has {n} primaries, spec <= {PER_FAMILY_MAX}")
    if counts["absent"] < ABSENT_MIN:
        errors.append(f"mix: {counts['absent']} absent-type violations, spec >= {ABSENT_MIN}")
    if counts["non_p_layout"] < NON_P_LAYOUT_MIN:
        errors.append(f"mix: {counts['non_p_layout']} non-paragraph triggers, spec >= {NON_P_LAYOUT_MIN}")
    if counts["injection"] < INJECTION_MIN or counts["injection_hiding_violation"] < 1:
        errors.append("mix: injection cases below spec (>= 2, >= 1 hiding a violation)")

    summary = {
        "cases": len(pages),
        "violation": counts["VIOLATION"],
        "compliant": counts["COMPLIANT"],
        "not_applicable": counts["NOT_APPLICABLE"],
        "absent_type": counts["absent"],
        "non_p_layout": counts["non_p_layout"],
        "injection": counts["injection"],
        "per_market": dict(sorted(per_market.items())),
        "per_category": dict(sorted(per_category.items())),
        "missing_term": sum(1 for e in pages.values() if (e.get("primary") or {}).get("evidence_type") == "missing_term"),
        "max_cases_per_rule": max(per_rule.values(), default=0),
        "max_cases_per_family": max(per_family.values(), default=0),
        "cells": sum(len(e.get("cells") or {}) for e in pages.values()),
    }
    return errors, summary


def manifest_lines(holdout_dir: Path, pages_only: bool) -> list[str]:
    root = Path(holdout_dir)
    base = root / "pages" if pages_only else root
    files = sorted(p for p in base.rglob("*") if p.is_file())
    lines = []
    for p in files:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.relative_to(root).as_posix()}")
    return lines


def verify_manifest(holdout_dir: Path, manifest_path: Path) -> list[str]:
    listed = [ln for ln in Path(manifest_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not listed or any("  " not in ln for ln in listed):
        return ["manifest file is empty or malformed"]
    pages_only = all(ln.split("  ", 1)[1].startswith("pages/") for ln in listed)
    current = manifest_lines(holdout_dir, pages_only)
    if listed == current:
        return []
    return [f"manifest mismatch: {len(set(listed) ^ set(current))} differing entries"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("holdout_dir", type=Path)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--write-manifest", type=Path)
    group.add_argument("--verify-manifest", type=Path)
    ap.add_argument("--pages-only", action="store_true",
                    help="manifest covers pages/ only (before blind labeling)")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2

    try:
        errors, summary = check_holdout(args.holdout_dir)
    except CheckFailed as exc:
        errors, summary = [str(exc)], {}
    if args.verify_manifest and not errors:
        errors = verify_manifest(args.holdout_dir, args.verify_manifest)

    if errors:
        for err in errors:
            print(f"FAIL {err}")
        print(f"Holdout self-check: FAIL ({len(errors)} errors). Nothing written.")
        return 1
    for k, v in summary.items():
        print(f"{k}: {v}")
    if args.write_manifest:
        lines = manifest_lines(args.holdout_dir, args.pages_only)
        args.write_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.write_manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"manifest: {len(lines)} files written")
    if args.verify_manifest:
        print("manifest: match")
    print("Holdout self-check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
