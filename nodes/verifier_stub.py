"""Deterministic stub for the verifier node: returns hand-written fixture
AccuracyFinding payloads, standing in for the real ai-claim-verification-
agent subprocess wrapper (ADR-0002, Phase 4). Not wired into the Phase 2
pipeline run -- the verifier is an optional fourth checker per
BLUEPRINT.md §2 step 3, and its only relevant failure mode (FI-5,
conflicting findings) stays skipped until Phase 4. This stub exists so
the node has a fixture-shaped callable to swap the real subprocess node
into later, and so agents/planner and agents/checker are not the only
stubbed node type in the repo.

Fixtures are invented for orchestration testing, independent of
evals/answer_key.yaml (BLUEPRINT.md §7 bounds rule applies to stubs
too).
"""
from __future__ import annotations

from orchestrator.pipeline import BudgetExceededError

# (page_path, claim) -> (verdict, source, evidence). Anything not listed
# defaults to UNVERIFIABLE below.
FIXTURE_VERDICTS: dict[tuple[str, str], tuple[str, str, str]] = {
    ("p03.html", "Boosted odds 3.50 on tonight's match!"): (
        "UNVERIFIABLE", "none", "stub fixture: no base-odds source to compare against",
    ),
}

_DEFAULT = ("UNVERIFIABLE", "none", "stub fixture: no matching source found")

FAILURE_MODES: dict[tuple[str, str], str] = {}


def configure_failure(page_path: str, claim: str, mode: str) -> None:
    FAILURE_MODES[(page_path, claim)] = mode


def reset_failures() -> None:
    FAILURE_MODES.clear()


def stub_verifier(page_path: str, claim: str, task_id: str) -> dict:
    key = (page_path, claim)
    mode = FAILURE_MODES.get(key)

    if mode == "budget":
        raise BudgetExceededError(f"simulated budget/turn cap trip for {key}")

    verdict, source, evidence = FIXTURE_VERDICTS.get(key, _DEFAULT)
    payload = {
        "claim": claim,
        "verdict": verdict,
        "source": source,
        "evidence": evidence,
        "task_id": task_id,
    }

    if mode == "malformed":
        del payload["verdict"]  # schema-invalid: required field missing

    return payload
