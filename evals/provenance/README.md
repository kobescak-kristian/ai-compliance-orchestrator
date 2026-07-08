# evals/provenance/

Provenance gate for the Phase 1b eval dataset (standing decision,
recorded 2026-07-09 as part of Phase 4 completion — blocks Phase 5).
ADR-0004 names the three-actor protocol that produced the frozen answer
key; this folder is the reconstructed record of what the **page author**
(Claude Code, commit `3124c1e`) actually worked from, plus the filler
sweep that ran before the blind-label pass.

Everything here is reconstructed from already-committed record — no new
information is introduced, nothing is approximated. Sources, per file:

- **PAGE_BRIEFS.md** — the 12 per-page construction briefs, quoted
  verbatim from `evals/INJECTION_SPEC.md`'s "Page briefs" section as
  committed in `3124c1e`.
- **PAGE_AUTHOR_PROMPT.md** — the binding instruction the page author
  worked under. `evals/INJECTION_SPEC.md` states in its own header that
  it *is* "the page-construction brief for the page author (Claude
  Code)" — there is no separate chat-transcript artifact recording a
  distinct prompt; the committed document is the instruction. This file
  extracts the binding, non-per-page parts of that instruction (the
  three-actor protocol, applicability semantics, and page construction
  rules) so the page-author's operating contract is legible on its own,
  without re-deriving it from the full spec.
- **SWEEP_REPORT.md** — the pre-blind filler sweep, reconstructed from
  `evals/ADJUDICATION_LOG.md`'s "Pre-blind filler sweep" section (the
  keyword set as logged, the one P12 collision it caught) plus the
  actual fix, `git show fa5d6a1`, quoted directly.

No source material required approximation for this folder — the keyword
list quoted in SWEEP_REPORT.md is reproduced exactly as logged, including
the trailing ellipsis in the original record (see that file's note).
