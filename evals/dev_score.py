"""Phase 3 dev eval leg (BLUEPRINT.md §7, §9): runs the real checker
agent on the dev model (Haiku 4.5, Max plan auth, no API key) over a
configurable page subset, scores its emitted verdicts against
evals/answer_key.yaml -- harness-side only, never inside any agent
prompt -- and reports per-jurisdiction precision/recall for VIOLATION
detection.

Acceptance for this leg (BLUEPRINT.md §9 Phase 3): the leg runs clean --
all tasks terminal, scorer reports plausible numbers. Gate thresholds
(precision >= 0.95, recall >= 0.90) are Phase 6's job, on Sonnet,
official -- this script reports, it does not gate.

Usage:
    python evals/dev_score.py [page.html ...]
    (defaults to 6 pages covering all three jurisdictions if none given)
"""
from __future__ import annotations

import sqlite3
import sys
import time
import uuid
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import agents.checker.harness as harness  # noqa: E402
from agents.checker.config import AUDIT_DB_PATH  # noqa: E402
from agents.checker.select import get_checker_fn  # noqa: E402
from intake.inventory import build_check_tasks  # noqa: E402
from orchestrator.ledger import create_db  # noqa: E402
from orchestrator.pipeline import get_findings, run_check_stage  # noqa: E402

ANSWER_KEY_PATH = REPO_ROOT / "evals" / "answer_key.yaml"

# Markers that could only appear in an audit.db payload if answer_key.yaml
# itself (its filename, or its frozen-status wording) leaked into what the
# agent saw. Deliberately not the verdict words themselves (COMPLIANT /
# VIOLATION / NOT_APPLICABLE) -- the agent legitimately produces those as
# its own output, so matching them would be a false-positive-prone check,
# not proof of a leak (same reasoning the shipped verifier's bounds test
# uses for ground_truth.json).
LEAK_MARKERS = ["answer_key", "FROZEN (adjudicated", "ADJUDICATION_LOG"]

DEFAULT_PAGES = ["p01.html", "p02.html", "p03.html", "p04.html", "p05.html", "p06.html"]


