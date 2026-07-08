# PAGE_AUTHOR_PROMPT — reconstructed provenance record

*Source: `evals/INJECTION_SPEC.md`, as committed together with the
resulting pages in `3124c1e` (Phase 1b-i, 2026-07-08). No separate
chat-transcript artifact recording the literal session prompt was ever
committed to this repo — INJECTION_SPEC.md's own header states that the
document itself *is* the page-construction brief for the page author
(Claude Code): "This document is the page-construction brief for the
page author (Claude Code)." What follows is that binding instruction,
extracted verbatim (not paraphrased) from the parts of INJECTION_SPEC.md
that apply across all 12 pages, so the page author's operating contract
is legible without re-reading the full spec. Per-page briefs are the
companion file, `evals/provenance/PAGE_BRIEFS.md`.*

---

## Document framing (verbatim, INJECTION_SPEC.md header)

> Authored by the spec author (three-actor protocol, ADR-0004 pending).
> This document is the page-construction brief for the page author
> (Claude Code). It contains the injected violations verbatim — it is
> therefore proto-answer-key material. The blind labeler (ChatGPT) must
> NEVER see this file; it receives only the finished pages + the three
> rule sets.

## Three-actor protocol (verbatim)

> 1. Spec author (strongest model): rule sets + this spec, incl. expected verdicts.
> 2. Page author (Claude Code): materializes pages from briefs below. May read
>    this spec (it must, to build pages) — its independence is not claimed.
> 3. Blind labeler (ChatGPT): given ONLY pages + rule sets + applicability
>    semantics, labels every (page × jurisdiction × rule) cell.
> 4. Adjudicator (Kristian): diffs spec key vs blind labels; agreements freeze
>    into answer_key.yaml; disagreements adjudicated case-by-case and logged.
> The committed answer key is therefore authored by no single model.

## Applicability semantics — binding for key derivation, blind labeler, and checkers (verbatim)

> - Every page declares target markets in a footer line: `Markets: MLT, GBR`.
> - Geo N/A: if jurisdiction J is not in the page's targets, ALL J rules are
>   NOT_APPLICABLE for that page.
> - Rule-level N/A: a rule is NOT_APPLICABLE when the content it governs is
>   absent (no bonus on page → bonus-terms rules N/A; no odds boost → DEU-BT-02
>   N/A; no operators/offers promoted → licence-line rules N/A; no deposit-based
>   play promoted → DEU-RG-02 N/A). Each brief lists its rule-level N/As —
>   the list is exhaustive, no judgment calls left open.
> - Everything else: VIOLATION if listed below, otherwise COMPLIANT.

## Page construction rules — binding for the page author (verbatim)

> - Static HTML, one file per page: evals/dataset/pages/p01.html … p12.html.
> - Realistic look: title, nav placeholder, sections, footer. 150–400 words.
> - Injected violation strings must appear VERBATIM as specified.
> - Distractor strings must appear VERBATIM as specified.
> - "Compliant furniture" = the standard block satisfying RG/licence/terms rules
>   for the page's targets, EXCEPT where a brief explicitly removes an element.
>   Standard furniture strings:
>   - RG notice: "Please gamble responsibly." · Age: "18+" ·
>     Help: "Help available at GambleSupport.example" ·
>     GBR tagline: "Take time to think." ·
>     Licences: "Licensed by the MLT Gaming Authority (MGA/EX/001/2026)" /
>     "Licensed by the GBR Gambling Commission (GC-EX-2026)" /
>     "Licensed under the DEU State Treaty (DE-EX-2026)" ·
>     DEU deposit limit: "A cross-operator monthly deposit limit of €1,000 applies."

## What the page author was NOT given

Per the protocol above, the page author (Claude Code) *did* have access
to the full INJECTION_SPEC.md, including expected verdicts per brief —
its independence from that document is explicitly not claimed (point 2).
The isolation this protocol relies on is downstream of page authorship:
the blind labeler (ChatGPT, step 3) never saw this document, only the
finished pages, the rule sets, and the applicability semantics quoted
above. See ADR-0004 for the resulting named residual (page author, spec
author, and this system's checkers are all Claude family; the one
cross-family seam is the blind labeler checking the key, not checking
checker behavior).
