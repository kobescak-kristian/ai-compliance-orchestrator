# ai-compliance-orchestrator — Phase 4 adjudication policy
*v1.0 — 2026-07-08. Pre-committed policy: written before any Phase 4 code
exists (gates before agents). Governs how verifier and checker disagreement
is resolved. Sonnet builds Phase 4 following this document; deviations
require an ADR, not silent adaptation. Target path:
`ai-compliance-orchestrator/policy/ADJUDICATION_POLICY.md`, committed
before the first verifier code file.*

*Phase 4 session amendments (§§10–15, and the inline §4 citation swap)
folded in 2026-07-08 per Kristian's Phase-4 instruction — each marked
"Phase 4 amendment" at its point of insertion.*

## 1. Roles (hard boundary)

- **Checker** proposes findings. Only the checker can assert a violation.
- **Verifier** challenges findings. It re-derives each finding
  independently and issues a verdict on it. The verifier can NEVER add a
  new finding — a violation the checker missed stays missed and shows up
  as a recall failure. Rationale: if the verifier can also detect, the
  roles blur, scoring attribution breaks, and the verifier becomes a
  second checker with no one checking it.
- **Orchestrator** applies this policy mechanically. It never judges
  content.

## 2. Verifier input (blindness rules)

The verifier receives, per finding: the FindingRecord (rule_id,
jurisdiction, verdict, evidence anchor, severity), the rule text, and the
page text. It does NOT receive:

- the answer key (bounds test extends to the verifier — same marker-scan
  pattern as Phase 3),
- the checker's reasoning/transcript (prevents agreement anchoring — the
  verifier must re-derive from rule + page, not audit the checker's
  prose),
- other findings on the same page (each finding adjudicated in
  isolation; no verdict momentum).

## 3. Verdicts (exactly three)

| Verdict | Meaning | Requirement |
|---|---|---|
| CONFIRMED | Finding stands; enters the report as an assertion | Verifier cites the bright-line criterion AND the page evidence it verified |
| REJECTED | Finding removed from assertions; retained in ledger with status | Verifier MUST cite the specific bright-line criterion the evidence fails — no naked rejections. If it cannot cite, it may not reject. |
| DISPUTED | Verifier cannot confirm or cleanly reject | Both positions recorded; finding published in a separate "disputed" section of the report, not as an assertion |

Uncertainty resolves to DISPUTED, never to REJECTED. A rejection is a
positive claim ("this evidence fails criterion X") and carries the same
citation burden as a finding.

## 4. Precedence and limits

- The verifier may not edit a finding — not its severity, not its
  evidence anchor, not its rule mapping. Confirm, reject, or dispute the
  record as-is. (Severity is a rule-set field, never assigned per-finding
  — rule-set quality bar, Phase 1 spec. **[Phase 4 amendment: citation
  swapped from "per R2" to the Phase 1 rule-set-quality-bar source; the
  substance of this clause is unchanged.]**)
- One adjudication cycle only. The verifier's verdict is final for the
  run — no checker rebuttal, no loops. The pipeline stays acyclic.
  Escalation path for DISPUTED is a human (Kristian) at report-review
  time, outside the run.
- Adjudication is deterministic in structure: same finding set in, same
  ledger states out (idempotent re-run per FI-6 — re-adjudicating a
  finding already in a terminal verdict state is a no-op).

## 5. Scoring treatment (what the eval gate sees)

The gate scores **the system's assertions**: CONFIRMED findings only.

- CONFIRMED + in key → TP. CONFIRMED + not in key → FP.
- Key violation with no CONFIRMED finding → FN — regardless of whether
  the checker found it and the verifier rejected/disputed it. A true
  violation the system failed to assert is a system miss; the internal
  reason is diagnostic, not exculpatory.
- DISPUTED findings are never scored as assertions. If a disputed
  finding matches a key violation, it is still an FN (see above) — the
  honest reading is "the system could not commit to a true finding."
- The run report includes an **adjudication table**: counts of
  CONFIRMED / REJECTED / DISPUTED, and for the eval run, how many
  rejections were correct (rejected FP = verifier added value) vs.
  wrong (rejected TP = verifier destroyed recall). This table is the
  published evidence that the verifier earns its cost.

## 6. Ledger and audit requirements

- Every verdict writes a ledger row: finding_id, verdict, verifier
  citation (criterion + evidence), model, timestamp, run_id. Rejected
  and disputed findings are retained forever — disagreement is
  evidence, never deleted.
- No silent overwrites: a finding's assertion status changes only
  through an adjudication row. FI-5 test asserts exactly this.

## 7. FI-5 test (unskip in Phase 4)

Seed a synthetic conflict (stub checker emits a finding the stub
verifier is scripted to reject, and one to dispute). Assert: both
positions in ledger; report shows the disputed row in the disputed
section and excludes the rejected row from assertions; re-run is
idempotent; nothing overwritten. Plus the verifier bounds test: key
markers absent from all verifier I/O; verifier receives no checker
transcript (assert on the constructed prompt, not on trust).

## 8. Model routing

Dev leg: Haiku 4.5 verifier over the Phase 3 dev findings — expected
outcome is a populated adjudication table, not gate-passing numbers.
Official run: Sonnet 4.6 for both roles, per blueprint. Same-model
checker/verifier is a stated limitation (correlated errors — the
verifier catches sloppiness, not blind spots); goes in the README
honest-limitations section verbatim intent: "checker and verifier share
a model; adjudication guards against per-finding error, not
model-family blind spots."

## 9. Decisions locked (override by ADR only)

