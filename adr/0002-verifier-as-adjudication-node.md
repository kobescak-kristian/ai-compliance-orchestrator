# ADR 0002: Verifier as Adjudication Node

## Status
Accepted (2026-07-08, Phase 4)

## Date: 2026-07-08

## Context
BLUEPRINT.md §2 step 3 originally framed the shipped
ai-claim-verification-agent as an independent fourth checker, running
its own claim-vs-source-pages verification and emitting AccuracyFinding
records into the same finding flow as the three jurisdiction checkers.
Designing the actual Phase 4 handoff surfaced a sharper, more valuable
role: the shipped agent re-deriving and challenging a jurisdiction
checker's own VIOLATION findings, rather than running a parallel,
unrelated check. This is the first artifact in the portfolio where a
previously-shipped, unmodified agent is reused in a *different* role
than its original design — a stronger reuse claim than "runs alongside"
if it can be made to work without editing the shipped agent at all.

policy/ADJUDICATION_POLICY.md (pre-committed 2026-07-08, before any
Phase 4 code) specifies this role in full: the verifier challenges
checker VIOLATION findings and issues CONFIRMED / REJECTED / DISPUTED
verdicts; it can never add a finding the checker missed; it is blind to
the answer key, the checker's reasoning, and sibling findings; and the
gate scores CONFIRMED findings only. This ADR records the *node
architecture* decision that makes that policy implementable against the
shipped agent without touching it.

## Decision
The verifier is an **adjudication node**, not a fourth checker. Given
one checker VIOLATION finding, `nodes/assembler.py` reframes it as the
shipped agent's own native case format (one target claim + rule text
and page as sources) and `nodes/verifier.py` invokes the shipped agent,
byte-literal unchanged, as a subprocess against that case — pinned to a
specific commit (`d444b13c3ba07b9f4798d3298ec3bfc92da5a960`, checked at
every invocation) — via `nodes/verifier_runner.py`, a small script that
lives in this repo and imports the shipped agent's own
`agent.harness.run_case_result` unmodified. The shipped agent's native
SUPPORTED / CONTRADICTED / UNVERIFIABLE verdict maps onto
CONFIRMED / REJECTED / DISPUTED (policy §14). All adaptation — case
assembly, subprocess invocation, output parsing, verdict remapping —
lives in this orchestrator; editing the shipped agent's prompt or code
is forbidden, and the need to would itself be the trigger to build a
purpose-built adjudicator instead (policy §12–13).

The case directory is written into the shipped repo's own
`evals/dataset/` (the only path its hardcoded `DATASET_ROOT` can read)
and always removed afterward, in a `finally` block — the shipped repo's
git working tree is checked clean before and after every invocation
(`tests/test_bounds.py::test_verifier_cage`, and directly in the Phase 4
dev-leg report, `evals/EVAL_RESULTS.md`).

## Consequences
- `contracts.schemas.AccuracyFinding`/`AccuracyVerdict` (the original
  "4th checker" contract) are superseded and retained, unused, as the
  Phase 2/3 scaffolding record of that earlier design — not deleted,
  since they document a real prior decision. `AdjudicationRecord` is
  the live contract for verifier output (Phase 4 contract amendment).
- `orchestrator.pipeline.run_verify_stage` groups findings by their
  originating CheckTask; a verifier invocation failure (non-zero exit,
  schema-invalid output, pinned-commit mismatch) fails that whole task
  atomically (task-atomic FAILED — the same atomicity FI-2 established
  for schema-invalid checker payloads, applied here to an
  agent-invocation failure rather than a content-payload failure). A
  task's terminal state is otherwise ESCALATED if any adjudication came
  back DISPUTED, else DONE, whatever the mix of CONFIRMED/REJECTED
  (policy §11) — this is FI-5's new behavior, superseding BLUEPRINT §6's
  original wording (noted in the test's own docstring).
- **Publication dependency:** the reuse claim ("we didn't fork the
  shipped agent, we reused it in a new role, unmodified") only holds up
  publicly once a reader can actually verify it — which requires the
  shipped `ai-claim-verification-agent` repo to be public *and* the
  pinned commit hash to be checkable, before this orchestrator's own
  public card ships. As of this ADR, both repos are private. This is a
  named, tracked gate on publication (kristian-os), not a blocker on
  continued Phase 4/5/6 development, which only needs local repo access.
- Trade-off: pinning to a specific commit means a future improvement to
  the shipped agent does not automatically flow into this orchestrator;
  bumping the pin is a deliberate, recorded action (this ADR + updated
  `config.yaml` + `policy/ADJUDICATION_POLICY.md` §12), not a silent
  drift.
- The dev-leg run (2026-07-08, `evals/EVAL_RESULTS.md`) is the first
  evidence this design actually works end to end against the real
  shipped agent: 16/16 findings adjudicated, shipped repo clean before
  and after, fallback trigger (policy §13) evaluated and not fired.
