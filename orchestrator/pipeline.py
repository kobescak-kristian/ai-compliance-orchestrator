"""Deterministic orchestration loop (ADR-0001): drives CheckTasks (and,
for the plan stage, ViolationFindings) through a stub/agent callable,
enforces Pydantic contract validation at the boundary, and persists
ledger state + findings/proposals + dead-letters. No LLM calls originate
here -- process_fn is supplied by the caller (a stub in Phase 2, a caged
agent from Phase 3 on).

State machine: QUEUED -> RUNNING -> DONE | FAILED | DEAD_LETTER |
ESCALATED (BLUEPRINT.md §3). Resume-from-ledger: a task whose (task_id,
stage) already has a terminal row is skipped, not reprocessed, unless
force=True (FI-6's deliberate re-run). Idempotency is enforced two ways:
resume-skip (the common case) and, independently, a UNIQUE(content_hash,
rule_id) constraint at the storage layer so even a forced re-run cannot
duplicate a finding or proposal (FI-6).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from pydantic import ValidationError

from contracts.schemas import (
    AdjudicationRecord,
    AdjudicationVerdict,
    CheckTask,
    ComplianceRule,
    RemediationProposal,
    TaskState,
    ViolationFinding,
)

TERMINAL_STATES = {
    TaskState.DONE.value,
    TaskState.FAILED.value,
    TaskState.DEAD_LETTER.value,
    TaskState.ESCALATED.value,
}


class BudgetExceededError(Exception):
    """Raised by a checker/planner callable to simulate FI-1: the agent's
    budget or turn cap tripped mid-task."""


class VerifierInvocationError(Exception):
    """Raised by a verifier callable (nodes.verifier.verify_finding or
    its stub) on a non-zero subprocess exit, schema-invalid output, or a
    config/pinned-commit mismatch. Maps to task-atomic FAILED in
    run_verify_stage (policy/ADJUDICATION_POLICY.md §12)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_id_for(task: CheckTask) -> str:
    return f"{task.page_path}::{task.jurisdiction}"


def finding_id_for(finding: ViolationFinding) -> str:
    return f"{finding.task_id}::{finding.rule_id}"


def _content_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def finding_content_hash(finding: ViolationFinding) -> str:
    return _content_hash(
        finding.page_path,
        finding.jurisdiction,
        finding.rule_id,
        finding.ruleset_version,
        finding.verdict.value,
        finding.evidence_excerpt,
    )


def proposal_content_hash(proposal: RemediationProposal) -> str:
    return _content_hash(
        proposal.page_path,
        proposal.rule_id,
        proposal.offending_text,
        proposal.proposed_text,
    )


# --------------------------------------------------------------------------
# Ledger primitives
# --------------------------------------------------------------------------


def register_tasks(item_ids: list[str], conn: sqlite3.Connection, stage: str) -> None:
    """Insert a QUEUED row (attempt=1) for every item_id that has no
    ledger row yet at this stage. Idempotent: safe to call repeatedly.
    """
    for item_id in item_ids:
        existing = conn.execute(
            "SELECT 1 FROM task_ledger WHERE task_id = ? AND stage = ? LIMIT 1",
            (item_id, stage),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO task_ledger "
                "(task_id, stage, state, attempt, started_at) VALUES (?, ?, ?, ?, ?)",
                (item_id, stage, TaskState.QUEUED.value, 1, _now()),
            )
    conn.commit()


def _latest_terminal_row(conn: sqlite3.Connection, item_id: str, stage: str) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM task_ledger WHERE task_id = ? AND stage = ? "
        f"AND state IN ({', '.join('?' * len(TERMINAL_STATES))}) "
        "ORDER BY id DESC LIMIT 1",
        (item_id, stage, *TERMINAL_STATES),
    ).fetchone()
    return row


def _next_attempt(conn: sqlite3.Connection, item_id: str, stage: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM task_ledger WHERE task_id = ? AND stage = ? AND state = ?",
        (item_id, stage, TaskState.RUNNING.value),
    ).fetchone()
    return row[0] + 1


