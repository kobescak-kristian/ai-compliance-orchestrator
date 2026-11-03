"""Eval runner and grader for gate v2 (evals/eval_config.yaml; repair
program P-001, P2: D2 and D9). Replaces the v1.0 runner, which is in Git
history (last at commit 35323ab) with the July FAIL it produced.

One call runs one series on one dataset:
  - the July development set (evals/dataset/pages/, key v1.0, primaries
    in evals/v2/july_primaries.yaml): reported, never gated;
  - a private holdout H<n> under holdout_root (config.local.yaml or
    --holdout-root): manifest check and self-check first, then A3, then
    N runs.

Each run gets a fresh ledger DB and audit DBs under
holdout_root/runs/<dataset>/<series_id>/run<k>/ (gate overall.
runs_independent). Nothing is written inside the repository or a holdout
folder; the storage guard refuses such paths. Holdout pages are served
through the checker cage's alias map, so agents never see a case ID.

Default mode is stub (no model call). --real runs the caged agents and
the pinned verifier; it needs the owner's paid-run authorization and is
not used in P2.

Usage (from the repo root):
  python evals/run_eval.py --dataset july [--runs N] [--holdout-root PATH]
  python evals/run_eval.py --dataset H2 [--runs N] [--holdout-root PATH] [--real [--gated]]
Exit codes: 0 completed series (PASS or FAIL); 2 INVALID RUN;
3 NOT ENOUGH CASES; 64 usage error. Console output is IDs and counts
only, never page text or private paths.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.checker import audit as checker_audit  # noqa: E402
from agents.checker import pages  # noqa: E402
from agents.checker import stub as checker_stub  # noqa: E402
from agents.checker.config import QUALIFIED_TOOL_NAMES as CHECKER_TOOLS  # noqa: E402
from agents.planner import audit as planner_audit  # noqa: E402
from agents.planner import stub as planner_stub  # noqa: E402
from agents.planner.config import QUALIFIED_TOOL_NAMES as PLANNER_TOOLS  # noqa: E402
from agents.planner.config import TOOL_NAMES as PLANNER_TOOL_NAMES  # noqa: E402
from contracts.schemas import CheckTask, ComplianceRule  # noqa: E402
from evals import check_holdout  # noqa: E402
from evals.dev_score import assert_no_key_leak  # noqa: E402
from intake.inventory import KNOWN_JURISDICTIONS, extract_markets, load_rulesets  # noqa: E402
from intake.local_config import load_local_config  # noqa: E402
from intake.textrule import excerpt_on_page, excerpt_parts, extract, is_absent_excerpt, normalize, visible_text  # noqa: E402
from nodes import verifier_stub  # noqa: E402
from orchestrator.ledger import create_db  # noqa: E402
from orchestrator.pipeline import (  # noqa: E402
    TERMINAL_STATES,
    get_adjudications,
    get_findings,
    run_check_stage,
    run_plan_stage,
    run_verify_stage,
)

EVAL_CONFIG_PATH = REPO_ROOT / "evals" / "eval_config.yaml"
RULESETS_DIR = REPO_ROOT / "rulesets"
JULY_PAGES_DIR = REPO_ROOT / "evals" / "dataset" / "pages"
JULY_KEY_PATH = REPO_ROOT / "evals" / "answer_key.yaml"
JULY_PRIMARIES_PATH = REPO_ROOT / "evals" / "v2" / "july_primaries.yaml"
MANIFEST_DIR = REPO_ROOT / "evals" / "v2" / "holdouts"
RESULTS_DIR = REPO_ROOT / "evals" / "results"

CASE_ID_PATTERN = r"\bh\d+-\d\d\b"
HOLDOUT_FILE_MARKERS = ("key.yaml", "briefs.md", "adjudication.md")
HOLDOUT_ID_RE = re.compile(r"^H\d+$")

EXIT_COMPLETED, EXIT_INVALID_RUN, EXIT_NOT_ENOUGH_CASES, EXIT_USAGE = 0, 2, 3, 64
PASS, FAIL, INVALID_RUN, NOT_ENOUGH_CASES = "PASS", "FAIL", "INVALID RUN", "NOT ENOUGH CASES"
EXIT_FOR = {PASS: EXIT_COMPLETED, FAIL: EXIT_COMPLETED, INVALID_RUN: EXIT_INVALID_RUN, NOT_ENOUGH_CASES: EXIT_NOT_ENOUGH_CASES}


class InvalidRun(Exception):
    """A gate INVALID RUN condition (result_rules.INVALID_RUN)."""


class NotEnoughCases(Exception):
    """Fewer valid cases than the gate's min_cases at series start."""


class StorageError(InvalidRun):
    """An output path inside the repository or a holdout folder."""


def load_eval_config() -> dict:
    return yaml.safe_load(EVAL_CONFIG_PATH.read_text(encoding="utf-8"))


