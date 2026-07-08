"""Deterministic stub planner: returns hand-written fixture
RemediationProposal payloads for VIOLATION findings, standing in for the
real caged LLM planner agent (Phase 5). Emits proposals only -- this
stub cannot write, edit, or publish anything, matching the real agent's
bound (BLUEPRINT.md §4).

Fixtures are invented for orchestration testing, independent of
evals/answer_key.yaml (BLUEPRINT.md §7 bounds rule applies to stubs
too).
"""
from __future__ import annotations

from orchestrator.pipeline import BudgetExceededError

STUB_RUN_ID = "phase2-stub-run"

# Test hook: (page_path, rule_id) -> failure mode ("budget" | "malformed").
FAILURE_MODES: dict[tuple[str, str], str] = {}


def configure_failure(page_path: str, rule_id: str, mode: str) -> None:
    FAILURE_MODES[(page_path, rule_id)] = mode


def reset_failures() -> None:
    FAILURE_MODES.clear()


def stub_planner(finding) -> dict | None:
    """finding is a contracts.schemas.ViolationFinding with verdict ==
    VIOLATION (run_plan_stage filters non-violations before calling this).
    """
    key = (finding.page_path, finding.rule_id)
    mode = FAILURE_MODES.get(key)

    if mode == "budget":
        raise BudgetExceededError(f"simulated budget/turn cap trip for {key}")

    payload = {
        "page_path": finding.page_path,
        "rule_id": finding.rule_id,
        "offending_text": finding.evidence_excerpt,
        "proposed_text": f"stub fixture proposal: revise per {finding.rule_id}",
        "evidence_refs": [finding.task_id],
        "created_by_run_id": STUB_RUN_ID,
    }

    if mode == "malformed":
        del payload["rule_id"]  # schema-invalid: required field missing

    return payload