def load_answer_key() -> dict:
    """HARNESS-SIDE ONLY: called here, in the scorer, never from inside
    agents/checker/. assert_no_key_leak() below is what proves the
    agent never saw it."""
    with open(ANSWER_KEY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["answer_key"]


def assert_no_key_leak(run_id: str) -> None:
    """Bounds check (BLUEPRINT.md §7): every tool_input/tool_response this
    run logged must be free of answer-key markers. This is the harness-
    side guarantee the dev leg's numbers mean anything at all."""
    if not AUDIT_DB_PATH.exists():
        raise RuntimeError(f"no audit.db at {AUDIT_DB_PATH} -- cannot verify no key leak")
    conn = sqlite3.connect(AUDIT_DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, payload FROM tool_calls WHERE run_id = ?", (run_id,)
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        raise RuntimeError(f"no tool_calls rows for run_id={run_id!r} -- cannot verify no key leak")
    for row_id, payload in rows:
        for marker in LEAK_MARKERS:
            if marker in payload:
                raise AssertionError(
                    f"BOUNDS VIOLATION: answer-key marker {marker!r} found in "
                    f"audit.db tool_calls row {row_id} (run_id={run_id}) -- "
                    "the answer key leaked into agent input/output."
                )


def score(pages: list[str]) -> None:
    run_id = f"dev-{uuid.uuid4().hex[:8]}"
    print(f"=== Phase 3 dev eval leg -- run_id={run_id} ===")
    print("Model: dev leg (Haiku 4.5, Max plan auth, no per-token API key)")
    print(f"Pages: {pages}")
    print()

    db_path = REPO_ROOT / f"dev_score_{run_id}.db"
    conn = create_db(str(db_path))

    all_tasks, missing = build_check_tasks(REPO_ROOT / "evals" / "dataset" / "pages", REPO_ROOT / "rulesets")
    if missing:
        raise RuntimeError(f"cannot run dev leg: rule sets missing for {missing}")
    tasks = [t for t in all_tasks if t.page_path in pages]
    if not tasks:
        raise RuntimeError(f"no CheckTasks found for pages: {pages}")

    print(f"CheckTasks to run: {len(tasks)}")
    for t in tasks:
        print(f"  {t.page_path} x {t.jurisdiction} ({len(t.assigned_rules)} rules)")
    print()

    total_cost = 0.0
    total_turns = 0
    real_checker = get_checker_fn(conn, run_id=run_id, mode="real")

    def checker_fn(task):
        nonlocal total_cost, total_turns
        result = real_checker(task)
        if harness.last_result is not None:
            total_cost += harness.last_result.total_cost_usd or 0.0
            total_turns += harness.last_result.num_turns or 0
        return result

    start = time.monotonic()
    run_check_stage(tasks, checker_fn, conn)
    elapsed = time.monotonic() - start

    terminal = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM task_ledger WHERE stage='check' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED')"
    ).fetchone()[0]

    print(f"=== Run complete in {elapsed:.1f}s ===")
    print(f"Tasks terminal: {terminal}/{len(tasks)}  (zero lost: {terminal == len(tasks)})")
    for state, n in conn.execute(
        "SELECT state, COUNT(*) FROM task_ledger WHERE stage='check' "
        "AND state IN ('DONE','FAILED','DEAD_LETTER','ESCALATED') GROUP BY state"
    ):
        print(f"  {state}: {n}")
    print()

    assert_no_key_leak(run_id)
    print("Bounds check: no answer_key.yaml marker found in any audit.db tool payload for this run. PASS")
    print()

    answer_key = load_answer_key()
    findings = get_findings(conn)

    per_jurisdiction: dict[str, dict[str, int]] = {}
    scored = 0
    unscored: list[tuple[str, str]] = []

    for f in findings:
        if f.page_path not in pages:
            continue
        page_key = f.page_path.removesuffix(".html")
        cell_verdict = answer_key["pages"].get(page_key, {}).get("cells", {}).get(f.rule_id)
        if cell_verdict is None:
            unscored.append((f.page_path, f.rule_id))
            continue
        scored += 1
        predicted_violation = f.verdict.value == "VIOLATION"
        actual_violation = cell_verdict == "VIOLATION"
        counts = per_jurisdiction.setdefault(f.jurisdiction, {"tp": 0, "fp": 0, "fn": 0})
        if predicted_violation and actual_violation:
            counts["tp"] += 1
        elif predicted_violation and not actual_violation:
            counts["fp"] += 1
        elif not predicted_violation and actual_violation:
            counts["fn"] += 1

    print(f"Scored {scored} findings against answer_key.yaml ({len(unscored)} unscored)")
    if unscored:
        print(f"  unscored (no matching cell): {unscored}")
    print()
    print(f"{'Jurisdiction':<14}{'TP':>4}{'FP':>4}{'FN':>4}{'Precision':>12}{'Recall':>10}")
    pooled = {"tp": 0, "fp": 0, "fn": 0}
    for j, counts in sorted(per_jurisdiction.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        print(f"{j:<14}{tp:>4}{fp:>4}{fn:>4}{precision:>12.3f}{recall:>10.3f}")
        pooled["tp"] += tp
        pooled["fp"] += fp
        pooled["fn"] += fn

    p_pooled = pooled["tp"] / (pooled["tp"] + pooled["fp"]) if (pooled["tp"] + pooled["fp"]) else float("nan")
    r_pooled = pooled["tp"] / (pooled["tp"] + pooled["fn"]) if (pooled["tp"] + pooled["fn"]) else float("nan")
    print(f"{'POOLED':<14}{pooled['tp']:>4}{pooled['fp']:>4}{pooled['fn']:>4}{p_pooled:>12.3f}{r_pooled:>10.3f}")
    print()
    print(f"Total cost: ${total_cost:.4f}   Total turns: {total_turns}   Avg turns/task: {total_turns / len(tasks):.1f}")
    print()
    print("Dev leg only (Haiku, no gate thresholds enforced here).")
    print("Gate thresholds (precision >= 0.95, recall >= 0.90) are Phase 6's job, on Sonnet, official.")

    conn.close()


if __name__ == "__main__":
    score(sys.argv[1:] or DEFAULT_PAGES)
