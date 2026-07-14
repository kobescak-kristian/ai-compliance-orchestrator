# ADR 0004: Three-Actor Answer-Key Protocol

## Status
Accepted — Executed (2026-07-08, Phase 1b). Recorded 2026-07-09 (Phase 4
completion reconciliation): this ADR was referenced as "pending" from
`evals/INJECTION_SPEC.md`'s header at Phase 1b time but never written up
as its own file. This is that record, written after the fact, describing
what was actually executed — not a new decision.

## Date: 2026-07-08 (executed) / 2026-07-09 (recorded)

## Context
BLUEPRINT.md §7 named the answer-key authorship split as an open item
("the model that writes the seeded pages must not author the answer
key") that had to be resolved before Phase 1 kickoff — SPEC.md §10.7
tracked it as `OPEN`, explicitly "Not Code's decision." A single model
authoring both the injected violations and the eval dataset it's later
scored against is the same shared-author-leakage limitation the
ai-claim-verification-agent's own eval named and accepted; this project
fixes it by construction rather than by caveat (BLUEPRINT.md §7).

## Decision
SPEC.md §10.7, resolved 2026-07-07: a four-role split, no role
authoring both the injected content and its own check.

1. **Spec author — Claude (strongest model available):** wrote the three
   jurisdiction rule sets and `evals/INJECTION_SPEC.md`, including the
   expected verdict per page brief (proto-answer-key material).
2. **Page author — Claude Code:** materialized `evals/dataset/pages/
   p01.html`…`p12.html` from those briefs (commit `3124c1e`). Reads the
   spec to build the pages; its independence from that document is not
   claimed, and INJECTION_SPEC.md says so explicitly.
3. **Blind labeler — ChatGPT:** a separate model family, given only the
   12 finished pages, the three rule sets, and the applicability
   semantics — never INJECTION_SPEC.md, never a draft key. Labeled all
   288 (page × jurisdiction × rule) cells independently.
4. **Adjudicator — Kristian:** diffed the spec-author's draft key
   against the blind labels; agreements froze into `evals/
   answer_key.yaml`; the 7 disagreements were adjudicated case-by-case
   (D1–D7, `evals/ADJUDICATION_LOG.md`).

Execution record: `evals/ADJUDICATION_LOG.md` (288/288 cells labeled,
97.6% blind-label agreement, 30-violation frozen key, net +2 over the
spec author's 28-violation draft from D4/D5). Provenance record for the
page-author's inputs: `evals/provenance/` (this Phase 4 completion).

## Consequences
- The committed answer key is authored by no single model — the stated
  goal of SPEC.md §10.7 is met, not just declared.
- **Named residual (not resolved by this protocol):** the spec author,
  page author, and this system's own checker agents are all Claude
  family. Cross-family independence exists at exactly one seam — the
  blind labeler (ChatGPT) checking the *key* — and nowhere else in the
  pipeline. Concretely: blind labeling verifies that the frozen answer
  key is *correct* (a second, differently-trained model reading the
  same pages reaches the same verdicts); it does **not** verify that the
  checker agents' behavior is *independent of the page/key authors'
  stylistic habits* — a Claude-family blind spot shared by spec author,
  page author, and checker alike would not be caught by this protocol,
  because nothing in the loop that actually runs the checkers is
  non-Claude. This must be stated plainly wherever precision/recall
  numbers are reported (README, EVAL_RESULTS.md), the same way ADR-0003
  requires the synthetic-rulesets caveat to travel with every result.
- The blind-label diff (D1, D4, D5, D6) caught two genuine spec-author
  errors (D4/D5, net +2 violations) and one rule-scope miss (D1) that
  the spec author's own draft key got wrong — direct evidence the
  cross-family seam does real work at the one place it exists, which is
  also why its scope limit above matters: it is real, but narrow.
- Provenance gate (standing decision, recorded 2026-07-09): Phase 5 is
  blocked until `evals/provenance/` — the reconstructed page briefs,
  the page-author's binding construction rules, and the pre-blind
  filler-sweep report — is committed. See `evals/provenance/README.md`.

## Addendum (2026-07-14)

Evidence pointer added at gate-0 verification for the publication
window (Q-24): the executed protocol and frozen answer key this ADR
records are committed at `dd155bf` and `0d84bf9`; the adjudication
record cited generically above is `evals/ADJUDICATION_LOG.md` as of
those commits. Added as a dated addendum, not an edit to the
original text — the original ADR body is unchanged.
