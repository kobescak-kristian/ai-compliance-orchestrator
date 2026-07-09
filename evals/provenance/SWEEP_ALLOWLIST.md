# SWEEP_ALLOWLIST — adjudicated residual sweep hits

*Adjudicated 2026-07-09 (Kristian, via session ruling); these residuals
predate the blind pass — the labeler saw the pages as-is, so the frozen
key already reflects them.*

`tests/test_sweep.py`'s trigger pattern (`evals/provenance/SWEEP_REPORT.md`
"Live sweep") caught 8 hits on p03/p04/p10 that fall outside
`evals/check_pages.py`'s `PAGE_SPECS["strings"]` — titles, nav text, and
elaboration prose never enumerated there, because that list was only ever
built to verify a brief's *required* elements are present, not to
inventory every word on the page. Per Kristian's ruling: these are
resolved as an **adjudicated allowlist**, not by extending `PAGE_SPECS` —
spec strings stay exactly what was specified at page-construction time
(`evals/provenance/PAGE_BRIEFS.md`); post-hoc residuals are a separate,
human-adjudicated category, kept here so the distinction stays visible
instead of being absorbed into the construction record.

**Hard check performed for all 8 entries:** does this hit plausibly flip
a frozen answer-key cell's verdict (`evals/answer_key.yaml`)? For every
entry below, no — each is either elaboration of the *same* offer whose
cell is already adjudicated, or content on a page/rule pair that's
already `NOT_APPLICABLE` with no bonus-terms surface for the keyword to
touch. None met the bar for "STOP and report alone."

## Entries

### 1. p03.html — page title
- Matched text: `Free` (within `Free Bet + Boosted Odds — ProLine Sports`, the `<title>`)
- Rule surface: GBR-BT-02 (free-item-requiring-deposit pattern)
- Frozen key cell: p03 × GBR-BT-02 = **COMPLIANT**
- Rationale: the title echoes the page's own single, already-specified,
  already-adjudicated compliant free-bet offer ("€50 Free Bet — no
  deposit needed" — genuinely no deposit, per `PAGE_BRIEFS.md`'s P03
  distractor). No second offer, no new rule surface.

### 2. p04.html — body prose
- Matched text: `free` (within "...96.1% RTP with a free-spins round triggered by three or more scatter symbols...")
- Rule surface: bonus-terms category (all BT rules)
- Frozen key cells: p04 × MLT-BT-01/02/03, GBR-BT-01, GBR-BT-02 = all **NOT_APPLICABLE**
- Rationale: "free-spins round" is an in-game slot mechanic (an RTP
  feature description), not a bonus offer. P04 has no bonus offers per
  its brief; every BT cell is already N/A for lack of any bonus-terms
  surface — there is nothing here for the keyword to touch.

### 3. p10.html — page title
- Matched text: `Free` (within `Free Bet Offer — BetSense Affiliates`, the `<title>`)
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: names the page's own single, already-specified,
  already-adjudicated free-bet-requiring-deposit offer. No second offer.

### 4. p10.html — nav
- Matched text: `Free` (within `Home | Free Bets | Sports | Reviews`, the `<nav>`)
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: nav label for the site's free-bets section, not a distinct
  offer instance — same single offer already adjudicated.

### 5. p10.html — body prose
- Matched text: `free` (within "...Register, deposit, and your free bet token lands in your account automatically within a few minutes.")
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: elaboration of the same specified offer's mechanics
  (deposit unlocks a token) — not a second offer, no new claim.

### 6. p10.html — body prose
- Matched text: `Free` (within "Free bet stakes are not returned with winnings, and winnings from the free bet are paid as cash, ready to withdraw...")
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: standard free-bet-stake-not-returned disclosure for the
  same offer; no new offer or claim.

### 7. p10.html — body prose (same sentence as #6, second occurrence)
- Matched text: `free` (within "...and winnings from the free bet are paid as cash, ready to withdraw or use to place another bet.")
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: same sentence, same offer, same rationale as #6 — logged
  separately because it is a distinct pattern match, not distinct content.

### 8. p10.html — body prose
- Matched text: `free` (within "The free bet token can be used on any sport listed in our A-Z index, and it expires automatically if unused within the stated period...")
- Rule surface: GBR-BT-02
- Frozen key cell: p10 × GBR-BT-02 = **VIOLATION**
- Rationale: usage-terms elaboration of the same specified offer; no new
  offer or claim.

## Machine-readable index (consumed by tests/test_sweep.py)

Matched by `(page, text)` — substring containment against the page's
extracted visible text, not by offset (offsets rot as pages change).
`tests/test_sweep.py` also asserts every entry's `text` still occurs on
its `page` (stale-allowlist guard): an entry that stops matching fails
the test rather than silently going unused.

```yaml
entries:
  - page: p03.html
    text: "Free Bet + Boosted Odds"
  - page: p04.html
    text: "free-spins round"
  - page: p10.html
    text: "Free Bet Offer"
  - page: p10.html
    text: "Home | Free Bets | Sports | Reviews"
  - page: p10.html
    text: "your free bet token lands in your account automatically"
  - page: p10.html
    text: "Free bet stakes are not returned with winnings"
  - page: p10.html
    text: "winnings from the free bet are paid as cash"
  - page: p10.html
    text: "The free bet token can be used on any sport listed in our A-Z index"
```
