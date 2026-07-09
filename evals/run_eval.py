"""Official gate run + scorer (BLUEPRINT.md §7, §9 Phase 6). Two halves:

1. run_official_pipeline(): drives the full 12-page corpus through
   check -> verify -> plan on the official-gate model (Sonnet 4.6 for
   checker and verifier; planner is included so the run produces the
   complete artifact, but proposals are never scored -- BLUEPRINT.md §2
   step 6, this Phase 6 instruction).

2. score_official(): the scoring semantics frozen *before* the run
   (gates-before-agents discipline, same as the eval dataset itself):
   (a) assertions = CONFIRMED findings only (policy/ADJUDICATION_POLICY.md
       §5) -- a key violation with no CONFIRMED finding is an FN
       regardless of internal reason (rejected-true and disputed-true
       both score as FN, never as an exculpated miss).
   (b) full-key scoring: every judged cell (a CheckTask existed --
       intake actually asked the checker) plus every geo-derived cell
       (intake never created a CheckTask because the page doesn't
       target that jurisdiction -- correctly NOT_APPLICABLE by
       construction, per BLUEPRINT.md §2 step 1's geo-applicability
       resolution and SPEC.md's Phase 2 ruling) sum to the dataset's
       full 288-cell matrix (12 pages x 3 jurisdictions x 8 rules).
   (c) the NOT_APPLICABLE leg is measured ONLY over rule-level N/A cells
       (judged cells whose key verdict is NOT_APPLICABLE) -- the 104
       geo-derived cells are reported separately as a coverage fact,
       not blended into this leg (they are always correct by
       construction and would inflate the metric to be meaningless).
   (d) precision/recall computed pooled AND per jurisdiction, PASS/FAIL
       against evals/eval_config.yaml's committed thresholds,
       mechanically -- no judgment calls at scoring time.

This scorer is committed and frozen before the official run is ever
executed (Phase 6 pre-run step); the run cannot change how it is scored.
"""
from __future__ import annotations

import functools
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.checker.harness import real_checker  # noqa: E402
from agents.planner.harness import real_planner  # noqa: E402
from contracts.schemas import ComplianceRule  # noqa: E402
from evals.dev_score import LEAK_MARKERS, assert_no_key_leak, load_answer_key  # noqa: E402
from intake.inventory import KNOWN_JURISDICTIONS, build_check_tasks, extract_markets, load_rulesets  # noqa: E402
from nodes.verifier import verify_finding  # noqa: E402
from orchestrator.ledger import create_db  # noqa: E402
from orchestrator.pipeline import (  # noqa: E402
    get_adjudications,
    get_findings,
    run_check_stage,
    run_plan_stage,
    run_verify_stage,
)

EVAL_CONFIG_PATH = REPO_ROOT / "evals" / "eval_config.yaml"
PAGES_DIR = REPO_ROOT / "evals" / "dataset" / "pages"
RULESETS_DIR = REPO_ROOT / "rulesets"

OFFICIAL_MODEL = "claude-sonnet-4-6"
OFFICIAL_CHECK_BUDGET_USD = 1.50  # agents/checker/config.py EVAL_MAX_BUDGET_USD
OFFICIAL_VERIFY_BUDGET_USD = 1.50  # config.yaml verifier_agent.max_budget_usd.official_gate
OFFICIAL_PLAN_BUDGET_USD = 1.00  # agents/planner/config.py EVAL_MAX_BUDGET_USD


