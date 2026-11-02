# Ruleset v1.1: interpretation notes (PROPOSED, for owner signature)

Status: **PROPOSED 2026-11-02.** Not in force. The owner signs or changes
this text at the P1 stop (repair program P-001, defect D7). Until then
`rulesets/*.json` stay at v1.0 and nothing here reaches any agent.

## What changes and what does not

- Only the `rule_text` of 11 of the 24 rules changes. The first sentence of
  each stays word for word; one "Interpretation (v1.1):" note is appended.
- No schema change, no new rule, no severity change, no category change.
- `ruleset_version` becomes `v1.1` in all three files (DEU, GBR, MLT), so
  every finding cites the version it was judged under.
- On signature, P2 writes these strings into `rulesets/deu-v1.json`,
  `rulesets/gbr-v1.json` and `rulesets/mlt-v1.json` (file names unchanged,
  because `intake/inventory.py` loads them by name).

## Why these notes are allowed (source of each bright line)

Each note states a boundary that the frozen v1.0 key already applies but
that the one-line rule text does not say. No note creates a new reading.
Sources are public records in this repo:

| Rule(s) | Bright line in the note | Recorded source |
|---|---|---|
| GBR-BT-02 | "free" is judged wherever the word and the deposit condition sit on the page; "risk-free" is a risk claim, not a free item | `evals/provenance/PAGE_BRIEFS.md` P11 boundary decision; July miss Pattern 3 and Pattern 4 |
| GBR-PC-02 | plain validity or expiry statements are not urgency; urgency on a non-gambling element is not covered | PAGE_BRIEFS P09 distractor; July miss Pattern 5 |
| GBR-PC-01, MLT-PC-01, DEU-PC-02 | "risk-free" and "lose nothing" are covered even when backed by a refund; factual refund terms and slogans that promise no outcome are not | PAGE_BRIEFS P06, P11 (violations and distractor); `evals/ADJUDICATION_LOG.md` D3 |
| GBR-BT-01, MLT-BT-01 | the offer's heading is part of the offer block; a term only behind a link is not shown; an odds boost is not a bonus offer | PAGE_BRIEFS P06 boundary decision; P09 brief (terms in the offer headline); v1.0 key p03 (boost without terms is COMPLIANT) |
| MLT-BT-02, MLT-BT-03 | presence rules: a term only behind a link counts as not stated; a no-deposit offer is not deposit-linked; an odds boost is not a bonus offer | ADJUDICATION_LOG D4, D5, D1; v1.0 key p03 |
| DEU-RG-02 | deposit-based play means any real-money product or operator promotion, with or without a bonus | ADJUDICATION_LOG D7 |
| GBR-RG-02 | an offer is a promotional incentive; operator or game links alone are not an offer | ADJUDICATION_LOG D2 |

The notes are general. None names a page, a brand or a test case.

## Proposed rule_text, exact strings

The note text follows the original sentence after one space.

**GBR-BT-01**
> Significant bonus terms (wagering, minimum deposit, expiry) must appear together with the headline offer, not only behind a link. Interpretation (v1.1): "together with the headline offer" means in the same offer block, and the offer's own heading counts as part of that block. A term that is available only behind a link counts as not shown. Here a bonus offer is a bonus, free bet, free spins or cashback offer; an odds boost is not a bonus offer for this rule.

**GBR-BT-02**
> An offer must not be described as free if claiming it requires a deposit or spend. Interpretation (v1.1): this covers any offer the page calls free (for example free spins or a free bet), wherever the word "free" and the deposit or spend condition appear on the page, including in headings, lists or separate sections. A game feature, such as a free-spins round inside a slot, is not an offer. "Risk-free" or "no-risk" wording describes risk, not a free offer; it is judged under GBR-PC-01, not under this rule.

**GBR-PC-01**, **MLT-PC-01**, **DEU-PC-02** (same text in all three)
> No claims of guaranteed winnings or risk-free gambling in any wording. Interpretation (v1.1): this covers any claim that the player will win or profit for certain, or cannot lose (for example "guaranteed profit", "risk-free", "lose nothing"), including when the claim is backed by a refund or cashback. A factual statement of refund or cashback terms that does not claim the player cannot lose is not covered, and neither is a slogan that promises no outcome.

**GBR-PC-02**
> Gambling offers must not use urgency pressure such as countdowns, last-chance, or ends-soon wording. Interpretation (v1.1): urgency pressure is wording or a device that pushes the reader to act on a gambling offer now because time or availability is running out (for example a countdown, "last chance", "ends soon", "today only", "only 10 left"). A plain statement of an offer's validity period, or a calm reminder that an unused offer will expire, is not urgency pressure. Urgency wording that applies only to a non-gambling element, such as a newsletter sign-up, is not covered.

**GBR-RG-02**
> Pages promoting a gambling offer must carry a safer-gambling tagline. Interpretation (v1.1): for this rule, an offer is a bonus, free bet, odds boost, cashback or other promotional incentive. A page that only lists or links to operators or games, with no such incentive, promotes no offer, so this rule is NOT_APPLICABLE there.

**MLT-BT-01**
> Where a bonus offer is presented, its wagering requirement must be stated in the same section as the offer, not only behind a link. Interpretation (v1.1): the offer's heading and its small print in the same section both count as the same section. Here a bonus offer is a bonus, free bet, free spins or cashback offer; an odds boost is not a bonus offer for this rule.

