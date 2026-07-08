# INJECTION_SPEC — eval dataset pages (Phase 1b)
*v1.0 — 2026-07-07. Authored by the spec author (three-actor protocol, ADR-0004
pending). This document is the page-construction brief for the page author
(Claude Code). It contains the injected violations verbatim — it is therefore
proto-answer-key material. The blind labeler (ChatGPT) must NEVER see this
file; it receives only the finished pages + the three rule sets.*

**Amendment to BLUEPRINT §7:** injection math totals **28 violations** across
12 pages (spec said ~25; estimate superseded by this spec).

## Three-actor protocol (methodology, goes into EVAL_RESULTS.md later)
1. Spec author (strongest model): rule sets + this spec, incl. expected verdicts.
2. Page author (Claude Code): materializes pages from briefs below. May read
   this spec (it must, to build pages) — its independence is not claimed.
3. Blind labeler (ChatGPT): given ONLY pages + rule sets + applicability
   semantics, labels every (page × jurisdiction × rule) cell.
4. Adjudicator (Kristian): diffs spec key vs blind labels; agreements freeze
   into answer_key.yaml; disagreements adjudicated case-by-case and logged.
The committed answer key is therefore authored by no single model.

## Applicability semantics (binding for key derivation, blind labeler, and checkers)
- Every page declares target markets in a footer line: `Markets: MLT, GBR`.
- Geo N/A: if jurisdiction J is not in the page's targets, ALL J rules are
  NOT_APPLICABLE for that page.
- Rule-level N/A: a rule is NOT_APPLICABLE when the content it governs is
  absent (no bonus on page → bonus-terms rules N/A; no odds boost → DEU-BT-02
  N/A; no operators/offers promoted → licence-line rules N/A; no deposit-based
  play promoted → DEU-RG-02 N/A). Each brief lists its rule-level N/As —
  the list is exhaustive, no judgment calls left open.
- Everything else: VIOLATION if listed below, otherwise COMPLIANT.

## Page construction rules (binding for the page author)
- Static HTML, one file per page: evals/dataset/pages/p01.html … p12.html.
- Realistic look: title, nav placeholder, sections, footer. 150–400 words.
- Injected violation strings must appear VERBATIM as specified.
- Distractor strings must appear VERBATIM as specified.
- "Compliant furniture" = the standard block satisfying RG/licence/terms rules
  for the page's targets, EXCEPT where a brief explicitly removes an element.
  Standard furniture strings:
  - RG notice: "Please gamble responsibly." · Age: "18+" ·
    Help: "Help available at GambleSupport.example" ·
    GBR tagline: "Take time to think." ·
    Licences: "Licensed by the MLT Gaming Authority (MGA/EX/001/2026)" /
    "Licensed by the GBR Gambling Commission (GC-EX-2026)" /
    "Licensed under the DEU State Treaty (DE-EX-2026)" ·
    DEU deposit limit: "A cross-operator monthly deposit limit of €1,000 applies."

## Page briefs

### P01 — operator casino welcome promo · Markets: MLT, GBR
Casino welcome offer: "100% up to €200 + 50 Free Spins". Wagering "35x wagering
applies" adjacent, "Minimum deposit €20", "Offer valid for 30 days" — all in the
offer section. Full furniture for MLT+GBR EXCEPT: GBR licence line ABSENT.
- VIOLATIONS: GBR-GE-01 (missing GBR licence line); GBR-BT-02 ("50 Free Spins"
  granted only after deposit — page states "Spins credited after first deposit").
- Distractor: "Your winnings, your way." (not a guarantee claim)
- Rule-level N/A: DEU-* all (geo).

### P02 — affiliate casino bonus roundup · Markets: MLT, DEU
Three casino bonuses with wagering+min-deposit stated. Expiry stated on offers
1 and 3; offer 2 has NO expiry ("100% up to €150, 30x wagering, min €10" — no
validity period anywhere). Furniture: MLT full; DEU licence line ABSENT; DEU
deposit-limit line ABSENT.
- VIOLATIONS: DEU-PC-01 (casino bonuses promoted to DEU); MLT-BT-02 (offer 2 no
  expiry); DEU-GE-01; DEU-RG-02.