1. Verifier challenges; never detects. 2. Three verdicts; uncertainty →
DISPUTED; rejections carry citation burden. 3. Gate scores CONFIRMED
only; disputed-true = FN. 4. No finding edits; one cycle; acyclic.
5. Disagreement retained in ledger permanently; adjudication table
published. 6. Verifier blind to key AND checker reasoning.

## 10. Scope — which findings are adjudicated (Phase 4 amendment)

Only **VIOLATION**-verdict findings are adjudicated. COMPLIANT and
NOT_APPLICABLE findings are never sent to the verifier and never
challenged.

**Named limitation:** a checker that wrongly calls a true violation
COMPLIANT is never caught by this layer — a wrong COMPLIANT is a
recall-failure path, not an adjudication-failure path, explicit by
design. The verifier only ever challenges what the checker already
asserted; per §1 it can never add a finding the checker missed. This is
the same boundary as §1's "verifier never detects," restated at the
scope level.

## 11. TaskState mapping (Phase 4 amendment)

Adjudication verdicts roll up to the *originating CheckTask's*
verify-stage terminal state (not a new per-finding task):

- **≥ 1 DISPUTED finding** on the task → task state **ESCALATED**.
- **Rejected-only or all-CONFIRMED** (zero DISPUTED findings, whatever
  the mix of CONFIRMED/REJECTED) → task state **DONE**.

This mapping governs `orchestrator/pipeline.py`'s verify stage exactly
as the check/plan stages' terminal-state mapping is governed by
BLUEPRINT.md §3.

## 12. Verifier identity (Phase 4 amendment)

The verifier is the shipped **ai-claim-verification-agent**, run
byte-literal unchanged — no edit to its prompt, tools, or harness code,
ever. All Phase 4 adaptation (case assembly, subprocess invocation,
output parsing, verdict remapping) lives in this orchestrator's
`nodes/assembler.py` and `nodes/verifier.py`, never inside the shipped
repo.

- Repo: `ai-claim-verification-agent` (local path: sibling checkout,
  `../ai-claim-verification-agent` relative to this repo's root — path
  is environment-specific, see `config.yaml`; remote
  `https://github.com/kobescak-kristian/ai-claim-verification-agent.git`,
  **PRIVATE** as of 2026-07-08).
- **Pinned commit:** `d444b13c3ba07b9f4798d3298ec3bfc92da5a960`
  ("pre-flip: scrub internal references (CLAUDE.md, SPEC.md); ADR-002
  records DEMO_SCRIPT Tier-1 exception per 2026-07-05 locked decision").
  Recorded here and in this orchestrator's `config.yaml`; both must
  match at every verifier invocation or the run fails loudly rather than
  silently drifting onto an unpinned version of the shipped code.
- **Fallback trigger:** editing the shipped agent's prompt or code to
  make Phase 4 work is forbidden. If the adjudicator role cannot be made
  to work through the assembler alone — i.e. the shipped agent's fixed
  four-tool contract genuinely cannot express what adjudication needs —
  that need is itself the signal to fall back to a purpose-built
  adjudicator agent, not to fork the shipped one. See §13.
- **Publication dependency:** the reuse claim ("we didn't fork the
  shipped agent, we reused it") only holds up publicly once the shipped
  repo is public and this pinned hash is verifiable by a reader. Both
  `ai-claim-verification-agent` and `ai-compliance-orchestrator` are
  private as of this writing — this is a named gate on the orchestrator's
  public card, not yet met, tracked outside this session (kristian-os).

## 13. Fallback trigger — purpose-built adjudicator (Phase 4 amendment)

Recorded here at policy-commit time; **evaluated at dev-leg step (§8
model routing, dev leg)**, not decided in advance. The fallback (build a
purpose-built adjudicator agent instead of reusing the shipped one)
fires if, on the dev leg:

- the verifier **wrongly rejects more than 1 true finding** (rejected a
  finding that matches the frozen answer key), OR
- any of its **REJECTED verdicts fail §3's citation burden** on manual
  review (a rejection that does not cite the specific bright-line
  criterion the evidence fails is not a valid rejection under §3).

If neither condition holds, the shipped agent stays as the adjudicator
and the fallback is recorded as not fired, with the dev-leg evidence
cited.

## 14. Verdict mapping (Phase 4 amendment)

The shipped agent's native verdict schema (SUPPORTED / CONTRADICTED /
UNVERIFIABLE, per its `log_finding` tool) maps onto this policy's three
adjudication verdicts (§3) as follows — fixed, not configurable per run:

| Shipped agent verdict | Adjudication verdict |
|---|---|
| SUPPORTED | CONFIRMED |
| CONTRADICTED | REJECTED |
| UNVERIFIABLE | DISPUTED |

This mapping is what "the contract adapts to the shipped agent, not the
other way around" (BLUEPRINT.md §5) means concretely for Phase 4: the
assembler frames each VIOLATION finding as a claim the shipped agent can
SUPPORT/CONTRADICT/find UNVERIFIABLE about, and this table is the only
place that meaning gets translated back into CONFIRMED/REJECTED/DISPUTED.

## 15. Expectation note (Phase 4 amendment)

The Phase 3 dev leg (run_id dev-27b9e6bf, `evals/EVAL_RESULTS.md`) scored
**FP = 0** pooled. On an FP-poor dataset like this one, the adjudication
layer's REJECTED path has nothing to catch by construction — there is no
live false positive for the verifier to correctly reject in this
specific run. The dev-leg adjudication table is therefore read as **the
n = 0 insurance form**: it proves the mechanism runs correctly end to end
(ledger rows, task-state mapping, report sections) on real Phase 3
output, not that it has caught a real error yet. A dataset with FPs
present would be needed to demonstrate the REJECTED path earning its
cost live; that is a gate-run (Phase 6) question, not a dev-leg one.