**MLT-BT-02**
> Every bonus offer must state its expiry or validity period. Interpretation (v1.1): the term must be stated on the page itself; a term available only behind a link counts as not stated. Each bonus offer on the page is checked, and one bonus offer without the term is a violation. Here a bonus offer is a bonus, free bet, free spins or cashback offer; an odds boost is not a bonus offer for this rule.

**MLT-BT-03**
> Every deposit-linked bonus offer must state the minimum qualifying deposit. Interpretation (v1.1): the term must be stated on the page itself; a term available only behind a link counts as not stated. An offer that needs no deposit is not deposit-linked; if the page has no deposit-linked offer, this rule is NOT_APPLICABLE.

**DEU-RG-02**
> Pages promoting deposit-based play must reference the cross-operator monthly deposit limit. Interpretation (v1.1): promoting deposit-based play means promoting a named operator, a specific real-money gambling product (for example a casino game, live casino or a sportsbook) or an offer, with or without a bonus. General betting content that names no operator, product or offer is not covered.

The other 13 rules keep their v1.0 text and only change `ruleset_version`
to `v1.1`.

## July key check: no v1.0 key cell changes under v1.1

Every July cell of a changed rule, for the pages that target its market
(V = VIOLATION, C = COMPLIANT, N = NOT_APPLICABLE), from
`evals/answer_key.yaml` v1.0:

| Rule | July cells | Consistent with the note |
|---|---|---|
| GBR-BT-02 | p01 V, p03 C, p04 N, p06 C, p08 N, p09 C, p10 V, p11 C, p12 C | yes: p01 and p10 have "free" plus a deposit condition (p01 in a heading); p03 needs no deposit; p06 and p11 say "risk-free", which the note sends to PC-01; p04 and p08 have no offer |
| GBR-PC-02 | p03 V, p09 V, all other GBR pages C | yes: p03 "ends soon" and p09 countdown are urgency; p10's expiry reminder and p09's newsletter line are not |
| GBR-PC-01 | p06 V, p08 V, p11 V, others C | yes: "risk-free" (p06), "guarantees long-term profit" (p08), "lose nothing" with refund (p11); p11's factual refund line and p01's slogan are not covered |
| MLT-PC-01 | p06 V, p08 V, p11 V, others C (incl. p05 slogan) | yes, as GBR-PC-01 |
| DEU-PC-02 | p06 V, p08 V, others C | yes, as GBR-PC-01 |
| GBR-BT-01 | p06 V, p04 N, p08 N, others C | yes: p06 offer A has min deposit and expiry only behind a link; p09 terms sit in the offer heading |
| MLT-BT-01 | p05 N, p07 N, p08 N, others C | yes: p06 offer A shows "35x wagering" in small print in the same section |
| MLT-BT-02 | p02 V, p06 V, no-bonus pages N, others C | yes: p02 one offer has no expiry; p06 offer A expiry only behind a link |
| MLT-BT-03 | p06 V, p03 N, no-bonus pages N, others C | yes: p06 min deposit only behind a link; p03 offer needs no deposit |
| DEU-RG-02 | p02 V, p07 V, p08 N, p03 C, p06 C | yes: p07 promotes live casino with no bonus (real-money product); p08 promotes no operator or product |
| GBR-RG-02 | p12 V, p04 N, p08 N, others C | yes: p04 links operators but has no incentive |

Cells red team 1 (RT1-05) named as made debatable by the first draft of
these notes, and why the revised wording keeps each one:

| Cell | v1.0 key | Why it does not change |
|---|---|---|
| p03 GBR-BT-01 | C | the "Odds Boost" carries no terms, but the note now says an odds boost is not a bonus offer for this rule; the free bet's terms sit with its headline |
| p03 MLT-BT-01, MLT-BT-02 | C, C | same: the odds boost is not a bonus offer for these rules; the free bet states "5x wagering, valid 14 days" in its section |
| p04 GBR-BT-02 | N | the note now covers offers only and says a free-spins round inside a slot is a game feature, not an offer; p04 has no offer |
| p08 DEU-RG-02 | N | the note now needs a named operator, a specific product or an offer; p08 is general betting content and names none |
| p12 GBR-BT-01, GBR-BT-02 | C, C | the two "profit boost" picks state wagering, minimum deposit and validity, and nothing is called free, so the verdict is the same whether or not they count as bonus offers |

Result: 0 of 288 v1.0 key cells would change. The v1.0 key stays the
key for the July development set. The table was checked against
`evals/answer_key.yaml` by red team 1 (all listed values match).

Known limit (RT1-20): some note examples are close to July wording (an
expiry reminder, urgency on a newsletter line, "lose nothing" backed by a
refund). July results after v1.1 are therefore regression evidence only,
not proof that the repair works. The gate is not affected, because July
is not gated.

## Risk the owner should weigh

These notes come from the same people and records that wrote the key.
They make the rules clearer to the checker, and they also move the
checker toward this key's own reading. That is acceptable for synthetic
rules (ADR-0003), but it is a real limit: a v2 PASS shows the system
applies these written rules, not that it reads ambiguous rules the way a
regulator would. The test-scope statement (eval-gate skill §9, written at
P5) must say so.

## Signature

After signature, P2 writes the exact strings above into the three rule
files and records their SHA-256 in `evals/eval_config.yaml`
(`datasets.ruleset_sha256`, RT1-13). The holdout key is labelled against
that signed text.