- Distractor: "Top-rated by players." (puffery)
- Rule-level N/A: none beyond geo (GBR geo N/A).

### P03 — operator sportsbook promo · Markets: MLT, GBR, DEU
Sports free bet: "€50 Free Bet — no deposit needed" (genuinely no deposit).
"5x wagering, valid 14 days, min deposit not required." Odds boost section:
"Boosted odds 3.50 on tonight's match!" with NO base odds shown. Banner:
"Offer ends soon!". Full furniture all three markets incl. DEU deposit limit.
- VIOLATIONS: DEU-BT-02 (no base odds); GBR-PC-02 ("Offer ends soon!").
  NOTE MLT divergence: no urgency rule in MLT → MLT COMPLIANT on same text.
- Distractors: "€50 Free Bet — no deposit needed" (free is true → GBR-BT-02
  compliant); "Bet on 200+ markets" (count claim, benign).
- Rule-level N/A: DEU-PC-01 (no casino content), DEU-PC-03 (no live casino).

### P04 — affiliate slots review · Markets: GBR
Review of "Pixel Quest Slots" with cartoon mascot: "Zappy the Wizard — a
favourite with students and streamers alike!". Operators listed with play
links. RG notice + 18+ present; help resource ABSENT; GBR licence line present.
No bonus offers on page.
- VIOLATIONS: GBR-PC-03 (youth-appeal wording); GBR-RG-01 (help resource
  missing — rule requires all three elements).
- Distractor: "Colourful graphics the whole community enjoys." (benign)
- Rule-level N/A: GBR-BT-01/02 (no offers), GBR-RG-02 (no offer promoted),
  MLT-*/DEU-* (geo).

### P05 — operator generic homepage · Markets: MLT
Brand homepage, games catalogue teaser, no bonuses. Full MLT furniture.
Tagline: "Big games, every day."
- VIOLATIONS: none. Fully compliant page (tests false-positive discipline).
- Distractor: "Big games, every day." — factual/descriptive, NOT a guarantee;
  expected COMPLIANT under MLT-PC-01.
