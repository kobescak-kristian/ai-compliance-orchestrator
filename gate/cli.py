"""Human review queue CLI: list / approve / reject
contracts.schemas.RemediationProposal rows, plus a disputed section for
ESCALATED verify-stage tasks (policy/ADJUDICATION_POLICY.md §3). Fully
deterministic; approve/reject update ledger state (proposals.status)
only -- nothing in this module, or anywhere in the system, can modify a
page (BLUEPRINT.md §2 step 6, §4 human-gate row).

Idempotent: re-approving or re-rejecting a proposal already in a
terminal status (APPROVED/REJECTED/ESCALATED) is a no-op -- the UPDATE
is scoped to status='PENDING', so a second call touches zero rows and
the original decision stands.

Implemented Phase 5, alongside the planner agent (BLUEPRINT.md §9).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

TERMINAL_PROPOSAL_STATUSES = {"APPROVED", "REJECTED", "ESCALATED"}


def list_proposals(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    """Every proposal, joined with its originating finding (page_path +
    rule_id -- unique together, since rule_id already encodes
    jurisdiction) for evidence/jurisdiction context.
    """
    sql = (
        "SELECT p.id, p.page_path, p.rule_id, p.offending_text, p.proposed_text, "
        "p.status, p.created_by_run_id, p.created_at, f.jurisdiction, f.evidence_excerpt "
        "FROM proposals p LEFT JOIN findings f "
        "ON f.page_path = p.page_path AND f.rule_id = p.rule_id"
    )
    params: tuple = ()
    if status is not None:
        sql += " WHERE p.status = ?"
        params = (status,)
    sql += " ORDER BY p.id"
    rows = conn.execute(sql, params).fetchall()
    cols = [
        "id", "page_path", "rule_id", "offending_text", "proposed_text",
        "status", "created_by_run_id", "created_at", "jurisdiction", "evidence_excerpt",
    ]
    return [dict(zip(cols, row)) for row in rows]


def get_proposal(conn: sqlite3.Connection, proposal_id: int) -> dict | None:
    matches = [p for p in list_proposals(conn) if p["id"] == proposal_id]
    return matches[0] if matches else None


def _set_status(conn: sqlite3.Connection, proposal_id: int, new_status: str) -> str:
    proposal = get_proposal(conn, proposal_id)
    if proposal is None:
        return f"proposal {proposal_id} not found"
    if proposal["status"] in TERMINAL_PROPOSAL_STATUSES:
        return f"proposal {proposal_id} already {proposal['status']} -- no-op"

    cur = conn.execute(
        "UPDATE proposals SET status = ? WHERE id = ? AND status = 'PENDING'",
        (new_status, proposal_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        # lost a race with another decision between the read above and this
        # write -- re-read to report the status that actually won, not a lie
        current = get_proposal(conn, proposal_id)
        return f"proposal {proposal_id} already {current['status']} -- no-op"
    return f"proposal {proposal_id} -> {new_status}"


def approve_proposal(conn: sqlite3.Connection, proposal_id: int) -> str:
    return _set_status(conn, proposal_id, "APPROVED")


def reject_proposal(conn: sqlite3.Connection, proposal_id: int) -> str:
    return _set_status(conn, proposal_id, "REJECTED")


def list_disputed(conn: sqlite3.Connection) -> list[dict]:
    """ESCALATED verify-stage tasks (policy §11: >=1 DISPUTED finding on
    the task), each with both artifacts -- the finding(s) and their
    adjudication record(s) -- surfaced together, never auto-resolved
    (policy §3).
    """
    task_ids = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT task_id FROM task_ledger t1 "
            "WHERE stage='verify' AND state='ESCALATED' "
            "AND id = (SELECT MAX(id) FROM task_ledger t2 "
            "WHERE t2.task_id = t1.task_id AND t2.stage = 'verify')"
        ).fetchall()
    ]

    all_adjudications = conn.execute("SELECT finding_id, verdict, citation FROM adjudication_log").fetchall()

    entries = []
    for task_id in task_ids:
        findings = conn.execute(
            "SELECT rule_id, evidence_excerpt, rationale FROM findings "
            "WHERE task_id = ? AND verdict = 'VIOLATION'",
            (task_id,),
        ).fetchall()
        adjudications = {
            finding_id: {"verdict": verdict, "citation": citation}
            for finding_id, verdict, citation in all_adjudications
            if finding_id.startswith(f"{task_id}::")
        }
        entries.append(
            {
                "task_id": task_id,
                "findings": [
                    {
                        "rule_id": rule_id,
                        "evidence_excerpt": excerpt,
                        "rationale": rationale,
                        "adjudication": adjudications.get(f"{task_id}::{rule_id}"),
                    }
                    for rule_id, excerpt, rationale in findings
                ],
            }
        )
    return entries


def _print_proposals(proposals: list[dict]) -> None:
    if not proposals:
        print("(no proposals)")
        return
    for p in proposals:
        print(f"[{p['id']}] {p['status']:<10} {p['page_path']} x {p['rule_id']} ({p['jurisdiction'] or '?'})")
        print(f"      offending: {p['offending_text']!r}")
        print(f"      proposed:  {p['proposed_text']!r}")


def _print_disputed(entries: list[dict]) -> None:
    if not entries:
        print("(no disputed tasks)")
        return
    for entry in entries:
        print(f"task {entry['task_id']} -- ESCALATED")
        for f in entry["findings"]:
            adj = f["adjudication"]
            adj_str = f"{adj['verdict']}: {adj['citation']}" if adj else "(no adjudication record)"
            print(f"    finding: {f['rule_id']} -- {f['evidence_excerpt']!r}")
            print(f"    adjudication: {adj_str}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Human review queue: list / approve / reject / disputed")
    parser.add_argument("--db", required=True, help="path to the ledger SQLite db")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list proposals (optionally filtered by --status)")
    list_parser.add_argument("--status", default=None)

    sub.add_parser("disputed", help="list ESCALATED verify-stage tasks with both artifacts")

    approve_parser = sub.add_parser("approve", help="approve one proposal by id")
    approve_parser.add_argument("proposal_id", type=int)

    reject_parser = sub.add_parser("reject", help="reject one proposal by id")
    reject_parser.add_argument("proposal_id", type=int)

    args = parser.parse_args(argv)
    conn = sqlite3.connect(args.db)
    try:
        if args.command == "list":
            _print_proposals(list_proposals(conn, status=args.status))
        elif args.command == "disputed":
            _print_disputed(list_disputed(conn))
        elif args.command == "approve":
            print(approve_proposal(conn, args.proposal_id))
        elif args.command == "reject":
            print(reject_proposal(conn, args.proposal_id))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
