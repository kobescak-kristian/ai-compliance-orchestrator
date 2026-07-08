"""Deterministic inventory of published pages and committed rule sets;
builds one contracts.schemas.CheckTask per (page x jurisdiction). No LLM.

Also owns read_ruleset(): the checker-boundary tool a real checker agent
will call in Phase 3 (BLUEPRINT.md §4 -- fetch_page, read_ruleset (own
jurisdiction only), emit_finding). Implemented here, deterministically,
so the rule-isolation + path-escape rejection is enforced and audited
(FI-7) before any agent exists to (mis)use it.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from contracts.schemas import CheckTask, ComplianceRule

KNOWN_JURISDICTIONS = ("MLT", "GBR", "DEU")
RULESET_FILES = {"MLT": "mlt-v1.json", "GBR": "gbr-v1.json", "DEU": "deu-v1.json"}

MARKETS_RE = re.compile(r"Markets:\s*([A-Z, ]+)")


class RuleAccessDenied(Exception):
    """Raised when a jurisdiction requests a rule set it is not entitled
    to -- cross-jurisdiction access or a path-escape attempt in the
    requested jurisdiction string (BLUEPRINT.md §4, §6 FI-7)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_rulesets(rulesets_dir: str | Path) -> dict[str, list[ComplianceRule] | None]:
    """Load each known jurisdiction's rule set. A jurisdiction maps to
    None if its file is missing, fails to parse, or fails contract
    validation (FI-4) -- callers must treat None as an explicit gap,
    never silently skip it.
    """
    rulesets_dir = Path(rulesets_dir)
    result: dict[str, list[ComplianceRule] | None] = {}
    for jurisdiction, fname in RULESET_FILES.items():
        path = rulesets_dir / fname
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            result[jurisdiction] = [ComplianceRule(**r) for r in raw]
        except (OSError, json.JSONDecodeError, ValidationError):
            result[jurisdiction] = None
    return result


def extract_markets(page_html: str) -> list[str]:
    """Parse the page's `Markets: X, Y` footer line into target codes."""
    match = MARKETS_RE.search(page_html)
    if not match:
        return []
    return [m.strip() for m in match.group(1).split(",") if m.strip()]


def build_check_tasks(
    pages_dir: str | Path, rulesets_dir: str | Path
) -> tuple[list[CheckTask], set[str]]:
    """Inventory every page x targeted-jurisdiction pair into a CheckTask.

    Returns (tasks, missing_jurisdictions). A page targeting a
    jurisdiction whose rule set failed to load still gets a CheckTask
    (assigned_rules=[]) so the gap is visible and gate-able downstream
    (FI-4), rather than the page silently losing that jurisdiction.
    """
    pages_dir = Path(pages_dir)
    rulesets = load_rulesets(rulesets_dir)
    missing = {j for j, rules in rulesets.items() if rules is None}

    tasks: list[CheckTask] = []
    for page_path in sorted(pages_dir.glob("*.html")):
        html = page_path.read_text(encoding="utf-8")
        for jurisdiction in extract_markets(html):
            if jurisdiction not in KNOWN_JURISDICTIONS:
                continue
            rules = rulesets.get(jurisdiction)
            tasks.append(
                CheckTask(
                    page_path=page_path.name,
                    jurisdiction=jurisdiction,
                    ruleset_version=rules[0].ruleset_version if rules else "UNKNOWN",
                    assigned_rules=[r.rule_id for r in rules] if rules else [],
                )
            )
    return tasks, missing


def read_ruleset(
    own_jurisdiction: str,
    requested_jurisdiction: str,
    rulesets_dir: str | Path,
    conn: sqlite3.Connection,
) -> list[ComplianceRule]:
    """A checker may only ever read its own jurisdiction's rule set
    (BLUEPRINT.md §4: "may never see other jurisdictions' rules"). Every
    call -- allowed or rejected -- writes an audit_log row (FI-7).
    """
    allowed = (
        requested_jurisdiction == own_jurisdiction
        and requested_jurisdiction in KNOWN_JURISDICTIONS
    )
    reason = None if allowed else "cross-jurisdiction or invalid jurisdiction requested"
    conn.execute(
        "INSERT INTO audit_log "
        "(requesting_jurisdiction, requested_jurisdiction, allowed, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (own_jurisdiction, requested_jurisdiction, int(allowed), reason, _now()),
    )
    conn.commit()

    if not allowed:
        raise RuleAccessDenied(
            f"jurisdiction {own_jurisdiction!r} may not read rule set "
            f"for {requested_jurisdiction!r}"
        )

    rulesets = load_rulesets(rulesets_dir)
    rules = rulesets.get(requested_jurisdiction)
    if rules is None:
        raise FileNotFoundError(
            f"rule set for {requested_jurisdiction!r} missing or corrupt"
        )
    return rules
