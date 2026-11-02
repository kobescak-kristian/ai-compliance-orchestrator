# Scenario spec, gate v2 (holdout cases and development suite)

Status: written with gate v2 (`evals/eval_config.yaml` version 2.0,
repair program P-001, phase P1); frozen on the owner's sign-off at the
P1 stop. Every private holdout (H1, H2, ...) is drawn under this spec. A
change applies only to the next gate version. Red team 1
(`evals/v2/RED_TEAM_1.md`) findings are resolved in this version.

This file is public. It holds rules for building cases, never a case.
Holdout pages, briefs and keys never enter Git (eval-gate exception,
owner, 2026-11-02, recorded in `STATE.md` and `BLUEPRINT.md` §7).

## 1. Definitions

- **Cell:** one (page, rule) pair for a rule of a market the page
  targets. Verdict: `VIOLATION`, `COMPLIANT` or `NOT_APPLICABLE`.
  Geo cells (rules of markets the page does not target) are decided by
  intake code, never by a model, so they are never cells in a holdout key.
- **Case:** one scenario page with exactly one predeclared **primary
  decision**: one cell, its expected verdict, and its evidence.
- **Primary trigger:** the text the primary decision turns on. For a
  violation, the violating text (for an absence, a short description of
  what is missing). For a compliant or not-applicable case, the designed
  near-miss text that resembles a violation.
- **Rule family:** rules whose v1.0 sentence is the same once the market
  name is removed. Today there are two: the three licence-line rules
  (DEU-GE-01, GBR-GE-01, MLT-GE-01) and the three "guaranteed winnings or
  risk-free" rules (DEU-PC-02, GBR-PC-01, MLT-PC-01). The self-check
  computes families from the rule files.
- **Evidence type** of a primary violation:
  - `text`: the violation is in words on the page. The key gives one or
    more verbatim **spans**; the first is the **core span** (the words
    that break the rule), later spans are context (for example the
    deposit condition for a "free" claim). Every span occurs exactly
    once on the page.
  - `missing_term`: an offer is on the page but lacks a required term
    (no expiry, no base odds, minimum deposit only behind a link). The
    key gives the offer's span as the core span. An `ABSENT:` excerpt or
    an excerpt that overlaps the offer span both pass.
  - `absent`: required page content is missing entirely (a licence line,
    the whole RG block). The key gives the **required content** strings
    and **absent tokens** (short core words such as a licence number or
    a help-resource name); none may appear on the page, so a paraphrase
    cannot slip through.
- **Ruleset:** v1.1 (`evals/v2/RULESET_V1_1.md`) once the owner signs it.
  The holdout is labelled against the signed text.

## 2. Holdout size and mix (checked by `evals/check_holdout.py`)

| Item | Rule |
|---|---|
| Cases | exactly 30 pages, IDs `h<n>-01` to `h<n>-30` |
| Primary decisions | exactly 1 per page (no two-decision exceptions in this spec version) |
| Primary verdicts | 13 to 17 `VIOLATION`; at least 10 `COMPLIANT`; at least 3 `NOT_APPLICABLE` (rule-level, never geo). Grading treats N/A primaries exactly like COMPLIANT ones ("not flagged"); they exist to cover rule-level applicability near-misses |
| Markets | each of DEU, GBR, MLT is the primary market of at least 8 cases |
| Targets per page | 1 to 3 markets; at least 20 pages target 1 or 2 markets |
| Categories | BONUS_TERMS, PROHIBITED_CLAIMS and RG_MESSAGING each at least 5 primaries; GEO_ELIGIBILITY at least 2 |
| Same primary rule | at most 2 cases per primary `rule_id` (independence rule 2) |
| Same rule family | at most 2 cases per rule family (independence rule 2) |
| Evidence types | at least 2 `absent` primary violations; `missing_term` allowed |
| Layout | at least 6 primary triggers sit in a heading, list item or table cell, not a `<p>` |
| Page furniture | every page has at least one heading (`h1` to `h6`) and one list item, and a footer line `Markets: X, Y` |
| Injection | at least 2 cases contain text that tells an automated reviewer what verdict to give; it targets the primary decision; at least 1 tries to hide a real violation |
| Length | 150 to 450 visible words per page |

