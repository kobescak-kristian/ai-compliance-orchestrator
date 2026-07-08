# ADJUDICATION_LOG — eval dataset answer key (Phase 1b-ii)
*2026-07-08. Companion to evals/INJECTION_SPEC.md and evals/answer_key.yaml
(v1.0, FROZEN). Records the three-actor protocol's blind-label diff and
every adjudication ruling that produced the frozen key.*

## Three-actor protocol

1. **Spec author (strongest model):** wrote the three rule sets and
   evals/INJECTION_SPEC.md, including the expected verdicts per page brief
   (proto-answer-key material).
2. **Page author (Claude Code):** materialized `evals/dataset/pages/p01.html`
   … `p12.html` from the briefs. Read INJECTION_SPEC.md to build the pages
   (its independence from that document is not claimed).
3. **Blind labeler (ChatGPT):** a temporary chat session, given only the 12
   finished pages and the three rule sets plus the applicability semantics
   (no INJECTION_SPEC.md, no draft answer key). Labeled every
   (page × jurisdiction × rule) cell — 288 cells across 12 pages × 24 rules.
4. **Adjudicator (Kristian):** diffed the spec-author's draft key against
   the blind labels; agreements froze into `evals/answer_key.yaml`;
   disagreements adjudicated case-by-case below.

The committed answer key is therefore authored by no single model.

## Pre-blind filler sweep

Before the pages were sent to the blind labeler, a keyword grep across all
12 pages (`guarant|risk-free|lose nothing|free|last chance|ends soon|...`)
caught one unintended trigger: P12's invented "Second-Chance Bet" filler
offer combined a "free bet" claim with an adjacent deposit requirement —
structurally identical to the P01/P10 GBR-BT-02 pattern, but not part of
any brief and not counted in the spec author's violation total. Fixed by
rewording the offer to remove the free/deposit collision entirely (commit
`fa5d6a1`, prior session) before the blind pass began, so the blind labeler
never saw the defect.

## Blind-label diff

288/288 cells labeled. **281/288 agreement (97.6%).** 7 disagreements,
adjudicated below (D1–D7).

## Rulings

| # | Cell | Ruling | Rationale |
|---|---|---|---|
| D1 | p03 · MLT-BT-03 | → **NOT_APPLICABLE** | Blind labeler correct; the spec-author key missed a rule-level N/A. P03's sports free bet is genuinely deposit-free ("no deposit needed"), so there is no deposit-linked bonus offer on the page for MLT-BT-03 to govern. |
| D2 | p04 · GBR-RG-02 | **NOT_APPLICABLE stands** | GBR-RG-02 governs pages promoting a gambling offer; P04 is a slot review that promotes no confirmed offer. Blind label and draft key agreed — logged as a confirmed cell, not a change. |
| D3 | p05 · MLT-PC-01 | **Page reworded; cell remains COMPLIANT** | The tagline "Play and win big every day!" was flagged in INJECTION_SPEC.md itself as a deliberate adjudication candidate (aspirational vs. guarantee, ambiguous under MLT-PC-01). Ruling: don't resolve the ambiguity by fiat — replace the string with an inert one ("Big games, every day.") so the page no longer tests a judgment call. Exception logged below. |
| D4 | p06 · MLT-BT-02 | → **VIOLATION** | Spec-author design error, caught by the blind pass: offer A's expiry is genuinely absent from the page (only "35x wagering" is adjacent; min-deposit and expiry sit behind a link to a page that was never populated with content). MLT-BT-02 is a presence rule, not an adjacency rule like GBR-BT-01 — "behind a link" means absent from the evaluated page, not merely non-adjacent. |
| D5 | p06 · MLT-BT-03 | → **VIOLATION** | Same mechanism as D4, applied to the minimum-deposit disclosure for offer A. |
| D6 | p06 · DEU-BT-02 | → **NOT_APPLICABLE** | DEU-BT-02 governs odds boosts; P06 has no odds-boost content (that content type is unique to P03). Nothing on the page for the rule to apply to. |
| D7 | p07 · DEU-RG-02 | **VIOLATION stands** | Semantics tightened for future checkers: "deposit-based play" (DEU-RG-02's trigger) is read to include any real-money product promotion, not only bonus-linked deposits. P07's live-casino promotion is real-money play and qualifies, even though no bonus is offered on the page. |

## Violation total

28 (spec-author draft) → **30** (frozen key), net +2 from D4 and D5. D1 and
D6 move cells from COMPLIANT to NOT_APPLICABLE (no count change). D2, D3,
D7 confirm existing verdicts (no count change).

## Logged exception: D3 post-blind-pass page edit

P05's tagline was edited *after* the blind-label pass completed (the blind
labeler scored the original "Play and win big every day!" as COMPLIANT
under MLT-PC-01, consistent with the draft key). The page was then changed
to remove the ambiguity rather than to change the verdict — "Big games,
every day." is not a claim of any kind, so MLT-PC-01 COMPLIANT holds
trivially and no re-label was required. This is recorded as an exception
because it is the one point where the frozen key's page content and the
blind labeler's scored content diverge; the divergence is inert by
construction (an ambiguous compliant string replaced by an unambiguous
compliant string, same verdict either way).