def _insert_ledger_row(
    conn: sqlite3.Connection,
    item_id: str,
    stage: str,
    state: str,
    attempt: int,
    *,
    started_at: str | None = None,
    ended_at: str | None = None,
    exit_code: int | None = None,
    error_class: str | None = None,
    payload_ref: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO task_ledger "
        "(task_id, stage, state, attempt, started_at, ended_at, exit_code, error_class, payload_ref) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (item_id, stage, state, attempt, started_at, ended_at, exit_code, error_class, payload_ref),
    )
    conn.commit()


def _insert_dead_letter(conn: sqlite3.Connection, item_id: str, stage: str, raw_payload, error_message: str) -> None:
    conn.execute(
        "INSERT INTO dead_letter (task_id, stage, raw_payload, error_message, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (item_id, stage, json.dumps(raw_payload, default=str), error_message, _now()),
    )
    conn.commit()


def insert_finding(conn: sqlite3.Connection, finding: ViolationFinding) -> bool:
    """Insert a validated finding, deduped on (content_hash, rule_id).
    Returns True if newly inserted, False if it was a duplicate (FI-6).
    """
    h = finding_content_hash(finding)
    cur = conn.execute(
        "INSERT OR IGNORE INTO findings "
        "(content_hash, rule_id, task_id, page_path, jurisdiction, ruleset_version, "
        "verdict, evidence_excerpt, rationale, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            h, finding.rule_id, finding.task_id, finding.page_path, finding.jurisdiction,
            finding.ruleset_version, finding.verdict.value, finding.evidence_excerpt,
            finding.rationale, _now(),
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def insert_proposal(conn: sqlite3.Connection, proposal: RemediationProposal) -> bool:
    """Insert a validated proposal, deduped on (content_hash, rule_id).
    Returns True if newly inserted, False if it was a duplicate (FI-6).
    """
    h = proposal_content_hash(proposal)
    cur = conn.execute(
        "INSERT OR IGNORE INTO proposals "
        "(content_hash, rule_id, task_id, page_path, offending_text, proposed_text, "
        "status, created_by_run_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            h, proposal.rule_id, f"{proposal.page_path}::{proposal.rule_id}", proposal.page_path,
            proposal.offending_text, proposal.proposed_text, proposal.status.value,
            proposal.created_by_run_id, _now(),
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def insert_adjudication(conn: sqlite3.Connection, record: AdjudicationRecord) -> bool:
    """Insert one adjudication row, deduped on finding_id (UNIQUE
    constraint at the storage layer, same dual-layer idempotency pattern
    as insert_finding/insert_proposal): a second adjudication of the
    same finding is a no-op, never an overwrite (policy §6, §11 "no
    silent overwrites"). Returns True if newly inserted.
    """
    cur = conn.execute(
        "INSERT OR IGNORE INTO adjudication_log "
        "(finding_id, verdict, citation, model, run_id, created_at) VALUES (?,?,?,?,?,?)",
        (record.finding_id, record.verdict.value, record.citation, record.model, record.run_id, _now()),
    )
    conn.commit()
    return cur.rowcount > 0


def get_adjudications(conn: sqlite3.Connection) -> list[AdjudicationRecord]:
    rows = conn.execute(
        "SELECT finding_id, verdict, citation, model, run_id, created_at FROM adjudication_log"
    ).fetchall()
    return [
        AdjudicationRecord(
            finding_id=r[0], verdict=r[1], citation=r[2], model=r[3], run_id=r[4], timestamp=r[5]
        )
        for r in rows
    ]


def get_confirmed_findings(conn: sqlite3.Connection) -> list[ViolationFinding]:
    """The system's assertions (policy §5): CONFIRMED findings only,
    joined from findings + adjudication_log. REJECTED and DISPUTED
    findings are excluded here even though they remain in the ledger
    forever -- disagreement is retained, never asserted.
    """
    rows = conn.execute(
        "SELECT f.task_id, f.page_path, f.jurisdiction, f.rule_id, f.ruleset_version, "
        "f.verdict, f.evidence_excerpt, f.rationale "
        "FROM findings f JOIN adjudication_log a "
        "ON a.finding_id = f.task_id || '::' || f.rule_id "
        "WHERE a.verdict = 'CONFIRMED'"
    ).fetchall()
    return [
        ViolationFinding(
            task_id=r[0], page_path=r[1], jurisdiction=r[2], rule_id=r[3],
            ruleset_version=r[4], verdict=r[5], evidence_excerpt=r[6], rationale=r[7],
        )
        for r in rows
    ]


def get_findings(conn: sqlite3.Connection, page_path: str | None = None) -> list[ViolationFinding]:
    query = "SELECT task_id, page_path, jurisdiction, rule_id, ruleset_version, verdict, evidence_excerpt, rationale FROM findings"
    params: tuple = ()
    if page_path is not None:
        query += " WHERE page_path = ?"
        params = (page_path,)
    rows = conn.execute(query, params).fetchall()
    return [
        ViolationFinding(
            task_id=r[0], page_path=r[1], jurisdiction=r[2], rule_id=r[3],
            ruleset_version=r[4], verdict=r[5], evidence_excerpt=r[6], rationale=r[7],
        )
        for r in rows
    ]


# --------------------------------------------------------------------------
# Stage runner
# --------------------------------------------------------------------------


def run_check_stage(
    tasks: list[CheckTask],
    checker_fn: Callable[[CheckTask], list[dict]],
    conn: sqlite3.Connection,
    *,
    stage: str = "check",
    missing_rulesets: set[str] | None = None,
    force: bool = False,
) -> None:
    """Drive every CheckTask through checker_fn. Findings are validated
    as one atomic handoff per task: if any payload in the batch fails
    schema validation, the whole task -> DEAD_LETTER, all its raw
    payloads are preserved in dead_letter, and none of its findings
    (valid or not) reach the findings table (BLUEPRINT.md §3, FI-2).
    A task whose jurisdiction's rule set failed to load -> FAILED with
    error_class=MISSING_RULESET, without ever calling checker_fn (FI-4).
    """
    missing_rulesets = missing_rulesets or set()
    register_tasks([task_id_for(t) for t in tasks], conn, stage)

    for task in tasks:
        item_id = task_id_for(task)

        if not force and _latest_terminal_row(conn, item_id, stage) is not None:
            continue  # resume: already terminal, do not reprocess

        attempt = _next_attempt(conn, item_id, stage)
        started = _now()
        _insert_ledger_row(conn, item_id, stage, TaskState.RUNNING.value, attempt, started_at=started)

        if task.jurisdiction in missing_rulesets:
            _insert_ledger_row(
                conn, item_id, stage, TaskState.FAILED.value, attempt,
                started_at=started, ended_at=_now(), error_class="MISSING_RULESET",
            )
            continue

        try:
            raw_payloads = checker_fn(task)
        except BudgetExceededError as exc:
            _insert_ledger_row(
                conn, item_id, stage, TaskState.FAILED.value, attempt,
                started_at=started, ended_at=_now(), error_class="BUDGET_EXCEEDED",
                payload_ref=str(exc),
            )
            continue

        validated: list[ViolationFinding] = []
        invalid = False
        for raw in raw_payloads:
            try:
                validated.append(ViolationFinding(**raw))
            except ValidationError as exc:
                _insert_dead_letter(conn, item_id, stage, raw, str(exc))
                invalid = True

        if invalid:
            _insert_ledger_row(
                conn, item_id, stage, TaskState.DEAD_LETTER.value, attempt,
                started_at=started, ended_at=_now(), error_class="SCHEMA_INVALID",
            )
            continue  # atomic: no finding from this task reaches storage

        for finding in validated:
            insert_finding(conn, finding)

        _insert_ledger_row(conn, item_id, stage, TaskState.DONE.value, attempt, started_at=started, ended_at=_now())


def run_verify_stage(
    findings: list[ViolationFinding],
    rules_by_id: dict[str, ComplianceRule],
    verifier_fn: Callable[[ViolationFinding, ComplianceRule, str], dict],
    conn: sqlite3.Connection,
    run_id: str,
    *,
    stage: str = "verify",
    force: bool = False,
) -> None:
    """Adjudicate every VIOLATION finding through verifier_fn (policy/
    ADJUDICATION_POLICY.md §10: COMPLIANT/NOT_APPLICABLE findings are
    never sent to the verifier -- a wrong COMPLIANT is a recall-failure
    path, not an adjudication-failure path, explicit by design).

    Findings are grouped by their originating CheckTask (task_id). A
    verifier_fn failure (VerifierInvocationError or a schema-invalid
    raw payload) on any one finding fails the whole task atomically --
    mirroring FI-2's DEAD_LETTER atomicity, except here the terminal
    state is FAILED, not DEAD_LETTER (policy §12: this is an agent-
    invocation failure, not a content-payload failure) -- and none of
    that task's adjudication rows are written. Otherwise the task's
    terminal state is ESCALATED if any adjudication came back DISPUTED,
    else DONE, whatever the mix of CONFIRMED/REJECTED (policy §11).
    """
    violations = [f for f in findings if f.verdict.value == "VIOLATION"]
    by_task: dict[str, list[ViolationFinding]] = {}
    for f in violations:
        by_task.setdefault(f.task_id, []).append(f)

    register_tasks(list(by_task.keys()), conn, stage)

    for item_id, task_findings in by_task.items():
        if not force and _latest_terminal_row(conn, item_id, stage) is not None:
            continue  # resume: already terminal, do not reprocess (also FI-6 idempotency)

        attempt = _next_attempt(conn, item_id, stage)
        started = _now()
        _insert_ledger_row(conn, item_id, stage, TaskState.RUNNING.value, attempt, started_at=started)

        records: list[AdjudicationRecord] = []
        failure: str | None = None
        for finding in task_findings:
            rule = rules_by_id[finding.rule_id]
            try:
                raw = verifier_fn(finding, rule, run_id)
                records.append(AdjudicationRecord(**raw))
            except (VerifierInvocationError, ValidationError) as exc:
                failure = str(exc)
                break

        if failure is not None:
            _insert_ledger_row(
                conn, item_id, stage, TaskState.FAILED.value, attempt,
                started_at=started, ended_at=_now(), error_class="VERIFIER_FAILED",
                payload_ref=failure,
            )
            continue  # atomic: no adjudication row from this task reaches storage

        for record in records:
            insert_adjudication(conn, record)

        terminal = (
            TaskState.ESCALATED.value
            if any(r.verdict == AdjudicationVerdict.DISPUTED for r in records)
            else TaskState.DONE.value
        )
        _insert_ledger_row(conn, item_id, stage, terminal, attempt, started_at=started, ended_at=_now())


def run_plan_stage(
    findings: list[ViolationFinding],
    planner_fn: Callable[[ViolationFinding], dict | None],
    conn: sqlite3.Connection,
    *,
    stage: str = "plan",
    force: bool = False,
) -> None:
    """Drive every VIOLATION finding through planner_fn, same terminal-
    state / dead-letter / dedup mechanics as run_check_stage. A finding
    with verdict != VIOLATION is skipped entirely (nothing to remediate).
    planner_fn may return None (no proposal drafted) or raise
    BudgetExceededError.
    """
    violations = [f for f in findings if f.verdict.value == "VIOLATION"]
    register_tasks([finding_id_for(f) for f in violations], conn, stage)

    for finding in violations:
        item_id = finding_id_for(finding)

        if not force and _latest_terminal_row(conn, item_id, stage) is not None:
            continue

        attempt = _next_attempt(conn, item_id, stage)
        started = _now()
        _insert_ledger_row(conn, item_id, stage, TaskState.RUNNING.value, attempt, started_at=started)

        try:
            raw = planner_fn(finding)
        except BudgetExceededError as exc:
            _insert_ledger_row(
                conn, item_id, stage, TaskState.FAILED.value, attempt,
                started_at=started, ended_at=_now(), error_class="BUDGET_EXCEEDED",
                payload_ref=str(exc),
            )
            continue

        if raw is None:
            _insert_ledger_row(conn, item_id, stage, TaskState.DONE.value, attempt, started_at=started, ended_at=_now())
            continue

        try:
            proposal = RemediationProposal(**raw)
        except ValidationError as exc:
            _insert_dead_letter(conn, item_id, stage, raw, str(exc))
            _insert_ledger_row(
                conn, item_id, stage, TaskState.DEAD_LETTER.value, attempt,
                started_at=started, ended_at=_now(), error_class="SCHEMA_INVALID",
            )
            continue

        insert_proposal(conn, proposal)
        _insert_ledger_row(conn, item_id, stage, TaskState.DONE.value, attempt, started_at=started, ended_at=_now())