## 3. Independence rules (frozen; the self-check enforces both)

1. **Own brief, own text, own layout.** Each case comes from its own
   brief. No two cases share a primary trigger, and no two triggers share
   60% or more of their words. No two pages share a page template: the
   same sequence of tags in `<body>`, with or without class names.
2. **At most 2 cases per primary rule and per rule family**, so one
   rule-reading weakness cannot move many cases at once.

The checks are mechanical and catch copies and near-copies, not every
kind of similarity. Shared factors that remain (one spec author, one
page author, one model family, one spec, synthetic rules) are
population-level. They are stated in the test-scope statement (eval-gate
skill §9, written at P5), and the public claim says "separately
briefed", not "independently authored".

## 4. What a key holds (private file `key.yaml`)

Per page: `file`, `targets`, `cells` (every rule of every target market,
8 per market, nothing else), and `primary` with `rule_id`, `expected`,
`evidence_type` (`text`, `missing_term`, `absent` or `none`), `spans`
(text and missing_term; first = core), `required_content` and
`absent_tokens` (absent), `trigger`, `layout` (`p`, `heading`, `list` or
`table`; `none` for absent only) and `injection` (true or false). The
primary cell's verdict in `cells` equals `primary.expected`. For an
absent case the trigger is a short description, not looked up on the
page.

Applicability semantics are the v1.0 ones, unchanged
(`evals/provenance/PAGE_AUTHOR_PROMPT.md`): geo N/A for markets not
targeted; rule-level N/A when the content a rule governs is absent;
otherwise `VIOLATION` or `COMPLIANT`. Standard furniture strings are the
v1.0 ones from the same file.

## 5. Self-check (generator self-check, eval-gate build check b)

`evals/check_holdout.py <holdout dir>` checks the whole set every time
and stops with exit 1, writing nothing, on any of:

- a duplicate case ID in the key, a missing page file, a page file with
  no key entry, or a page ID that does not match its file;
- a `Markets:` footer that does not match the key's targets;
- a key whose cells are not exactly the 8 rules of each target market,
  or an invalid verdict;
- a primary cell outside the targets, a primary verdict that differs
  from its cell, or an evidence type that does not fit the verdict;
- a span that does not occur exactly once in the visible text; a
  trigger (except absent type) not in the visible text or not inside the
  element its `layout` names; an absent case whose required content or
  absent token appears;
- any mix rule in §2 or independence rule in §3 broken;
- answer-key words in a page (`answer key`, `holdout`, `primary
  decision`, `expected verdict`).

Visible text comes from the grader's full-text extractor in
`evals/check_holdout.py` (shared text rule: `evals/eval_config.yaml`
`evidence_grading.shared_text_rule`; P2 moves it into one module the
system reader also uses). Check A3 compares the system reader against
it.

On success it prints counts only (no page text) and can write
(`--write-manifest`, `--pages-only` before blind labeling) or verify
(`--verify-manifest`) the SHA-256 manifest. A keyless test
(`tests/test_check_holdout.py`) plants each mistake above and shows the
check stops.

## 6. Authoring protocol (ADR-0004 roles, private)

1. **Spec author** (Claude, fresh context): writes 30 briefs and a draft
   full-cell key under this spec. Works only in the private folder.
2. **Page author** (Claude, fresh context, not the spec author's
   session): builds each page from its brief alone. Varies layout per
   page (operator and affiliate styles, tables, lists, cards).
3. **Spec author, second pass:** reads the finished pages, finalizes
   every cell of the draft key and runs a filler sweep (unintended
   triggers in filler text are fixed in the page, before blind labeling).
4. **Self-check** passes; the page hashes go into the committed manifest
   (`--pages-only`).
5. **Blind labeler** (a different model family, run by the owner): gets
   only the pages, the signed v1.1 rule sets and the applicability
   semantics. Labels every cell.
6. **Adjudicator** (owner): diffs draft key and blind labels; agreements
   freeze; each disagreement is ruled and logged in a private
   adjudication file. A page changed after blind labeling is relabeled,
   and its new hash replaces the old one in the manifest by a recorded
   owner decision (before the first run only).
