"""Subprocess entry point invoked by nodes/verifier.py. Runs the shipped
ai-claim-verification-agent's own agent.harness.run_case_result()
unmodified -- imported, not edited -- and prints its raw findings
(including evidence_note, which the shipped CLI's run_case.py formats
away) as JSON on stdout. This script itself lives in this repo, not the
shipped one; nothing is ever written into the shipped repo except the
case's own data files (written by nodes/verifier.py, removed after the
run -- see the git-status-clean check in tests/test_bounds.py and the
Phase 4 dev-leg report). With VERIFIER_DATASET_ROOT and
VERIFIER_AUDIT_DB set (every runner series), not even those (P3).

Usage:
    python nodes/verifier_runner.py <repo_path> <case_id> <run_id> <model> <max_budget_usd>

On success: prints one JSON object to stdout, exits 0.
On any failure (bad case, agent error, exception): prints an error
message to stderr, exits 1 -- nodes/verifier.py maps this to a
task-atomic FAILED, per policy/ADJUDICATION_POLICY.md §12.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys


def main() -> None:
    if len(sys.argv) != 6:
        print("Usage: verifier_runner.py <repo_path> <case_id> <run_id> <model> <max_budget_usd>", file=sys.stderr)
        sys.exit(1)

    repo_path, case_id, run_id, model, max_budget_usd = sys.argv[1:]
    sys.path.insert(0, repo_path)

    try:
        # Owner decision D1 (2026-11-03): no dotenv load. load_dotenv()
        # searched upward from this folder and could pick up an API key
        # outside the repository; the session uses the subscription login.
        from agent.harness import run_case_result  # noqa: E402 -- shipped repo, unmodified

        # D3: keep the shipped agent's audit DB out of its checkout. Its
        # agent/audit.py does `from .config import AUDIT_DB_PATH`, so the
        # name is patched on agent.audit itself (agent.config alone would
        # not reach it). The shipped code on disk is not changed.
        audit_db = os.environ.get("VERIFIER_AUDIT_DB")
        if audit_db:
            import agent.audit  # noqa: E402 -- shipped repo, unmodified

            agent.audit.AUDIT_DB_PATH = audit_db

        # P3: the case files (page text) live in a private folder, not in
        # the checkout. DATASET_ROOT is copied into agent.pages and
        # agent.harness by `from .config import DATASET_ROOT`, so all three
        # names are patched; the shipped path cage then holds at this root.
        dataset_root = os.environ.get("VERIFIER_DATASET_ROOT")
        if dataset_root:
            from pathlib import Path

            import agent.config  # noqa: E402 -- shipped repo, unmodified
            import agent.harness  # noqa: E402 -- shipped repo, unmodified
            import agent.pages  # noqa: E402 -- shipped repo, unmodified

            root = Path(dataset_root).resolve()
            agent.config.DATASET_ROOT = agent.pages.DATASET_ROOT = agent.harness.DATASET_ROOT = root

        result, findings = asyncio.run(
            run_case_result(case_id, run_id=run_id, model=model, max_budget_usd=float(max_budget_usd))
        )
    except Exception as exc:  # noqa: BLE001 -- any failure here is a verifier-invocation failure
        print(f"verifier_runner failed for case {case_id!r}: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.is_error:
        # api_error_status lets nodes/verifier.py tell a provider error
        # (auth, rate limit, overload) from an agent error (D6); the error
        # text lets it see a subscription usage-limit message (RT2-05).
        status = getattr(result, "api_error_status", None)
        print(
            f"shipped agent run ended in error for case {case_id!r}: {result.subtype} "
            f"api_error_status={status} error_text={(getattr(result, 'result', None) or '')[:300]!r} "
            f"errors={(getattr(result, 'errors', None) or [])!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    payload = {
        "findings": findings,
        "cost_usd": result.total_cost_usd,
        "num_turns": result.num_turns,
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