def lf_sha256(path: Path) -> str:
    """SHA-256 of a file's content with LF line endings (as Git stores it)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------


@dataclass
class Case:
    case_id: str
    page_name: str  # the name agents see (alias for a holdout)
    file: Path  # the real page file
    targets: list[str]
    cells: dict[str, str]  # rule_id -> key verdict, target markets only
    primary: dict


@dataclass
class Dataset:
    name: str
    gated: bool
    pages_dir: Path
    cases: list[Case]
    holdout_dir: Path | None = None
    aliases: dict[str, str] = field(default_factory=dict)

    def case_for_page(self, page_name: str) -> Case:
        return next(c for c in self.cases if c.page_name == page_name)


def load_july() -> Dataset:
    key = yaml.safe_load(JULY_KEY_PATH.read_text(encoding="utf-8"))["answer_key"]["pages"]
    primaries = yaml.safe_load(JULY_PRIMARIES_PATH.read_text(encoding="utf-8"))["primaries"]
    cases = []
    for case_id, primary in sorted(primaries.items()):
        entry = key[case_id]
        targets = list(entry["targets"])
        cells = {r: v for r, v in entry["cells"].items() if r.split("-")[0] in targets}
        name = f"{case_id}.html"
        cases.append(Case(case_id, name, JULY_PAGES_DIR / name, targets, cells, dict(primary)))
    return Dataset("july", False, JULY_PAGES_DIR, cases)


def load_holdout(holdout_root: Path, holdout_id: str) -> Dataset:
    holdout_dir = Path(holdout_root) / holdout_id
    key = yaml.safe_load((holdout_dir / "key.yaml").read_text(encoding="utf-8")) or {}
    pages_dir = holdout_dir / "pages"
    cases, aliases = [], {}
    for n, (case_id, entry) in enumerate(sorted((key.get("pages") or {}).items()), start=1):
        alias = f"page{n:02d}.html"
        aliases[alias] = entry["file"]
        targets = list(entry["targets"])
        cases.append(Case(str(case_id), alias, pages_dir / entry["file"], targets, dict(entry["cells"]), dict(entry["primary"])))
    return Dataset(holdout_id, True, pages_dir, cases, holdout_dir, aliases)


# --------------------------------------------------------------------------
# Storage guard
# --------------------------------------------------------------------------


def guard_output_path(path: Path, holdout_root: Path, holdout_dirs: list[Path]) -> Path:
    """Refuse any run output outside holdout_root/runs, inside the
    repository or inside a holdout folder (P2 storage requirement), or
    inside any other Git work tree (P3)."""
    resolved = Path(path).resolve()
    runs_root = (Path(holdout_root) / "runs").resolve()
    if resolved.is_relative_to(REPO_ROOT.resolve()):
        raise StorageError("refusing run output inside the repository")
    if any((p / ".git").exists() for p in (resolved, *resolved.parents)):
        raise StorageError("refusing run output inside a Git work tree")
    for d in holdout_dirs:
        if resolved.is_relative_to(Path(d).resolve()):
            raise StorageError("refusing run output inside a holdout folder")
    if not resolved.is_relative_to(runs_root):
        raise StorageError("run output must be under holdout_root/runs")
    return resolved


def holdout_folders(holdout_root: Path) -> list[Path]:
    root = Path(holdout_root)
    return [p for p in root.iterdir() if p.is_dir() and HOLDOUT_ID_RE.match(p.name)] if root.is_dir() else []


# --------------------------------------------------------------------------
# A3: reader visibility (keyless, before the series)
# --------------------------------------------------------------------------


def reader_text(page_name: str) -> str:
    """Normalized text of what fetch_page shows an agent (title + blocks)."""
    title, blocks = pages.read_page(page_name)
    return normalize(" ".join([title, *blocks]))


def a3_checks(dataset: Dataset) -> list[dict]:
    """Component A3 (gate a3_reader_visibility). Counts are failures."""
    blocks_missing = triggers_missing = absent_present = 0
    for case in dataset.cases:
        shown = reader_text(case.page_name)
        parsed = extract(case.file.read_text(encoding="utf-8"))
        blocks_missing += sum(1 for b in parsed.blocks if normalize(b) not in shown)
        primary = case.primary
        etype = primary.get("evidence_type")
        wanted = [str(s) for s in primary.get("spans") or []]
        if etype != "absent" and primary.get("trigger"):
            wanted.append(str(primary["trigger"]))
        triggers_missing += sum(1 for s in wanted if normalize(s) not in shown)
        if etype == "absent":
            forbidden = [*(primary.get("required_content") or []), *(primary.get("absent_tokens") or [])]
            absent_present += sum(1 for s in forbidden if normalize(str(s)) in shown)
    return [
        {"check_name": "a3_grader_blocks_in_reader", "run_index": 0, "passed": blocks_missing == 0, "count": blocks_missing},
        {"check_name": "a3_triggers_and_spans_in_reader", "run_index": 0, "passed": triggers_missing == 0, "count": triggers_missing},
        {"check_name": "a3_absent_content_not_in_reader", "run_index": 0, "passed": absent_present == 0, "count": absent_present},
    ]


# --------------------------------------------------------------------------
# A2: run-derived checks (one run's ledger and audit DBs, no model call)
# --------------------------------------------------------------------------


def _row(name: str, run_index: int, failures: int | None) -> dict:
    """passed is None when the check cannot run in this mode."""
    return {"check_name": name, "run_index": run_index, "passed": None if failures is None else failures == 0,
            "count": failures}


def planner_integrity(conn: sqlite3.Connection, run_id: str, page_text_for) -> list[tuple[str, int]]:
    """Gate a2_run_derived.planner_integrity; (check, failures) pairs.
    proposals do not persist evidence_refs; a proposal resolves to its
    finding by page_path + rule_id (the rule_id encodes the market, so
    this is the same finding as task_id + '::' + rule_id)."""
    findings = {(f.page_path, f.rule_id): f for f in get_findings(conn)}
    adjudications = {a.finding_id: a for a in get_adjudications(conn)}
    proposals = conn.execute(
        "SELECT page_path, rule_id, offending_text, proposed_text, status FROM proposals"
    ).fetchall()

    def confirmed(f) -> bool:
        a = adjudications.get(f"{f.task_id}::{f.rule_id}")
        return a is not None and a.verdict.value == "CONFIRMED" and a.run_id == run_id

    per_cell: dict[tuple[str, str], int] = {}
    not_pending = unresolved = offending_mismatch = off_page = bad_proposed = 0
    for page_path, rule_id, offending, proposed, status in proposals:
        per_cell[(page_path, rule_id)] = per_cell.get((page_path, rule_id), 0) + 1
        not_pending += status != "PENDING"
        f = findings.get((page_path, rule_id))
        if f is None or f.verdict.value != "VIOLATION" or not confirmed(f):
            unresolved += 1
            continue
        offending_mismatch += offending != f.evidence_excerpt
        text_based = not is_absent_excerpt(f.evidence_excerpt)
        if text_based and not excerpt_on_page(offending, page_text_for(page_path)):
            off_page += 1
        if not proposed.strip() or (text_based and proposed.strip() == offending.strip()):
            bad_proposed += 1
    confirmed_cells = {k for k, f in findings.items() if f.verdict.value == "VIOLATION" and confirmed(f)}
    one_each = sum(1 for k in confirmed_cells if per_cell.get(k, 0) != 1)
    whitelist = sum(1 for n in PLANNER_TOOL_NAMES if re.search(r"approv|reject|status", n, re.I))
    return [
        ("planner_one_pending_proposal_per_confirmed", one_each + not_pending),
        ("planner_proposal_resolves_to_confirmed_finding", unresolved),
        ("planner_offending_text_equals_excerpt", offending_mismatch),
        ("planner_offending_text_on_page", off_page),
        ("planner_proposed_text_valid", bad_proposed),
        ("planner_no_status_tool", whitelist),
    ]


def resume_check(db_path: Path, run_dir: Path, tasks, rules_by_id, run_id: str) -> int:
    """Rerun all stages on a copy of the ledger with functions that count
    calls and never call a model; failures = calls + rows added."""
    copy = run_dir / "resume_check.db"
    shutil.copyfile(db_path, copy)
    conn = sqlite3.connect(copy)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

        def total_rows() -> int:
            return sum(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables)

        before = total_rows()
        calls = 0

        def guarded(*_args, **_kw):
            nonlocal calls
            calls += 1
            raise RuntimeError("resume check: a model function was called")

        run_check_stage(tasks, guarded, conn)
        findings = get_findings(conn)
        run_verify_stage(findings, rules_by_id, guarded, conn, run_id)
        run_plan_stage(_confirmed(conn, findings), guarded, conn)
        return calls + (total_rows() - before)
    finally:
        conn.close()
        copy.unlink(missing_ok=True)


def a2_checks(ctx: "RunContext") -> list[dict]:
    conn, k = ctx.conn, ctx.run_index
    rows: list[dict] = []

    expected = {(c.page_name, r) for c in ctx.dataset.cases for r in c.cells}
    assigned: dict[tuple[str, str], int] = {}
    for t in ctx.tasks:
        for r in t.assigned_rules:
            assigned[(t.page_path, r)] = assigned.get((t.page_path, r), 0) + 1
    coverage = sum(1 for cell in expected if assigned.get(cell, 0) != 1) + len(set(assigned) - expected)
    rows.append(_row("coverage_each_rule_in_one_task", k, coverage))

    latest = conn.execute(
        "SELECT t.task_id, t.stage, t.state FROM task_ledger t JOIN "
        "(SELECT task_id, stage, MAX(id) AS id FROM task_ledger GROUP BY task_id, stage) m ON t.id = m.id"
    ).fetchall()
    not_terminal = sum(1 for _t, _s, state in latest if state not in TERMINAL_STATES)
    check_ids = {t for t, s, _ in latest if s == "check"}
    lost = sum(1 for t in ctx.tasks if f"{t.page_path}::{t.jurisdiction}" not in check_ids)
    rows.append(_row("every_task_terminal_zero_lost", k, not_terminal + lost))

    findings = get_findings(conn)
    done = {t for t, s, state in latest if s == "check" and state == "DONE"}
    by_task: dict[str, list[str]] = {}
    for f in findings:
        by_task.setdefault(f.task_id, []).append(f.rule_id)
    one_per_rule = sum(
        1 for t in ctx.tasks
        if f"{t.page_path}::{t.jurisdiction}" in done
        and sorted(by_task.get(f"{t.page_path}::{t.jurisdiction}", [])) != sorted(t.assigned_rules)
    )
    rows.append(_row("done_task_one_finding_per_rule", k, one_per_rule))

    versions = {j: (rules[0].ruleset_version if rules else None) for j, rules in ctx.rulesets.items()}
    bad_citation = sum(
        1 for f in findings
        if f.rule_id not in ctx.rules_by_id or ctx.rules_by_id[f.rule_id].jurisdiction != f.jurisdiction
        or f.ruleset_version != versions.get(f.jurisdiction)
    )
    rows.append(_row("finding_cites_own_ruleset_and_version", k, bad_citation))

    recorded = ctx.config["datasets"]["ruleset_sha256"]
    rows.append(_row("ruleset_sha256_matches_gate", k, sum(
        1 for rel, digest in recorded.items() if lf_sha256(REPO_ROOT / rel) != digest
    )))

    if ctx.real:
        audit = sqlite3.connect(ctx.audit_db)
        try:
            audited = {r[0] for r in audit.execute("SELECT DISTINCT task_id FROM tool_calls WHERE run_id = ?", (ctx.run_id,))}
            names = {r[0] for r in audit.execute("SELECT DISTINCT tool_name FROM tool_calls WHERE run_id = ?", (ctx.run_id,))}
        finally:
            audit.close()
        rows.append(_row("independence_model_call_per_task", k, sum(
            1 for t in ctx.tasks if f"{t.page_path}::{t.jurisdiction}" not in audited
        )))
        rows.append(_row("audit_tools_whitelisted", k, len(names - set(CHECKER_TOOLS) - set(PLANNER_TOOLS))))
        # Checker and planner audit DB, plus the verifier's own audit DB
        # (same tool_calls schema; it exists only if the verifier ran).
        leak = 0
        verifier_db = ctx.run_dir / "verifier_audit.db"
        for db in (ctx.audit_db, *([verifier_db] if verifier_db.is_file() else [])):
            try:
                assert_no_key_leak(ctx.run_id, db_path=db, extra_markers=ctx.leak_markers, patterns=[CASE_ID_PATTERN])
            except (AssertionError, RuntimeError):  # a leak, or no rows to verify
                leak += 1
        rows.append(_row("no_key_or_holdout_marker", k, leak))
        from nodes.verifier import VerifierConfigError, check_verifier_checkout

        try:
            check_verifier_checkout()
            pin = 0
        except VerifierConfigError:
            pin = 1
        rows.append(_row("verifier_pinned_and_clean_after_run", k, pin))
    else:
        for name in ("independence_model_call_per_task", "audit_tools_whitelisted",
                     "no_key_or_holdout_marker", "verifier_pinned_and_clean_after_run"):
            rows.append(_row(name, k, None))  # audit-based: not run in stub mode

    try:
        resume_failures = resume_check(ctx.db_path, ctx.run_dir, ctx.tasks, ctx.rules_by_id, ctx.run_id)
    except Exception as exc:  # noqa: BLE001 -- RT2-04: a crash of system code here is a failed resume, scored as is
        if _raised_in_runner(exc):
            raise
        resume_failures = 1
    rows.append(_row("resume_zero_calls_zero_rows", k, resume_failures))
    for name, failures in planner_integrity(conn, ctx.run_id, ctx.page_text):
        rows.append(_row(name, k, failures))
    return rows


# --------------------------------------------------------------------------
# B: evidence grading and case/page scoring
# --------------------------------------------------------------------------


def grade_evidence(excerpt: str, core_span: str, page_text: str) -> str | None:
    """Gate evidence_grading for a text-type key cell. None = pass, else
    the miss category."""
    if is_absent_excerpt(excerpt):
        return "ABSENT_ON_TEXT"
    parts = excerpt_parts(excerpt)
    if not parts or any(p not in page_text for p in parts):
        return "OFF_PAGE"
    core = normalize(core_span)
    if sum(len(p) for p in parts) > max(200, 2 * len(core)):
        return "TOO_LONG"
    start = page_text.find(core)
    need = min(15, len(core))
    if start >= 0:
        end = start + len(core)
        for p in parts:
            i = page_text.find(p)
            while i >= 0:
                if min(end, i + len(p)) - max(start, i) >= need:
                    return None
                i = page_text.find(p, i + 1)
    return "NO_OVERLAP"


@dataclass
class CellOutcome:
    decided: bool
    asserted: bool
    verdict: str | None  # the finding's verdict
    adjudication: str | None
    excerpt: str | None


def cell_outcomes(conn: sqlite3.Connection, tasks: list[CheckTask]) -> dict[tuple[str, str], CellOutcome]:
    """Per (page_name, rule_id): decided iff the check task is DONE and has
    a finding for the rule (gate component_b.decided)."""
    latest_check = dict(conn.execute(
        "SELECT t.task_id, t.state FROM task_ledger t JOIN (SELECT task_id, MAX(id) AS id FROM task_ledger "
        "WHERE stage = 'check' GROUP BY task_id) m ON t.id = m.id"
    ).fetchall())
    findings = {(f.page_path, f.rule_id): f for f in get_findings(conn)}
    adjudications = {a.finding_id: a.verdict.value for a in get_adjudications(conn)}
    out = {}
    for t in tasks:
        done = latest_check.get(f"{t.page_path}::{t.jurisdiction}") == "DONE"
        for r in t.assigned_rules:
            f = findings.get((t.page_path, r))
            if not done or f is None:
                out[(t.page_path, r)] = CellOutcome(False, False, None, None, None)
                continue
            adj = adjudications.get(f"{f.task_id}::{f.rule_id}") if f.verdict.value == "VIOLATION" else None
            out[(t.page_path, r)] = CellOutcome(True, adj == "CONFIRMED", f.verdict.value, adj, f.evidence_excerpt)
    return out


def primary_miss(case: Case, cell: CellOutcome | None, page_text: str) -> str | None:
    """Gate primary_decision_passes_in_a_run_iff. None = pass."""
    if cell is None or not cell.decided:
        return "NOT_DECIDED"
    expected = case.primary["expected"]
    if expected != "VIOLATION":
        return "ASSERTED_ON_NON_VIOLATION" if cell.asserted else None
    if not cell.asserted:
        if cell.adjudication in ("DISPUTED", "REJECTED"):
            return cell.adjudication
        return "NOT_ASSERTED"
    etype = case.primary.get("evidence_type")
    if etype == "absent":
        return None
    core = str((case.primary.get("spans") or [""])[0])
    if etype == "missing_term" and is_absent_excerpt(cell.excerpt or ""):
        return None
    return grade_evidence(cell.excerpt or "", core, page_text)


def off_target_error(key_verdict: str, cell: CellOutcome | None) -> str | None:
    """Gate off_target_guardrail.material_error; None = no material error."""
    if cell is None or not cell.decided:
        return "undecided"
    if cell.asserted and key_verdict != "VIOLATION":
        return "false_alarm"
    if key_verdict == "VIOLATION" and not cell.asserted:
        return "missed"
    return None


def score_series(dataset: Dataset, runs: list[dict], config: dict) -> dict:
    """Component B over all runs, plus the diagnostics aggregates."""
    b = config["component_b"]
    allowed_failing = b["claim"]["allowed_failing_cases"]
    max_unclean = b["off_target_guardrail"]["max_unclean_pages"]
    per_case, per_page = [], []
    failing_cases = unclean_pages = 0
    tp = fp = fn = na_total = na_right = 0
    adj_counts = {"CONFIRMED": 0, "REJECTED": 0, "DISPUTED": 0}
    rejected_correct = rejected_wrong = flips = 0
    for case in dataset.cases:
        page_text = visible_text(case.file.read_text(encoding="utf-8"))
        rid = case.primary["rule_id"]
        case_ok = True
        for k, run in enumerate(runs, start=1):
            miss = primary_miss(case, run["cells"].get((case.page_name, rid)), page_text)
            case_ok = case_ok and miss is None
            per_case.append({"case_id": case.case_id, "jurisdiction": rid.split("-")[0], "rule_id": rid,
                             "run_index": k, "passed": miss is None, "miss_category": miss})
        failing_cases += not case_ok
        counts = {"false_alarm": 0, "missed": 0, "undecided": 0}
        one_off = repeated = 0
        for r, key_verdict in case.cells.items():
            outcomes = [run["cells"].get((case.page_name, r)) for run in runs]
            flips += len({(o.decided, o.asserted, o.verdict) if o else None for o in outcomes}) > 1
            for o in outcomes:
                if o is not None and o.decided:
                    tp += o.asserted and key_verdict == "VIOLATION"
                    fp += o.asserted and key_verdict != "VIOLATION"
                    if o.adjudication:
                        adj_counts[o.adjudication] += 1
                        if o.adjudication == "REJECTED":
                            rejected_correct += key_verdict != "VIOLATION"
                            rejected_wrong += key_verdict == "VIOLATION"
                    if key_verdict == "NOT_APPLICABLE":
                        na_total += 1
                        na_right += o.verdict == "NOT_APPLICABLE"
                fn += key_verdict == "VIOLATION" and not (o is not None and o.decided and o.asserted)
            if r == rid:
                continue
            errors = [off_target_error(key_verdict, o) for o in outcomes]
            material = [e for e in errors if e]
            if len(material) >= 2:
                repeated += 1
                counts[max(set(material), key=material.count)] += 1
            elif len(material) == 1:
                one_off += 1
        unclean = repeated > 0
        unclean_pages += unclean
        per_page.append({"case_id": case.case_id, "unclean": unclean, "false_alarm_cells": counts["false_alarm"],
                         "missed_cells": counts["missed"], "undecided_cells": counts["undecided"],
                         "one_off_error_cells": one_off})
    aggregates = {
        "cases_passed": len(dataset.cases) - failing_cases, "cases_failed": failing_cases,
        "unclean_pages": unclean_pages, "tp": tp, "fp": fp, "fn": fn,
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        "na_accuracy": round(na_right / na_total, 4) if na_total else None,
        "confirmed": adj_counts["CONFIRMED"], "rejected": adj_counts["REJECTED"], "disputed": adj_counts["DISPUTED"],
        "rejected_correct": rejected_correct, "rejected_wrong": rejected_wrong, "flips": flips,
        "cost_usd": round(sum(run["cost_usd"] for run in runs), 4), "turns": sum(run["turns"] for run in runs),
        "wall_clock_s": round(sum(run["wall_clock_s"] for run in runs), 1),
    }
    b_pass = failing_cases <= allowed_failing and unclean_pages <= max_unclean
    return {"per_case": per_case, "per_page_off_target": per_page, "aggregates": aggregates, "b_pass": b_pass}


# --------------------------------------------------------------------------
# Runs
# --------------------------------------------------------------------------


@dataclass
class RunContext:
    dataset: Dataset
    config: dict
    run_index: int
    run_id: str
    run_dir: Path
    db_path: Path
    audit_db: Path
    conn: sqlite3.Connection
    tasks: list[CheckTask]
    rulesets: dict
    rules_by_id: dict[str, ComplianceRule]
    real: bool
    official: bool
    leak_markers: list[str]
    page_text_cache: dict = field(default_factory=dict)

    def page_text(self, page_name: str) -> str:
        if page_name not in self.page_text_cache:
            self.page_text_cache[page_name] = visible_text(self.dataset.case_for_page(page_name).file.read_text(encoding="utf-8"))
        return self.page_text_cache[page_name]


def build_tasks(dataset: Dataset, rulesets: dict) -> list[CheckTask]:
    tasks = []
    for case in dataset.cases:
        for j in extract_markets(case.file.read_text(encoding="utf-8")):
            if j not in KNOWN_JURISDICTIONS:
                continue
            rules = rulesets.get(j)
            tasks.append(CheckTask(
                page_path=case.page_name, jurisdiction=j,
                ruleset_version=rules[0].ruleset_version if rules else "UNKNOWN",
                assigned_rules=[r.rule_id for r in rules] if rules else [],
            ))
    return tasks


def _confirmed(conn, findings):
    confirmed = {a.finding_id for a in get_adjudications(conn) if a.verdict.value == "CONFIRMED"}
    return [f for f in findings if f"{f.task_id}::{f.rule_id}" in confirmed]


def _agent_fns(ctx: RunContext, model: str | None):
    """(checker_fn, verifier_fn, planner_fn, stats). Stub mode never calls
    a model; real mode wires the caged agents and the pinned verifier."""
    stats = {"cost_usd": 0.0, "turns": 0}
    if not ctx.real:
        return checker_stub.stub_checker, verifier_stub.stub_verifier, planner_stub.stub_planner, stats
    import agents.checker.config as checker_config
    import agents.checker.harness as checker_harness
    import agents.planner.config as planner_config
    import agents.planner.harness as planner_harness
    from nodes.verifier import load_verifier_config, verify_finding
    from nodes.verifier import run_stats as verifier_run_stats

    official = ctx.official
    check_budget = checker_config.EVAL_MAX_BUDGET_USD if official else checker_config.MAX_BUDGET_USD
    plan_budget = planner_config.EVAL_MAX_BUDGET_USD if official else planner_config.MAX_BUDGET_USD
    verify_budget = load_verifier_config()["max_budget_usd"]["official_gate" if official else "dev"]

    def checker_fn(task):
        try:
            return checker_harness.real_checker(task, ctx.conn, ctx.run_id, model=model, max_budget_usd=check_budget)
        finally:
            r = checker_harness.last_result
            if r is not None:
                stats["cost_usd"] += r.total_cost_usd or 0.0
                stats["turns"] += r.num_turns or 0

    def verifier_fn(finding, rule, run_id):
        seen = len(verifier_run_stats)
        try:
            return verify_finding(finding, rule, run_id, model=model, max_budget_usd=verify_budget,
                                  audit_db_path=ctx.run_dir / "verifier_audit.db",
                                  case_root=ctx.run_dir / "verifier_cases")
        finally:
            for s in verifier_run_stats[seen:]:  # RT2-11: the verifier's cost and turns count too
                stats["cost_usd"] += s.get("cost_usd") or 0.0
                stats["turns"] += s.get("num_turns") or 0

    def planner_fn(finding):
        try:
            return planner_harness.real_planner(finding, ctx.conn, ctx.run_id, ctx.rules_by_id, model=model, max_budget_usd=plan_budget)
        finally:
            r = planner_harness.last_result
            if r is not None:
                stats["cost_usd"] += r.total_cost_usd or 0.0
                stats["turns"] += r.num_turns or 0

    return checker_fn, verifier_fn, planner_fn, stats


def _raise_for_provider_rows(ctx: RunContext) -> None:
    provider = ctx.conn.execute("SELECT COUNT(*) FROM task_ledger WHERE error_class = 'PROVIDER_ERROR'").fetchone()[0]
    if provider:
        raise InvalidRun(f"run {ctx.run_index}: {provider} provider error rows (auth, rate limit or overload)")


def run_once(ctx: RunContext, model: str | None) -> dict:
    checker_fn, verifier_fn, planner_fn, stats = _agent_fns(ctx, model)
    t0 = time.monotonic()
    # P3 (owner decision 2A): real agent sessions run in the private run
    # directory, so their CLI transcripts are kept apart from coding sessions.
    with contextlib.chdir(ctx.run_dir) if ctx.real else contextlib.nullcontext():
        run_check_stage(ctx.tasks, checker_fn, ctx.conn)
        findings = get_findings(ctx.conn)
        run_verify_stage(findings, ctx.rules_by_id, verifier_fn, ctx.conn, ctx.run_id)
        run_plan_stage(_confirmed(ctx.conn, findings), planner_fn, ctx.conn)
    wall = time.monotonic() - t0
    _raise_for_provider_rows(ctx)
    return {"cells": cell_outcomes(ctx.conn, ctx.tasks), "cost_usd": stats["cost_usd"], "turns": stats["turns"],
            "wall_clock_s": wall}


def _raised_in_runner(exc: BaseException) -> bool:
    """True iff the innermost repo frame of the traceback is under evals/
    (runner or grader code): INVALID RUN. Elsewhere it is system code and
    the run is scored as is (gate inside_the_automation_is_a_miss)."""
    innermost = None
    for frame in traceback.extract_tb(exc.__traceback__):
        p = Path(frame.filename).resolve()
        if p.is_relative_to(REPO_ROOT):
            innermost = p
    return innermost is None or innermost.is_relative_to(REPO_ROOT / "evals")


# --------------------------------------------------------------------------
# Series
# --------------------------------------------------------------------------

SERIES_FIELDS_ORDER = [
    "series_id", "date", "commit", "config_sha256", "holdout_id", "manifest_sha256", "model", "verifier_pin",
    "ruleset_version", "ruleset_sha256", "run_db_names", "earlier_series_count", "result", "exit_code",
]


def sanitize(results: dict, config: dict) -> dict:
    """Enforce sanitized_results_allowlist: refuse any extra field, any
    unknown miss category and any non-integer off-target count."""
    allow = config["sanitized_results_allowlist"]
    if set(results) - {"series", "component_a", "per_case", "per_page_off_target", "aggregates"}:
        raise ValueError("results: unexpected top-level section")
    if set(results.get("series", {})) - set(allow["series"]):
        raise ValueError("results: field not on the series allowlist")
    if set(results.get("aggregates", {})) - set(allow["aggregates"]):
        raise ValueError("results: field not on the aggregates allowlist")
    for section in ("component_a", "per_case", "per_page_off_target"):
        for row in results.get(section, []):
            if set(row) - set(allow[section]):
                raise ValueError(f"results: field not on the {section} allowlist")
    for row in results.get("per_case", []):
        if row.get("miss_category") is not None and row["miss_category"] not in allow["miss_categories"]:
            raise ValueError("results: unknown miss category")
    for row in results.get("per_page_off_target", []):
        for k, v in row.items():
            if k not in ("case_id", "unclean") and not isinstance(v, int):
                raise ValueError("results: off-target counts must be integers")
    return results


FULL_MANIFEST_FILES = {"key.yaml", "briefs.md", "adjudication.md"}  # RT2-03; SCENARIO_SPEC §6 step 7


def _manifest_names(manifest: Path) -> set[str]:
    return {ln.split("  ", 1)[1].strip() for ln in manifest.read_text(encoding="utf-8").splitlines() if "  " in ln}


def _git_head() -> str:
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return r.stdout.strip() or "unknown"


def _git_dirty() -> bool:
    """True when the repository has any uncommitted or untracked file
    (gitignored files excluded), or its status cannot be read."""
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"], capture_output=True, text=True, check=False)
    return r.returncode != 0 or bool(r.stdout.strip())


def run_series(
    dataset_name: str,
    holdout_root: Path,
    *,
    runs: int | None = None,
    real: bool = False,
    gated: bool = False,
    manifest_dir: Path = MANIFEST_DIR,
    results_dir: Path = RESULTS_DIR,
    run_a1: bool | None = None,
) -> tuple[str, dict, Path | None]:
    """Run one series; return (result, sanitized results, results path)."""
    if not (dataset_name == "july" or HOLDOUT_ID_RE.match(dataset_name)):
        raise ValueError(f"unknown dataset {dataset_name!r}")
    if gated and not HOLDOUT_ID_RE.match(dataset_name):
        raise ValueError("the July set is development data and is never gated")
    config = load_eval_config()
    holdout_root = Path(holdout_root).resolve()
    series_id = f"{dataset_name}-{date.today().isoformat()}-{uuid.uuid4().hex[:6]}"
    runs_per_case = config["component_b"]["claim"]["runs_per_case"]
    runs = runs_per_case if runs is None else runs
    if runs < 1:
        raise ValueError("--runs must be at least 1")
    if gated:
        # RT2-01, RT2-02, RT2-03: an official series is exactly the gate's
        # run count, on a clean tree (so the recorded commit is what ran),
        # on a holdout with no completed official series (retirement rule).
        if runs != runs_per_case:
            raise ValueError(f"a gated series has exactly {runs_per_case} runs")
        if _git_dirty():
            raise ValueError("a gated series needs a clean working tree (commit first)")
        if results_dir.is_dir() and any(results_dir.glob(f"{dataset_name}-*.json")):
            raise ValueError(f"{dataset_name} already has a completed official series and is retired")
    rulesets = load_rulesets(RULESETS_DIR)
    rules_by_id = {r.rule_id: r for rules in rulesets.values() if rules for r in rules}
    model = config["model_routing"]["official" if gated else "development"] if real else "stub"
    series = {
        "series_id": series_id, "date": date.today().isoformat(), "commit": _git_head(),
        "config_sha256": lf_sha256(EVAL_CONFIG_PATH), "holdout_id": dataset_name, "manifest_sha256": None,
        "model": model, "verifier_pin": yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))["verifier_agent"]["pinned_commit"],
        "ruleset_version": next(iter(rules_by_id.values())).ruleset_version,
        "ruleset_sha256": config["datasets"]["ruleset_sha256"], "run_db_names": [],
        "earlier_series_count": len(list(results_dir.glob(f"{dataset_name}-*.json"))) if results_dir.is_dir() else 0,
        "result": None, "exit_code": None,
    }
    results = {"series": series, "component_a": [], "per_case": [], "per_page_off_target": [], "aggregates": {}}
    series_dir = guard_output_path(holdout_root / "runs" / dataset_name / series_id, holdout_root, holdout_folders(holdout_root))

    def finish(result: str) -> tuple[str, dict, Path | None]:
        series["result"], series["exit_code"] = result, EXIT_FOR[result]
        sanitize(results, config)
        if gated and result in (PASS, FAIL):
            out = results_dir / f"{series_id}.json"
        else:
            series_dir.mkdir(parents=True, exist_ok=True)
            out = series_dir / "results.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        return result, results, out

    try:
        # Preflight: INVALID RUN or NOT ENOUGH CASES before any score.
        if HOLDOUT_ID_RE.match(dataset_name):
            manifest = Path(manifest_dir) / f"{dataset_name}.sha256"
            holdout_dir = holdout_root / dataset_name
            if not manifest.is_file() or not holdout_dir.is_dir():
                raise InvalidRun("holdout or its committed manifest not found")
            series["manifest_sha256"] = lf_sha256(manifest)
            if gated and not FULL_MANIFEST_FILES <= _manifest_names(manifest):
                raise InvalidRun("a gated series needs the full manifest (key, briefs and adjudication pinned)")
            if check_holdout.verify_manifest(holdout_dir, manifest):
                raise InvalidRun("holdout files do not match the committed manifest")
            errors, _summary = check_holdout.check_holdout(holdout_dir, RULESETS_DIR)
            if errors:
                raise NotEnoughCases("holdout self-check failed: no valid cases")
            dataset = load_holdout(holdout_root, dataset_name)
            if len(dataset.cases) < config["component_b"]["claim"]["min_cases"]:
                raise NotEnoughCases(f"{len(dataset.cases)} valid cases")
            pages.configure_cage(dataset.pages_dir, dataset.aliases)
        else:
            dataset = load_july()
            pages.configure_cage(dataset.pages_dir)
        if real:
            from nodes.verifier import VerifierConfigError, check_verifier_checkout

            try:
                check_verifier_checkout()
            except VerifierConfigError as exc:
                raise InvalidRun("verifier checkout not at the pin or not clean") from exc

        # A1 (gated series only) and A3, once, before the series.
        if run_a1 if run_a1 is not None else gated:
            a1 = subprocess.run(config["component_a"]["a1_keyless_suite"]["command"].split(),
                                cwd=REPO_ROOT, capture_output=True, text=True, check=False)
            results["component_a"].append(_row("a1_keyless_suite", 0, 0 if a1.returncode == 0 else 1))
        results["component_a"].extend(a3_checks(dataset))
        if dataset.gated and any(r["passed"] is False for r in results["component_a"]):
            return finish(FAIL)  # A1 or A3 failed: no series is run

        leak_markers = [*HOLDOUT_FILE_MARKERS, str(holdout_root), holdout_root.as_posix()] if dataset.gated else []
        tasks = build_tasks(dataset, rulesets)
        run_results = []
        for k in range(1, runs + 1):
            run_dir = guard_output_path(series_dir / f"run{k}", holdout_root, holdout_folders(holdout_root))
            run_dir.mkdir(parents=True, exist_ok=False)
            db_path, audit_db = run_dir / "ledger.db", run_dir / "audit.db"
            checker_audit.set_audit_db_path(audit_db)
            planner_audit.set_audit_db_path(audit_db)
            series["run_db_names"].append(f"run{k}/{db_path.name}")
            conn = create_db(str(db_path))
            try:
                ctx = RunContext(dataset, config, k, f"run-{uuid.uuid4().hex[:8]}", run_dir, db_path, audit_db,
                                 conn, tasks, rulesets, rules_by_id, real, gated, leak_markers)
                try:
                    run_results.append(run_once(ctx, None if model == "stub" else model))
                except InvalidRun:
                    raise
                except Exception as exc:  # noqa: BLE001 -- classified below
                    if _raised_in_runner(exc):
                        raise InvalidRun(f"run {k}: exception in runner code: {type(exc).__name__}") from exc
                    _raise_for_provider_rows(ctx)  # RT2-04: a provider error stays INVALID RUN after a crash too
                    run_results.append({"cells": cell_outcomes(conn, tasks), "cost_usd": 0.0, "turns": 0, "wall_clock_s": 0.0})
                results["component_a"].extend(a2_checks(ctx))
            finally:
                conn.close()

        scored = score_series(dataset, run_results, config)
        results["per_case"] = scored["per_case"]
        results["per_page_off_target"] = scored["per_page_off_target"]
        results["aggregates"] = scored["aggregates"]
        a_pass = all(r["passed"] is not False for r in results["component_a"])
        return finish(PASS if a_pass and scored["b_pass"] else FAIL)
    except NotEnoughCases as exc:
        print(f"NOT ENOUGH CASES: {exc}", file=sys.stderr)
        return finish(NOT_ENOUGH_CASES)
    except InvalidRun as exc:
        print(f"INVALID RUN: {exc}", file=sys.stderr)
        return finish(INVALID_RUN)
    except Exception as exc:  # noqa: BLE001 -- system exceptions are handled per run; this is runner or grader code
        print(f"INVALID RUN: exception in runner or grader code: {type(exc).__name__}", file=sys.stderr)
        return finish(INVALID_RUN)
    finally:
        pages.reset_cage()
        checker_audit.set_audit_db_path(checker_audit.AUDIT_DB_PATH)
        planner_audit.set_audit_db_path(planner_audit.AUDIT_DB_PATH)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dataset", required=True, help="july or a holdout ID such as H2")
    ap.add_argument("--runs", type=int, default=None)
    ap.add_argument("--holdout-root", type=Path, default=None, help="overrides holdout_root in config.local.yaml")
    ap.add_argument("--real", action="store_true", help="real agents and verifier (paid; owner authorization only)")
    ap.add_argument("--gated", action="store_true", help="official series: writes evals/results/<series_id>.json")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return EXIT_USAGE
    if args.gated and (not args.real or not HOLDOUT_ID_RE.match(args.dataset)):
        print("usage: --gated needs --real and a holdout dataset")
        return EXIT_USAGE
    holdout_root = args.holdout_root or load_local_config().get("holdout_root")
    if not holdout_root:
        print("usage: set holdout_root in config.local.yaml or pass --holdout-root")
        return EXIT_USAGE
    try:
        result, results, out = run_series(args.dataset, Path(holdout_root), runs=args.runs, real=args.real, gated=args.gated)
    except (ValueError, StorageError) as exc:
        print(f"usage: {exc}")
        return EXIT_USAGE
    a_rows = results["component_a"]
    print(f"series: {results['series']['series_id']}")
    print(f"component A: {sum(r['passed'] is True for r in a_rows)} passed, "
          f"{sum(r['passed'] is False for r in a_rows)} failed, {sum(r['passed'] is None for r in a_rows)} not run")
    agg = results["aggregates"]
    if agg:
        print(f"component B: {agg['cases_passed']} cases passed, {agg['cases_failed']} failed, "
              f"{agg['unclean_pages']} unclean pages")
    where = "evals/results/" if args.gated and out and out.is_relative_to(RESULTS_DIR) else "the private run directory"
    print(f"results: written to {where}")
    print(f"RESULT: {result}")
    return EXIT_FOR[result]


if __name__ == "__main__":
    sys.exit(main())