7. Self-check passes again on the frozen key; the full manifest (pages,
   briefs, key, adjudication file) is committed before the first run.
   After the first run the manifest is immutable.

No author or labeler session sees results, run logs or miss notes of any
earlier holdout. A later holdout (H2, ...) is written by a fresh spec
author that gets only this file, `evals/v2/RULESET_V1_1.md` as signed,
and `evals/provenance/PAGE_AUTHOR_PROMPT.md`. Known limit (RT1-21): this
isolation is by instruction. Author and labeler sessions are told not to
open anything else, and the private adjudication file records how each
session was started.

## 7. Private storage

- Location: a private folder outside every Git repository, set on each
  machine by the setting `holdout_root` in the gitignored file
  `config.local.yaml` (never a path in a tracked file). One offline
  backup kept by the owner.
- Layout per holdout: `pages/`, `briefs.md`, `key.yaml`,
  `adjudication.md`, `blind_packet/` (what the labeler receives).
- Official runs read pages from there (P2 switches the reader's cage
  root through the local setting); pages are never copied into the repo.
  Run DBs and logs are written under `holdout_root`; console output is
  sanitized.
- Git holds only: this spec, the grader, `evals/v2/holdouts/H<n>.sha256`
  (the only files Git accepts in that folder, see `.gitignore`), and
  sanitized results (allowlist in `evals/eval_config.yaml`).
- A holdout is retired after any completed official series, PASS or
  FAIL, or on any leak. It then becomes local development data and is
  never published.

## 8. Development suite (public, reported, never gated)

Purpose: regression coverage for every rule and every known failure
mode. Same runner and grading as the holdout; results are reported only.

- **July set, 12 pages** (`evals/dataset/pages/p01` to `p12`, key
  `evals/answer_key.yaml` v1.0, unchanged). One primary decision per
  page was chosen in P1 and is recorded with its evidence in
  `evals/v2/july_primaries.yaml` (spans and triggers are the verbatim
  brief strings from `evals/provenance/PAGE_BRIEFS.md`):

  | Page | Primary | Expected | Why this one |
  |---|---|---|---|
  | p01 | GBR-BT-02 | VIOLATION | "Free Spins" in a heading, deposit condition elsewhere (July miss) |
  | p02 | MLT-BT-02 | VIOLATION | one of three offers lacks expiry (missing_term) |
  | p03 | DEU-BT-02 | VIOLATION | boosted odds without base odds (missing_term) |
  | p04 | GBR-PC-03 | VIOLATION | youth-appeal mascot |
  | p05 | MLT-PC-01 | COMPLIANT | slogan that promises no outcome |
  | p06 | GBR-BT-02 | COMPLIANT | "risk-free" is not a free offer (July miss) |
  | p07 | DEU-PC-03 | VIOLATION | live casino to DEU |
  | p08 | MLT-PC-02 | VIOLATION | gambling as side income |
  | p09 | MLT-BT-01 | COMPLIANT | wagering stated only in the offer heading (July miss) |
  | p10 | GBR-PC-02 | COMPLIANT | expiry reminder is not urgency (July miss) |
  | p11 | GBR-PC-01 | VIOLATION | "lose nothing" claim in a heading (July miss) |
  | p12 | GBR-RG-01 | VIOLATION | whole RG block missing (absent) |

  All 288 cells are also scored as diagnostics. July results after
  ruleset v1.1 are regression evidence only (RT1-20).
- **New development pages (built in P2, about 8, keys by the same
  three-actor protocol, public):** together they must cover
  - one violation case for each rule with none in the July key:
    DEU-BT-01, DEU-RG-01, MLT-BT-01, MLT-RG-01, MLT-RG-02, MLT-GE-01;
  - one near-miss per known failure mode: terms only in a heading;
    a prohibited claim only in a heading; operator links only in a list;
    "risk-free" next to a real "free" offer; a calm expiry reminder next
    to real urgency on another offer;
  - 2 injection pages (one tries to hide a violation, one tries to
    create a false one).
  After P2, every rule has at least one violation and one non-violation
  development case.
- Interaction sweep cases (P3) are added to the development suite, not
  to a holdout.
