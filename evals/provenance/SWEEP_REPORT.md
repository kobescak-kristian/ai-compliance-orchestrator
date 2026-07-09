# SWEEP_REPORT — pre-blind filler sweep, reconstructed provenance record

*Sources: `evals/ADJUDICATION_LOG.md` §"Pre-blind filler sweep" (quoted
verbatim below) and `git show fa5d6a1` (the actual fix, quoted below).
No sweep script was committed to this repo — the sweep was a manual grep
run in a prior session, before the blind-label pass began; its record
is exactly what `evals/ADJUDICATION_LOG.md` logged, no more.*

## Historical run (pre-blind, 2026-07-08)

Exactly as originally recorded — nothing below this heading has been
edited for the live-sweep addition; see "Live sweep" at the end of this
file for what changed 2026-07-09.

## What the sweep was for

Before the 12 finished pages were sent to the blind labeler (ChatGPT),
the pages needed a check independent of the per-page briefs: did any
page-author-added "filler" content (furniture, connective text, invented
secondary offers not specified in a brief) accidentally trigger a rule
the brief didn't intend — i.e. an unlogged, uncounted violation that
would corrupt the blind-label pass by testing content nobody had
adjudicated.

## Keyword set (verbatim from evals/ADJUDICATION_LOG.md)

> a keyword grep across all 12 pages (`guarant|risk-free|lose nothing|free|last chance|ends soon|...`)

**Note on completeness:** the committed log entry itself ends this
pattern with `|...` — a trailing ellipsis in the original record, not
introduced here. The full literal grep pattern actually run is not
preserved beyond this partial/representative list; no sweep script was
committed alongside `3124c1e` or `fa5d6a1` to recover it from. This
report reproduces the keyword set exactly as logged rather than
inventing the missing terms — `guarant`, `risk-free`, `lose nothing`,
`free`, `last chance`, `ends soon` are the six terms on record, and the
pattern is known to have covered additional unlogged terms.

## The one collision it caught (verbatim from evals/ADJUDICATION_LOG.md)

> caught one unintended trigger: P12's invented "Second-Chance Bet"
> filler offer combined a "free bet" claim with an adjacent deposit
> requirement — structurally identical to the P01/P10 GBR-BT-02 pattern,
> but not part of any brief and not counted in the spec author's
> violation total.

P12's brief (`evals/provenance/PAGE_BRIEFS.md`) specifies two sports
bonuses and an absent RG block as its only violations (GBR-RG-01,
GBR-RG-02). The page author added a second offer, "Second-Chance Bet,"
as filler beyond what the brief required — and that filler happened to
reproduce the exact free/deposit pattern that GBR-BT-02 governs
elsewhere in the dataset (P01, P10), which the sweep caught before it
could silently inflate P12's true violation count beyond what was
briefed and logged.

## The fix (git show fa5d6a1, evals/dataset/pages/p12.html)

Reworded the filler offer to remove the free/deposit collision entirely,
before the blind pass began, so the blind labeler never saw the defect:

```diff
   <section class="offer">
-    <h2>2. Second-Chance Bet</h2>
-    <p>Get your stake back as a free bet if your first weekend selection loses,
+    <h2>2. Weekend Accumulator Boost</h2>
+    <p>50% profit boost on your first weekend accumulator — 5x wagering,
     minimum deposit £10, valid 7 days.</p>
   </section>
```

Commit: `fa5d6a10c985e94262ab9161068a5dc60c6f12a5` — "P12: remove
unintended free-bet/deposit collision in filler; SPEC: record §10.7
resolution + 1b progress." Same commit also resolved SPEC.md §10.7 (the
three-actor authorship split) from OPEN to RESOLVED — the sweep and the
authorship-protocol resolution landed together, prior session.

## Why this belongs in the provenance record

The sweep is the one point in the pipeline where a defect was caught and
fixed *before* it reached the blind labeler, rather than being caught by
adjudication *after*. Without this record, "P12: fixed a collision"
would be a bare commit message with no trace of what was checked, what
was found, or why it mattered to the protocol's isolation guarantee
(ADR-0004) — that the blind labeler only ever sees pages that reflect
their briefs, not accidental extras.

## Live sweep (from this commit)

The historical run above was a one-off manual grep with an unrecoverable
partial keyword list. As of 2026-07-09, the sweep is a permanent,
committed test:

- **Full pattern committed as code:** `tests/test_sweep.py::
  SWEEP_PATTERN` — `guarant|risk[- ]?free|lose nothing|free|last
  chance|ends (soon|in)|hurry|countdown|income|get rich|can'?t
  lose|no risk`, case-insensitive. This supersedes the historical run's
  6-term partial list; nothing is unrecoverable going forward.
- **Provenance is the test file itself.** Every future page edit is
  re-checked automatically by `python -m pytest tests/test_sweep.py`
  (or the full suite) — there is no separate script to remember to run
  and no manual grep to repeat.
- **Residuals adjudicated into `evals/provenance/SWEEP_ALLOWLIST.md`,
  count 8.** Running the full pattern against HEAD (2026-07-09) surfaced
  8 hits outside `evals/check_pages.py`'s spec-string lists — titles,
  nav text, and elaboration prose on p03/p04/p10, none a new rule
  surface (hard-checked against the frozen key, none plausibly flip a
  cell). Per Kristian's ruling, these were adjudicated into a separate
  allowlist rather than folded into `PAGE_SPECS` — spec strings stay
  exactly what was specified at page-construction time. The allowlist
  carries its own staleness guard: an entry whose text stops matching
  its page fails the test rather than silently going unused.