- Rule-level N/A: MLT-BT-01/02/03 (no bonuses); GBR/DEU geo.
- **D3 amendment (adjudication, 2026-07-08):** original tagline "Play and
  win big every day!" was flagged a deliberate adjudication candidate
  (ambiguous under MLT-PC-01's guaranteed-winnings prohibition). Adjudicator
  ruling: reword to an inert string rather than resolve the ambiguity by
  fiat — the page-level VIOLATIONS list and rule-level N/As are unchanged;
  see evals/ADJUDICATION_LOG.md D3.

### P06 — affiliate best-bonuses comparison · Markets: MLT, GBR, DEU
Comparison table: casino + sports bonuses. Headline offer A: "200% up to €300
— see terms" with terms ONLY behind link (nothing adjacent); wagering for offer
A stated in linked page only. Offer B: "Risk-free first bet — refund if you
lose". Other offers carry full adjacent terms. Full furniture all markets.
- VIOLATIONS: DEU-PC-01 (casino bonuses to DEU); GBR-BT-01 (offer A: min
  deposit + expiry only behind link); MLT-PC-01 + GBR-PC-01 + DEU-PC-02
  ("Risk-free first bet").
  Boundary decision (final): offer A carries "35x wagering" adjacent in small
  print; only min-deposit and expiry sit behind the link. Therefore MLT-BT-01
  (wagering-adjacency only) is COMPLIANT while GBR-BT-01 (composite: all
  significant terms adjacent) is VIOLATED. Page author: include "35x
  wagering" adjacent to offer A.
- Distractor: "Our editors' pick." (benign)
- Rule-level N/A: DEU-PC-03 (no live casino).

### P07 — operator live-casino page · Markets: MLT, DEU
Live-dealer lobby promo: "Join our Live Roulette and Blackjack tables with real
dealers, streamed 24/7." No bonuses. MLT furniture full; DEU licence line
ABSENT; DEU deposit-limit line ABSENT.
- VIOLATIONS: DEU-PC-03 (live casino to DEU); DEU-GE-01; DEU-RG-02.
- Distractor: "Real dealers, real time." (benign)
- Rule-level N/A: all BT rules (no bonuses); GBR geo.

### P08 — affiliate betting strategy guide · Markets: MLT, GBR, DEU
Educational article, no operators promoted, no offers. Contains: "Following
this staking plan guarantees long-term profit." and "Turn betting into your
side income.". RG furniture full for all three (notice, 18+, help).
- VIOLATIONS: MLT-PC-01 + GBR-PC-01 + DEU-PC-02 (guarantee sentence);
  MLT-PC-02 ("side income" — MLT-only rule → three-way divergence case).
- Distractor: "Improve your understanding of the odds." (benign skill language)
- Rule-level N/A: all BT rules, all GE rules (no operators/offers), DEU-RG-02
  (no deposit-based play promoted), GBR-RG-02 (no offer promoted).

### P09 — operator reload promo with countdown · Markets: GBR, MLT
Reload bonus "50% up to €100, 20x wagering, min deposit €10, valid 7 days" —
all adjacent. Banner: "Last chance — bonus ends in 02:14:33!". Full furniture
both markets.
- VIOLATIONS: GBR-PC-02 (countdown/last-chance). MLT divergence: COMPLIANT.
- Distractor: "Don't miss our newsletter — sign up today." (urgency on
  non-gambling element → not GBR-PC-02)
- Rule-level N/A: DEU geo.

### P10 — affiliate free-bet page · Markets: GBR
"Claim your FREE £10 bet" — page states "Minimum deposit £10 required to
unlock." Terms adjacent (wagering 1x, min deposit £10, valid 7 days). Full GBR
furniture incl. tagline.
- VIOLATIONS: GBR-BT-02 ("FREE" requiring deposit).
- Distractor: "No promo code needed." (benign)
- Rule-level N/A: MLT/DEU geo.

### P11 — operator cashback week · Markets: MLT, GBR
"Risk-Free Week: play casino all week, lose nothing — we refund net losses up
to €50." Terms adjacent (min deposit €20, refund as cash, 7 days). Full
furniture both markets.
- VIOLATIONS: MLT-PC-01 + GBR-PC-01 ("Risk-Free" / "lose nothing").
- Distractor: "Refund paid as withdrawable cash." (benign factual term)
- Rule-level N/A: DEU geo.
  Boundary decision (final): GBR-BT-02 governs items described as "free";
  "Risk-Free" is a risk claim, not a free-item claim → GBR-BT-02 is COMPLIANT
  (applicable, not violated). Page author: no change needed.
- Expected blind-label divergence: PC vs BT boundary here is deliberate.

### P12 — affiliate weekend bonus picks · Markets: GBR
Two sports bonuses, full adjacent terms, GBR licence line present. RG block
ENTIRELY ABSENT: no notice, no 18+, no help resource, no tagline.
- VIOLATIONS: GBR-RG-01 (all three elements missing); GBR-RG-02 (no tagline).
- Distractor: "Terms apply — see full T&Cs." (benign, terms ARE adjacent)
- Rule-level N/A: MLT/DEU geo.

## Injection totals
Violations: P01:2 P02:4 P03:2 P04:2 P05:0 P06:5 P07:3 P08:4 P09:1 P10:1
P11:2 P12:2 = **28**. Severity mix: 12 CRITICAL, 13 MAJOR, 3 MINOR.
Divergence cases (same text, different verdicts by jurisdiction): P03, P08,
P09. Zero-violation page: P05. Deliberate adjudication candidates: P05
tagline, P11 GBR-BT-02 boundary.
