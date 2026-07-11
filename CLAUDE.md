# ai-compliance-orchestrator

- Read BLUEPRINT.md before any work.
- Phase start: update STATE.md status to in-progress before any phase work.
- One phase per session, per §9; stop at phase boundary and report.
- Never write agent code before Phase 1 is committed and Kristian-approved.
- Done = acceptance criteria + exit code 0 shown, never file existence.
- If the blueprint does not cover a mid-phase decision: STOP and ask
  Kristian — do not decide and log.
- No secrets in any file or output; .env local + gitignored only.

## Session boot and governance (applies to every session here)
- Governance home: kristian-os (PRINCIPLES -> GOVERNANCE ->
  FAILURE_REGISTER). Read before any irreversible action.
- Boot: read this repo's STATE.md first; the operating contract
  (SPEC) loads globally.
- Before any write: environment fingerprint (pwd + git config
  user.email; /home/user/ path or noreply@anthropic.com = cloud
  sandbox = read-only, no pen). Pen check on main at open AND
  immediately before every commit.
- Eval discipline: gates and thresholds are never adjusted after a
  run; the official gate result (FAIL, run gate-9328e564) is
  published as final by decision — no re-run, no re-gate this
  cycle. Scorers freeze before runs.
- Adjudication: policy/ADJUDICATION_POLICY.md is binding on all
  verifier work; deviations require an ADR.
- Evidence: commits here are hash-pinned by published records
  (ADJUDICATION_LOG, eval results, the agent reuse pin). NO
  history rewrites, ever.
- Close ritual: commit -> push origin main -> verify
  origin/main..HEAD empty -> report verbatim. Feature-branch push
  is not done.
- Work comes from the governance repo's queue (kristian-os,
  FABLE_QUEUE); do not invent tasks.
