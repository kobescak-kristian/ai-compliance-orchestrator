"""Subprocess entry point invoked by nodes/verifier.py. Runs the shipped
ai-claim-verification-agent's own agent.harness.run_case_result()
unmodified -- imported, not edited -- and prints its raw findings
(including evidence_note, which the shipped CLI's run_case.py formats
away) as JSON on stdout. This script itself lives in this repo, not the
shipped one; nothing is ever written into the shipped repo except the
case's own data files (written by nodes/verifier.py, removed after the
run -- see the git-status-clean check in tests/test_bounds.py and the
Phase 4 dev-leg report).

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
import sys


def main() -> None:
    if len(sys.argv) != 6:
        print("Usage: verifier_runner.py <repo_path> <case_id> <run_id> <model> <max_budget_usd>", file=sys.stderr)
        sys.exit(1)

    repo_path, case_id, run_id, model, max_budget_usd = sys.argv[1:]
    sys.path.insert(0, repo_path)

    try:
        from dotenv import load_dotenv

        load_dotenv()

        from agent.harness import run_case_result  # noqa: E402 -- shipped repo, unmodified

        result, findings = asyncio.run(
            run_case_result(case_id, run_id=run_id, model=model, max_budget_usd=float(max_budget_usd))
        )
    except Exception as exc:  # noqa: BLE001 -- any failure here is a verifier-invocation failure
        print(f"verifier_runner failed for case {case_id!r}: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.is_error:
        print(f"shipped agent run ended in error for case {case_id!r}: {result.subtype}", file=sys.stderr)
        sys.exit(1)

    payload = {
        "findings": findings,
        "cost_usd": result.total_cost_usd,
        "num_turns": result.num_turns,
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
