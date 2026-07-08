"""Deterministic stub checker: returns hand-written fixture payloads for
CheckTasks, standing in for the real caged LLM checker agent (Phase 3).

Fixture verdicts below are invented for orchestration testing and are
NOT derived from evals/answer_key.yaml -- the bounds rule (the answer
key must never appear in any agent's input or output) applies to stubs
too (BLUEPRINT.md §7). They will not match the frozen key and are not
meant to.

Configurable failure injection lets FI-1/FI-2 exercise the orchestrator's
handling of a budget trip and a schema-invalid payload without a real
agent.
"""
from __future__ import annotations

from orchestrator.pipeline import BudgetExceededError, task_id_for

# (page_path, jurisdiction, rule_id) -> (verdict, evidence_excerpt, rationale).
# Anything not listed defaults to a COMPLIANT fixture below. Hand-written,
# independent of the frozen answer key.
FIXTURE_VERDICTS: dict[tuple[str, str, str], tuple[str, str, str]] = {
    ("p01.html", "MLT", "MLT-BT-01"): (
        "VIOLATION", "stub fixture: wagering text not adjacent to offer",
        "stub fixture rationale: adjacency check",
    ),
    ("p01.html", "GBR", "GBR-GE-01"): (
        "VIOLATION", "stub fixture: no GBR licence line found",
        "stub fixture rationale: licence-line presence check",
    ),
    ("p03.html", "GBR", "GBR-PC-02"): (
        "VIOLATION", "stub fixture: urgency banner detected",
        "stub fixture rationale: urgency wording check",
    ),
    ("p03.html", "DEU", "DEU-BT-02"): (
        "NOT_APPLICABLE", "stub fixture: no odds boost content on page",
        "stub fixture rationale: content-absence N/A",
    ),
    ("p06.html", "MLT", "MLT-PC-01"): (
        "VIOLATION", "stub fixture: guarantee-adjacent wording",
        "stub fixture rationale: prohibited-claims check",
    ),
    ("p06.html", "GBR", "GBR-BT-01"): (
        "VIOLATION", "stub fixture: significant terms not adjacent",
        "stub fixture rationale: composite adjacency check",
    ),
    ("p08.html", "MLT", "MLT-PC-01"): (
        "VIOLATION", "stub fixture: guarantee-adjacent wording",
        "stub fixture rationale: prohibited-claims check",
    ),
    ("p08.html", "GBR", "GBR-PC-01"): (
        "VIOLATION", "stub fixture: guarantee-adjacent wording",
        "stub fixture rationale: prohibited-claims check",
    ),
    ("p12.html", "GBR", "GBR-RG-01"): (
        "VIOLATION", "stub fixture: RG block absent",
        "stub fixture rationale: RG element presence check",
    ),
}

_DEFAULT = ("COMPLIANT", "stub fixture: no issue found", "stub fixture rationale: default compliant")

# Test hook: (page_path, jurisdiction) -> failure mode, set by tests to
# force a task to simulate FI-1 ("budget") or FI-2 ("malformed").
FAILURE_MODES: dict[tuple[str, str], str] = {}


def configure_failure(page_path: str, jurisdiction: str, mode: str) -> None:
    FAILURE_MODES[(page_path, jurisdiction)] = mode


def reset_failures() -> None:
    FAILURE_MODES.clear()


def stub_checker(task) -> list[dict]:
    key = (task.page_path, task.jurisdiction)
    mode = FAILURE_MODES.get(key)

    if mode == "budget":
        raise BudgetExceededError(f"simulated budget/turn cap trip for {key}")

    item_id = task_id_for(task)
    payloads = []
    for rule_id in task.assigned_rules:
        verdict, excerpt, rationale = FIXTURE_VERDICTS.get(
            (task.page_path, task.jurisdiction, rule_id), _DEFAULT
        )
        payloads.append(
            {
                "page_path": task.page_path,
                "jurisdiction": task.jurisdiction,
                "rule_id": rule_id,
                "ruleset_version": task.ruleset_version,
                "verdict": verdict,
                "evidence_excerpt": excerpt,
                "rationale": rationale,
                "task_id": item_id,
            }
        )

    if mode == "malformed" and payloads:
        del payloads[0]["rule_id"]  # schema-invalid: required field missing

    return payloads