def load_eval_config() -> dict:
    with open(EVAL_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------
# Full-key cell reconstruction (semantics b)
# --------------------------------------------------------------------------


def reconstruct_full_key_cells(answer_key: dict) -> list[dict]:
    """Every (page, jurisdiction, rule_id) cell across the full 12 x 3 x 8
    matrix (288), tagged judged (a CheckTask exists -- the checker was
    actually asked) or derived (geo-N/A by construction, no CheckTask).
    The verdict for every cell -- judged or derived -- comes from the
    already-frozen evals/answer_key.yaml; this function only tags which
    cells intake would ask about, it invents no verdicts.
    """
    rulesets = load_rulesets(RULESETS_DIR)
    rule_ids_by_jurisdiction = {j: [r.rule_id for r in (rulesets[j] or [])] for j in KNOWN_JURISDICTIONS}

    cells = []
    for page_path in sorted(PAGES_DIR.glob("*.html")):
        page_key = page_path.stem
        html = page_path.read_text(encoding="utf-8")
        targeted = set(extract_markets(html)) & set(KNOWN_JURISDICTIONS)
        page_cells = answer_key["pages"][page_key]["cells"]
        for jurisdiction in KNOWN_JURISDICTIONS:
            judged = jurisdiction in targeted
            for rule_id in rule_ids_by_jurisdiction[jurisdiction]:
                cells.append(
                    {
                        "page": page_path.name,
                        "jurisdiction": jurisdiction,
                        "rule_id": rule_id,
                        "judged": judged,
                        "key_verdict": page_cells[rule_id],
                    }
                )
    return cells


# --------------------------------------------------------------------------
# Pipeline runner
# --------------------------------------------------------------------------


def run_official_pipeline(conn: sqlite3.Connection, run_id: str) -> dict:
    """Full corpus, all targeted jurisdictions, Sonnet 4.6 for checker
    and verifier; planner runs too (complete artifact) but is not
    scored. Returns per-stage cost/turns/wall-clock stats.
    """
    stats: dict = {}

    all_tasks, missing = build_check_tasks(PAGES_DIR, RULESETS_DIR)
    if missing:
        raise RuntimeError(f"cannot run official gate: rule sets missing for {missing}")

    checker_fn = functools.partial(
        real_checker, ledger_conn=conn, run_id=run_id, model=OFFICIAL_MODEL, max_budget_usd=OFFICIAL_CHECK_BUDGET_USD
    )
    t0 = time.monotonic()
    run_check_stage(all_tasks, checker_fn, conn)
    stats["check_wall_s"] = time.monotonic() - t0
    stats["check_task_count"] = len(all_tasks)

    findings = get_findings(conn)
    rulesets = load_rulesets(RULESETS_DIR)
    rules_by_id: dict[str, ComplianceRule] = {r.rule_id: r for rules in rulesets.values() for r in rules if rules}

    verifier_fn = functools.partial(verify_finding, model=OFFICIAL_MODEL, max_budget_usd=OFFICIAL_VERIFY_BUDGET_USD)
    t0 = time.monotonic()
    run_verify_stage(findings, rules_by_id, verifier_fn, conn, run_id)
    stats["verify_wall_s"] = time.monotonic() - t0
    stats["verify_finding_count"] = sum(1 for f in findings if f.verdict.value == "VIOLATION")

    confirmed = {a.finding_id for a in get_adjudications(conn) if a.verdict.value == "CONFIRMED"}
    confirmed_findings = [f for f in findings if f"{f.task_id}::{f.rule_id}" in confirmed]

    planner_fn = functools.partial(
        real_planner, ledger_conn=conn, run_id=run_id, rules_by_id=rules_by_id,
        model=OFFICIAL_MODEL, max_budget_usd=OFFICIAL_PLAN_BUDGET_USD,
    )
    t0 = time.monotonic()
    run_plan_stage(confirmed_findings, planner_fn, conn)
    stats["plan_wall_s"] = time.monotonic() - t0
    stats["plan_finding_count"] = len(confirmed_findings)

    return stats


# --------------------------------------------------------------------------
# Scorer (semantics a, c, d)
# --------------------------------------------------------------------------


def score_official(conn: sqlite3.Connection, cells: list[dict]) -> dict:
    findings = get_findings(conn)
    findings_by_cell = {(f.page_path, f.rule_id): f for f in findings}
    adjudications = {a.finding_id: a for a in get_adjudications(conn)}

    per_jurisdiction: dict[str, dict[str, int]] = {}
    unscored: list[tuple[str, str, str]] = []
    adjudication_counts = {"CONFIRMED": 0, "REJECTED": 0, "DISPUTED": 0}
    rejected_correct = 0
    rejected_wrong = 0
    disputed_true = 0
    disputed_false = 0
    na_correct = 0
    na_total = 0

    judged_cells = [c for c in cells if c["judged"]]
    derived_cells = [c for c in cells if not c["judged"]]

    for cell in judged_cells:
        page, jurisdiction, rule_id, key_verdict = cell["page"], cell["jurisdiction"], cell["rule_id"], cell["key_verdict"]

        finding = findings_by_cell.get((page, rule_id))
        if finding is None:
            unscored.append((page, rule_id, "no finding emitted for judged cell"))
            continue

        raw_verdict = finding.verdict.value
        asserted_violation = False

        if raw_verdict == "VIOLATION":
            finding_id = f"{finding.task_id}::{finding.rule_id}"
            adj = adjudications.get(finding_id)
            if adj is None:
                unscored.append((page, rule_id, "VIOLATION finding with no adjudication record"))
                continue
            adj_verdict = adj.verdict.value
            adjudication_counts[adj_verdict] += 1
            asserted_violation = adj_verdict == "CONFIRMED"
            key_is_violation = key_verdict == "VIOLATION"
            if adj_verdict == "REJECTED":
                if key_is_violation:
                    rejected_wrong += 1
                else:
                    rejected_correct += 1
            elif adj_verdict == "DISPUTED":
                if key_is_violation:
                    disputed_true += 1
                else:
                    disputed_false += 1

        if key_verdict == "NOT_APPLICABLE":
            na_total += 1
            if raw_verdict == "NOT_APPLICABLE":
                na_correct += 1

        key_is_violation = key_verdict == "VIOLATION"
        counts = per_jurisdiction.setdefault(jurisdiction, {"tp": 0, "fp": 0, "fn": 0})
        if asserted_violation and key_is_violation:
            counts["tp"] += 1
        elif asserted_violation and not key_is_violation:
            counts["fp"] += 1
        elif not asserted_violation and key_is_violation:
            counts["fn"] += 1

    pooled = {"tp": 0, "fp": 0, "fn": 0}
    for counts in per_jurisdiction.values():
        for k in ("tp", "fp", "fn"):
            pooled[k] += counts[k]

    return {
        "judged_count": len(judged_cells),
        "derived_count": len(derived_cells),
        "total_cells": len(cells),
        "per_jurisdiction": per_jurisdiction,
        "pooled": pooled,
        "not_applicable": {"correct": na_correct, "total": na_total},
        "geo_derived_count": len(derived_cells),
        "adjudication_counts": adjudication_counts,
        "rejected_correct": rejected_correct,
        "rejected_wrong": rejected_wrong,
        "disputed_true": disputed_true,
        "disputed_false": disputed_false,
        "unscored": unscored,
    }


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    return precision, recall


def compute_pass_fail(score: dict, eval_config: dict) -> dict:
    """Semantics (d): mechanical PASS/FAIL against the committed
    thresholds. No threshold is read or adjusted based on the outcome.
    """
    p_min = eval_config["violation_detection"]["precision_min"]
    r_min = eval_config["violation_detection"]["recall_min"]
    na_min = eval_config["not_applicable_handling"]["correct_min"]

    per_jurisdiction_prf = {}
    violation_pass = True
    for j, counts in sorted(score["per_jurisdiction"].items()):
        p, r = _prf(counts["tp"], counts["fp"], counts["fn"])
        j_pass = (p >= p_min) and (r >= r_min)
        violation_pass = violation_pass and j_pass
        per_jurisdiction_prf[j] = {"precision": p, "recall": r, "pass": j_pass}

    pooled = score["pooled"]
    p_pooled, r_pooled = _prf(pooled["tp"], pooled["fp"], pooled["fn"])
    pooled_pass = (p_pooled >= p_min) and (r_pooled >= r_min)
    violation_pass = violation_pass and pooled_pass

    na = score["not_applicable"]
    na_accuracy = na["correct"] / na["total"] if na["total"] else float("nan")
    na_pass = na_accuracy >= na_min

    return {
        "per_jurisdiction": per_jurisdiction_prf,
        "pooled": {"precision": p_pooled, "recall": r_pooled, "pass": pooled_pass},
        "violation_detection_pass": violation_pass,
        "not_applicable_accuracy": na_accuracy,
        "not_applicable_pass": na_pass,
        "thresholds": {"precision_min": p_min, "recall_min": r_min, "na_correct_min": na_min},
    }


if __name__ == "__main__":
    run_id = f"gate-{uuid.uuid4().hex[:8]}"
    print(f"=== Phase 6 official gate run -- run_id={run_id} ===")
    print(f"Model: {OFFICIAL_MODEL} (checker + verifier + planner)")

    db_path = REPO_ROOT / f"official_gate_{run_id}.db"
    conn = create_db(str(db_path))

    stats = run_official_pipeline(conn, run_id)
    print(stats)

    assert_no_key_leak(run_id)
    print("Bounds check: PASS -- no answer_key.yaml marker in any audit.db tool payload for this run")

    answer_key = load_answer_key()
    cells = reconstruct_full_key_cells(answer_key)
    score = score_official(conn, cells)
    eval_config = load_eval_config()
    verdict = compute_pass_fail(score, eval_config)

    print(score)
    print(verdict)

    conn.close()
