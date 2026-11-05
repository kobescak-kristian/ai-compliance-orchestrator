# STATE — ai-compliance-orchestrator
- STATUS: ACTIVE

**Classification:** PROJECT.

This file holds current status and open items. Change history is in Git. The
earlier log, including the sections older records cite (open loops, P2 entry,
development runs, change log), is at `git show 91105ca:STATE.md`.

## Current status (2026-11-05)

- **Repair program P-001:** at P5, publication of `repair/v2` (cut from `main` at
  `62f5935`, not merged). Until P5 closes, model runs, a push or merge of
  `repair/v2` and changes to other repositories each need separate authorization,
  and the close ritual in `CLAUDE.md` does not apply to this branch.
- **Official result:** gate v2.1 **PASS**, series `H2-2026-11-05-a7871a` at
  `91105ca`, runner exit 0, 29 of 30 synthetic compliance scenarios. Record:
  `evals/EVAL_RESULTS.md`, `evals/results/H2-2026-11-05-a7871a.json`.
- **Official-run authorization:** One H2 official series authorized on 2026-11-04.
- **Historical result:** gate v1.0 **FAIL**, run `gate-9328e564`, July 2026. It
  stays published (`evals/EVAL_RESULTS.md`).
- **Private run anchors:** procedure SHA-256 `5040E999...0A7D`; results file as
  written at the run (CRLF) SHA-256 `6AE3AD8E...381B`.

## Open items

- **`h2-22`:** the one failed case. Its cause has not been examined.
- **H2 offline backup:** copy created; not independently verified.
- **Raw run evidence:** private copy made 2026-11-05 (manifest SHA-256
  `7c80135eb3ed4746687484757c97022bbd385ff28041898dec2b07c8e592cc82`). No overall
  verification PASS: 421 of 422 files matched; one live index file changed during
  the copy.
- **RT2-07 (residual, not resolved):** the private run path appears in the CLI's
  per-record `cwd` metadata. It was found in no message content in the development
  runs where this was checked. The system prompt is not stored, so it cannot be
  checked.
- **R3 (not made in the repository):** `evals/PREFLIGHT.md` §3 still records the
  2026-11-03 clone check with `--ignored`. The private run procedures use
  `git status --porcelain`, as the D3 guard does.
- **p01 NO_OVERLAP (July page, dry runs 1 and 2):** the first excerpt part was 13
  characters inside a 31-character core span; the frozen grader needs 15. No
  grader change and no tuning from this page. No separate assessment was recorded.
- **D10 retest limit:** the targeted trial at `bb6d475` covered d06 and d10 only.
  The other 8 primaries passed earlier, in run `d10-2026-11-04-439347`, and were
  not retested after that prompt change.
- **Earlier wording kept on purpose:** `evals/eval_config.yaml`,
  `evals/run_eval.py`, `evals/check_holdout.py`, `intake/textrule.py`,
  `evals/v2/SCENARIO_SPEC.md`, `evals/v2/RULESET_V1_1.md`, `evals/INJECTION_SPEC.md`
  and `evals/provenance/PAGE_AUTHOR_PROMPT.md` are frozen, signed or verbatim.
  `budget.status` and `datasets.holdout.current` in the gate file are out of date
  and stay, because the result's `config_sha256` binds to the file. `adr/0002` to
  `adr/0004` are historical. `CLAUDE.md` and the files under `.githooks/`, `.kos/`,
  `.codex/` and `.github/workflows/` are functional; only the `.kos/unit.json`
  `status_line` changed (2026-11-05).

## Decisions

- **Policy §13 fallback:** the Phase 4 fallback decision is historical and is not
  re-triggered automatically by D10 results. No purpose-built adjudicator now.
  This does not exempt the verifier from later review.
- **Phase-start STATE rule:** the 2026-07-09 rule is retired (2026-09-19). It
  belonged to the original phased build.
- **Recorded elsewhere:** eval level and eval-gate exception, `BLUEPRINT.md` §7
  amendment; attempts, holdout retirement, `ABSENT:`, RT1-06, H1, official model
  and gate v2.1, `evals/eval_config.yaml`; storage isolation, `evals/PREFLIGHT.md`;
  subscription-only real runs, `evals/run_eval.py`.

## Repair program defects

| Defect | Finding | Repair |
|---|---|---|
| D1 | Page reader dropped headings and list items; 6 of the 8 July misses trace to it | `read_page` returns the title and every text block |
| D2 | Scorer left failed or missing cells unscored | Counted as misses (`evals/run_eval.py`) |
| D3 | Verifier checkout off its pin | Pin and clean-tree checks; dedicated pinned clone |
| D4 | No rule-coverage check | Foreign or repeated rule IDs rejected; a task without one finding per rule dead-letters |
| D5 | Evidence excerpts never checked | VIOLATION and COMPLIANT excerpts must be on the page (shared text rule) |
| D6 | No timeouts | Wall-clock caps; failures end in FAILED with a named class |
| D7 | Rule interpretation gap | Ruleset v1.1, 14 interpretations (`evals/v2/RULESET_V1_1.md`) |
| D8 | Prompt-injection boundary | Page content delimited; HTML escaped; verifier page copy marked untrusted between nonce markers |
| D9 | Eval runner below the eval-gate rules | Runner rewritten for gate v2: preflight, A1, A3, fresh DBs, storage guard, A2, B grading, sanitized results, result classes |
| D10 | 6 of 24 rules had no violation test case | 10 public development pages (`evals/dataset/d10/`) |

## H2 provenance

Rules: `evals/v2/SCENARIO_SPEC.md` §6. Manifest: `evals/v2/holdouts/H2.sha256`,
frozen 2026-11-02 at `35323ab`. Authors: fresh Claude contexts in a private folder,
one spec author and three page authors, none with access to H1.

- **Isolation slip and recovery:** the first batch-1 page author's check script
  read the other 20 pages (numbers only, no page text; no H1, key or briefs). A
  fresh page author with no directory access redid batch 1. The original batch is
  kept privately as evidence.
- **Blind labels:** GPT-6 (OpenAI) got only the 30 pages, the 24 effective v1.1
  rules and the applicability semantics. Of 296 cells, 291 agreed with the draft
  key and 5 disagreed, none primary. All five were adjudicated for the labeler.

## Backlog

Rows are read by project tooling. The `- STATUS:` line at the top of this file is
the unit status (ACTIVE | BLOCKED | DORMANT).

| ID | Auth | Title | Date |
|---|---|---|---|
| P-001 | AUTH | Repair program: defects D1-D10 and Standard gate v2 re-evaluation, local branch repair/v2, phase by phase | 2026-11-02 |
