"""Deterministic stub verifier: returns hand-written scripted
AdjudicationRecord-shaped payloads for VIOLATION findings, standing in
for the real subprocess adjudicator node (nodes/verifier.py, Phase 4).

Rewritten Phase 4, superseding its Phase 2 shape (which stubbed an
independent claim-vs-source checker returning AccuracyFinding payloads).
The verifier now adjudicates one checker VIOLATION finding at a time --
see policy/ADJUDICATION_POLICY.md. Configurable scripted verdicts let
FI-5 produce a REJECTED and a DISPUTED finding on demand, and let a test
exercise the "verifier subprocess failed" path without a real agent.
"""
from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.pipeline import VerifierInvocationError, finding_id_for

STUB_MODEL = "stub-verifier-v1"

# finding_id -> "CONFIRMED" | "REJECTED" | "DISPUTED" | "invocation_failed".
# Set by tests to script a specific adjudication outcome. Anything not
# listed defaults to CONFIRMED below.
SCRIPTED_VERDICTS: dict[str, str] = {}

_DEFAULT_VERDICT = "CONFIRMED"

_CITATIONS = {
    "CONFIRMED": "stub fixture: bright-line criterion met, evidence verified",
    "REJECTED": "stub fixture: evidence fails the cited bright-line criterion",
    "DISPUTED": "stub fixture: cannot confirm or cleanly reject from rule + page alone",
}


def configure_verdict(finding_id: str, verdict: str) -> None:
    SCRIPTED_VERDICTS[finding_id] = verdict


def reset_failures() -> None:
    SCRIPTED_VERDICTS.clear()


def stub_verifier(finding, rule, run_id: str) -> dict:
    """finding is a contracts.schemas.ViolationFinding with verdict ==
    VIOLATION (run_verify_stage filters non-violations before calling
    this, per policy §10 scope)."""
    fid = finding_id_for(finding)
    verdict = SCRIPTED_VERDICTS.get(fid, _DEFAULT_VERDICT)

    if verdict == "invocation_failed":
        raise VerifierInvocationError(f"simulated verifier subprocess failure for {fid}")

    return {
        "finding_id": fid,
        "verdict": verdict,
        "citation": _CITATIONS[verdict],
        "model": STUB_MODEL,
        "timestamp": datetime.now(timezone.utc),
        "run_id": run_id,
    }
