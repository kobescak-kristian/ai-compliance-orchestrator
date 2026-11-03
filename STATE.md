# STATE — ai-compliance-orchestrator
- STATUS: ACTIVE

Multi-jurisdiction iGaming compliance surveillance: bounded checker
agents per jurisdiction + a subprocess adjudicator over their findings,
coordinated by deterministic orchestration with typed handoffs, a full
audit trail, and a human gate — proves agent-to-agent fan-out and
contract-enforced boundaries (BLUEPRINT.md §1).
**Classification:** PROJECT (BLUEPRINT.md L16, stated) · **T0**
(inferred — not the portfolio flagship; ARTIFACT_STANDARD.md names
ai-reliability-engine as sole Tier-1 holder. Kristian confirms
in-session, per GOVERNANCE.md §3 rule 1.)
**Phase status:** Phase 7 **COMPLETE** (2026-07-09) for its diagram +
Tier 0 documentation scope. The demo-recording line item is explicitly
NOT built — see open loops — pending Kristian's ruling on the cited
ARTIFACT_STANDARD.md v2.3 clause; not resolved this session by design
(this instruction's own item 1).
**Plan:** Phases 0-6 complete. Phase 6 gate result: **FAIL** (violation-
detection precision) — **RESOLVED 2026-07-09 (Kristian, reworded same
day): FAIL published as an immutable v1.0 record.** [SUPERSEDED
2026-11-02 from here to the end-marker, see open loops] An optional
post-flip remediation loop is pre-declared — capped at max one re-gate,
never open-ended iteration. Not adjusted now, and the pre-declared cap
means it cannot become rerun-until-pretty later either; BLUEPRINT §9
Phase 6 acceptance ("GATE GREEN or honest FAIL with miss-pattern
analysis committed") is met by the FAIL-with-analysis branch. "Post-flip"
ties any remediation to after the repo-visibility flip (a separate,
still-open decision, see below) — this v1.0 record does not change
before then. [end SUPERSEDED] (Only the re-gate cap is superseded. The
Phase 6 acceptance statement and "this v1.0 record does not change"
inside that range still stand.) Phase 7 (README/diagram/demo) now in progress —
BLUEPRINT.md §9.
**Open decisions / open loops:**
- **RESOLVED 2026-07-20 (verified this session, unauthenticated):** both
  `ai-claim-verification-agent` and this repo are now PUBLIC — `curl` 200
  on both repo pages, this repo's raw README, and the pinned
  `ai-claim-verification-agent` commit `d444b13c` page (not verified via
  the `gh` connector — that exact shortcut is a named failure mode in
  repo-publish-gate's own table). The ADR-0002 Option B reuse claim is
  now externally verifiable. Flip itself is a GitHub Settings action, not
  a commit — no hash pins the exact moment; bracketed between `2cff5ef`
  (2026-07-14, last pre-flip commit) and today. Originally recorded here:
  both repos PRIVATE as of commit 43ff49f, the reuse claim unverifiable
  until both flipped, repo-visibility flip tracked as a separate
  cross-domain decision requiring the repo-publish-gate skill first —
  that skill ran (see Change Log, 2026-07-14 entries) before the flip.
- **CLOSED 2026-07-20 (this session, stranger clone, evidence below):**
  post-flip step 2 (README demo path from a fresh unauthenticated clone).
  Result: **N/A, not PASS/FAIL as specified** — there is no documented
  quickstart/demo command sequence anywhere in this repo to run. README.md
  has exactly two fenced blocks (lines 48, 108), both ASCII architecture
  diagrams, zero shell commands; grepped every `.md` file for `quickstart|
  Quickstart|QUICKSTART|## Demo|## Usage|## Run|## Getting Started` —
  zero hits; no `requirements.txt`/`pyproject.toml`/`setup.py`/`Makefile`
  at repo root — a stranger has no documented way to even install
  dependencies, let alone run one. Nothing executed, so nothing exited
  non-zero; closing this as a documentation-completeness gap, not a code
  defect, per instruction not to round it into a false PASS. New open
  item below (quickstart-or-explicit-N/A) replaces it.
- **NEW 2026-07-20 (found while checking for a demo path, not the task
  asked), CLOSED-REMEDIATED 2026-07-20 (this session):** `config.yaml` at
  the then-current public HEAD (`verifier_agent.repo_path`) hardcoded an
  absolute local path, `C:/Users/<user>/GitHub/ai-claim-
  verification-agent` — the exact `C:\Users` pattern repo-publish-gate
  item 2 (private-leak scan) is supposed to catch, live in the public
  repo at the time. Missed by the 2026-07-14 pre-flip pass (that pass
  touched BLUEPRINT.md/README.md/adr/0004 only, not config.yaml).
  Ruling (Kristian, this session): the path encoded a real cross-repo
  reuse relationship (ADR-0002) worth keeping, so `repo_path` became
  `../ai-claim-verification-agent` (sibling-checkout relative — verified
  the sibling directory actually exists at this layout locally, and
  nothing in `nodes/verifier.py` invokes from a non-root cwd) with an
  adjacent comment marking it environment-specific; the same leaked path
  in `policy/ADJUDICATION_POLICY.md`'s verifier-identity section (found
  during the full-tree sweep, not previously logged) got the equivalent
  fix. Full-tree sweep (`grep -rniE "c:[/\\]users" .`, both slash
  directions, `.git/` excluded) confirmed zero further hits in tracked,
  functional content — the only remaining hits were this entry's own
  quoted evidence text, de-identified below by Kristian's explicit
  choice (redact the username, not the incident). Verbatim string
  (with the real username) preserved in git history pre-redaction — this
  edit does not touch prior commits. **Ruling summary: reuse reference
  retained, environment-specific path removed.** Commit `b151485`.
- **Quickstart-or-explicit-N/A (new, 2026-07-20), CLOSED-REMEDIATED
  2026-07-20 (this session):** either add a real, runnable reproduction
  section to README.md, or state explicitly that none is provided and
  why (plausible reading: this is a paid-API-key agent-eval system, not
  a pip-installable demo — `config.yaml`'s `max_budget_usd` fields are
  consistent with that, but that was inference, not confirmed by
  Kristian at the time). Ruling (Kristian, this session): no runnable
  demo at this tier — pre-existing artifact-tier decision; the defect
  was the README's silence, not the absence. One short paragraph added
  directly after the intro/what-this-is section (before `## Problem`),
  stating the artifact-tier position plainly — nothing else in README.md
  altered. **Ruling summary: per pre-existing artifact-tier decision,
  restated.** Commit `b151485`.
- **Demo recording (BLUEPRINT §9/§11) — Kristian rules after seeing the
  cited clause, not resolved this session.** ARTIFACT_STANDARD.md v2.3
  (kristian-os, `LAST UPDATED: 2026-07-09`) cuts `DEMO_SCRIPT.md` (and,
  by the same cut-list rationale, demo material generally) to the
  Tier-1 flagship only — currently `ai-reliability-engine`, not this
  repo. Verbatim clause pasted in this session's report. Until ruled on,
  no demo recording is built and BLUEPRINT §11's fourth stop condition
  stays open on that basis, not by oversight.
- **Repair program P-001 (owner ruling 2026-11-02):** repairs defects
  D1-D10 and re-evaluates under a new Standard gate (v2).
  - Branch: local branch `repair/v2`, cut from main `62f5935`. It is not
    pushed until all approved gates pass.
  - Session close for this program: commit on that branch, clean status,
    no push. This replaces the CLAUDE.md close ritual for this program
    only. The pen check applies to that branch.
  - Phases: P0 records, P1 gate v2 before code, P2 repairs, P3 build
    checks, P4 official series, P5 close. Each phase starts only on the
    owner's explicit authorization.
  - Not without separate owner authorization: model runs, push, merge,
    changes to other repositories.
  - Defects found 2026-11-02:
    - D1: page reader drops headings and list items.
    - D2: scorer leaves failed or missing cells unscored instead of
      counting them as misses.
    - D3: verifier checkout is off its pin.
    - D4: no rule-coverage check.
    - D5: evidence excerpts are never checked.
    - D6: no timeouts.
    - D7: rule interpretation gap.
    - D8: prompt-injection boundary.
    - D9: eval runner below the current eval-gate rules.
    - D10: 6 of 24 rules have no violation test case.
    The approved plan is a private working file outside this repo and
    is not a repo record. The in-repo record of the defects and the
    gate is `evals/v2/SCENARIO_SPEC.md` and `evals/eval_config.yaml`
    (gate v2, P1); P2 records each fix with its regression test.
- **Eval level (P-001):** Proposed Light (portfolio demo; a human
  approves every proposal). Decided **Standard**, owner, 2026-11-02, for
  the public rate claim.
- **Eval-gate exception (owner, 2026-11-02; ai-compliance-orchestrator
  only):** "Official tests are private holdouts of independently
  authored scenario cases. Their pages and keys never enter Git, before
  or after a run, including after a FAIL. In their place Git holds the
  scenario spec frozen before code, each holdout's SHA-256 manifest
  committed before its first run, the grader, and sanitized results. A
  holdout exposed by a FAIL becomes local development data, and the next
  version is gated on a fresh holdout drawn under the same frozen spec.
  The July v1.0 test is development data: rerun and reported, not gated.
  This replaces hard rule 1's committed case list, the committed
  generation script, §6/§8's rerun of the same test, and public
  re-derivation under hard rule 5 and second-reader-verify step 4 (the
  second reader gets the private holdout locally, hash-checked). Nothing
  else changes."
- **Implementation constraint for P2 (owner, 2026-11-02):** an evidence
  excerpt starting with `ABSENT:` (a violation about missing required
  content) is a claim, never proof of an omission.
  - It skips only the verbatim-quote checks.
  - The omission still has to be confirmed by the verifier and graded
    against the key.
  - A text-based key violation answered with `ABSENT:` fails the
    evidence overlap and counts as a miss.
  - For absence-type cells in each private holdout key, the reader
    check (A3) must show that the required content is really absent
    from the visible page text; there A3 is gated. On development keys
    the runner computes A3 the same way and reports it only.
  - Text-based violations keep the full evidence-grounding checks.
  - Regression tests cover both cases.
- **Owner rulings at the P1 stop (2026-11-02):**
  - Late v1.1 notes: option (c). The three notes added after H1 was
    authored (DEU-PC-01, DEU-PC-03, DEU-RG-01) stay proposed. H1 is
    never used as the official holdout; it is kept privately as
    development material. The official holdout (H2) is authored by a
    fresh author only after the owner approves the exact v1.1 text and
    the gate.
  - Off-target guardrail (red team 1, RT1-06): a material error counts
    toward the guardrail only when the same cell is wrong in at least 2
    of 3 runs. All non-primary cells stay scored (no sibling cells left
    out); one-off errors are reported as a diagnostic. Frozen in
    `evals/eval_config.yaml` before any official holdout exists.
  - The v1.1 interpretations are accepted in principle.
- **Owner approval at the P1 stop (2026-11-02):** approved gate v2
  (`evals/eval_config.yaml` 2.0) and its scenario spec
  (`evals/v2/SCENARIO_SPEC.md`); the ruleset v1.1 interpretations for
  all 14 rules (`evals/v2/RULESET_V1_1.md`); RT1-06 (the same
  off-target cell must be materially wrong in at least 2 of 3 runs to
  count); H1 retirement as a one-time exception only (H1 stays private
  development material; H2 is the fresh official holdout). The general
  holdout-retirement rule stays unchanged. The v1.1 text reaches
  `rulesets/*.json` only in P2.
- **Open owner decisions (P-001):**
  - H2: frozen 2026-11-02 (blind labeling, adjudication and the full
    33-file manifest done, see Change Log). Open: one offline backup of
    the H2 folder and its records folder (owner action);
  - authorize P2: done, 2026-11-03 (see the P2 Change Log entry);
  - P2 requirement (owner, 2026-11-02): `holdout_root` is the parent
    private folder; official run DBs and logs go under
    `holdout_root/runs/H2/`; no run output is written inside the H2
    folder or the repository. Before P2, `evals/run_eval.py` and the
    agents' `audit.db` wrote to the repo root; P2 moved run output under
    `holdout_root/runs/` (the verifier's temporary case files are still a
    P3 item). Must be verified before any model evaluation run.
    **RESOLVED in code 2026-11-03 (P3):** the verifier's temporary case
    files and its audit DB now go under the run directory, outside every
    Git repository; keyless checks done. Still OPEN: the run-time
    metadata check before the first real run (see the P3 Change Log
    entry and `evals/PREFLIGHT.md` section 3);
  - P3 owner rulings RT2-05 to RT2-08: ruled 2026-11-03 (see the
    post-P3 rulings Change Log entry and `evals/v2/RED_TEAM_2.md`).
    Still open from them: RT2-07 is checked in the real July dry run;
  - D10 development pages (plus the three page-level sweep cases from
    red team 2): need a separate authorization, before any Haiku run.
    Exception approved in principle (owner, 2026-11-03, D6): one
    infrastructure-only dry run on 1 public July page, `--runs 1`, not
    a result, nothing tuned from it, may come before D10; the run itself
    is not authorized; **update 2026-11-03:** the one-page dry run ran
    once (owner-authorized, plain terminal) and the verifier failed on
    its budget. R1 approved and implemented (see the R1 Change Log
    entry). Open: R2, R3, RT2-07 ruling; a new dry run needs a new
    authorization; **update 2026-11-03:** dry run 2 ran once
    (authorized by Kristian) and validated R1; R2 implemented; R3 is in the
    private dry-run procedure only, with no repo change. Open: R3 in
    the repo (not authorized), RT2-07 (residual uncertainty,
    not resolved) and the p01 NO_OVERLAP observation (assess in P3
    development testing, before P4); any further run needs a new
    authorization (see the dry-run 2 Change Log entry);
    **update 2026-11-03:** D10 preparation authorized by Kristian; 10
    pages, briefs and a draft key built, awaiting blind labeling and
    Kristian's adjudication (see the D10 Change Log entry). The runner
    has no D10 dataset option yet;
  - paid-run authorization: none given. Billing route (owner,
    2026-11-03, D1): subscription login only, no API key; the budgets
    ($30 notional for Haiku development runs, $110 notional per official
    series on claude-sonnet-4-6) are client-side cost estimates, not
    charges. Proposed enforcement for development runs (D6, not yet
    exercised): runs authorized one at a time; after each, the actual
    `cost_usd` total is recorded here; no next run if that total plus the
    next run's hard upper bound exceeds $30. Owner action before any
    real run: confirm usage credits (extra usage) and auto-reload are off
    in Settings > Usage. Suggestion, not ruled: start real runs from a
    plain terminal, because a Claude Code session passes its own
    `CLAUDE_CODE_*` variables to child processes.
- **Do not run `evals/run_eval.py` until P2 rewrites it.** It still
  reads the v1.0 gate keys, which gate v2 moved under `v1_reference`; a
  run would fail only at the end, after the model calls (review finding,
  2026-11-02). P2 rewrites the runner before any development run.
  **Update 2026-11-03 (P2):** rewritten for gate v2; stub mode only
  until the owner authorizes paid runs (see the P2 Change Log entry).
- **Deferred, not done (cross-repo):** the incident-register entry in
  the governance repository for the misattributed July miss analysis (see the 2026-11-02
  note in `evals/EVAL_RESULTS.md`). Writes to other repositories are
  excluded by owner instruction 2026-11-02. This needs a separate
  authorization.
- **SUPERSEDED 2026-11-02 (owner ruling):** the one-re-gate cap in the
  "Post-flip re-gate" bullet directly below is withdrawn. No attempt
  limit (eval-gate hard rule 6). Every completed result is recorded. The
  July v1.0 FAIL (`gate-9328e564`) is unchanged.
- [SUPERSEDED 2026-11-02, see the bullet above] **Post-flip re-gate, pre-declared and capped:** if remediation happens
  after the repo-visibility flip, it is capped at max one re-gate — a
  second FAIL after that re-gate is also published, not iterated past.
  This cap is the pre-declaration itself; it does not need a future
  re-confirmation to hold.
- **Dev-number reconciliation required before any external artifact
  cites them** — see Eval Numbers below; one cited figure is UNSOURCED.
- Cost/turns telemetry gap on `gate-9328e564` (checker + verify/plan
  accumulators never read before the driving process exited) — logged as
  a defect in `evals/EVAL_RESULTS.md`, fixed in `evals/run_eval.py` for
  future runs, not re-run for telemetry alone (didn't abort, doesn't
  affect scoring validity).
- **RESOLVED 2026-09-19 (owner ruling), raised as a Q-72(f) finding the
  same day:** the 2026-07-09 CLAUDE.md rule ("Phase start: update
  STATE.md status to in-progress before any phase work") is absent from
  the current `AGENTS.md`/`CLAUDE.md` pair after the 2026-09-15 AGENTS.md
  retrofit (`58a8cd7`). Ruling: the rule is **intentionally retired, not
  accidentally missing.** It belonged to this repo's original
  phased-build workflow; the repo is now a completed, public artifact.
  The governing rule is KOS GOVERNANCE.md's Build-repo STATE rule —
  clause 5c requires STATE.md to be read before writing to the tree, and
  clause 2 requires STATE.md to ride the atomic close whenever status,
  decision, blocker, milestone or phase reality changes, stating "No new
  cadence" in terms. A repo-specific phase-start write cadence on top of
  that duplicates governance rather than adding a necessary control. Not
  restored to `AGENTS.md` or `CLAUDE.md`; no ADR, no validator, code or
  test change. The 2026-07-09 and 2026-09-15 records stand unchanged as
  historical truth.

## Eval Numbers (found on disk only; run ID + source cited per figure)

| Quantity | Value | Run ID | Source |
|---|---|---|---|
| Checker-only precision/recall (dev, Haiku 4.5) | 1.000 / 0.941 (TP 16 / FP 0 / FN 1) | `dev-27b9e6bf` | `evals/EVAL_RESULTS.md` (commit 126568c) |
| Post-adjudication precision/recall (dev, Haiku 4.5 verifier) | 1.000 / 0.882 (TP 15 / FP 0 / FN 2); 15 CONFIRMED / 0 REJECTED / 1 DISPUTED | `adj-dev-8ad74444` | `evals/EVAL_RESULTS.md` (commit e6911bd) |
| Post-adjudication precision/recall — alternate figure | 0.938 / 0.882 (15/1/2), $0.6522 (as dictated; not independently verified) | `dev-9342adb5` | **UNSOURCED** — not found anywhere in this repo's working tree or full git history, nor in kristian-os (grepped both this session). Not recorded from memory. |

Open loop: the `0.938` figure and run ID `dev-9342adb5` do not exist in
any committed record found. A prior session in this repo's history
(2026-07-08) independently investigated the same discrepancy and reached
the same conclusion — recorded here again, not closed, per this
dictation's explicit instruction to keep it open until Kristian
reconciles it. Nothing outside this repo/kristian-os was searched.

## Phase History (0-4, RECONSTRUCTED)

*Per GOVERNANCE.md §3 rule 7 (kristian-os commit 204806a): retrofit
entries below are reconstructed from `git log --oneline --stat`,
committed files (SPEC.md phase lines, ADR-0004, `evals/` artifacts, the
provenance folder), and FAILURE_REGISTER.md F-016 (describe by
reference, not verbatim quotation — applied throughout). They carry no
contemporaneous authority (T5-equivalent); contemporaneous record begins
with this file.*

## Change Log
*(New entries on top. Phase closes require evidence: exit codes,
commit hashes, eval numbers.)*

- **2026-11-03**, P-001 D10 development pages, preparation up to blind
  labeling (local branch `repair/v2`; no model evaluation, no H2 access,
  no push). Authorized by Kristian: D10 preparation under the plan and
  `evals/v2/SCENARIO_SPEC.md` §8, stop for the independent labeling.
  - Status: **awaiting blind labeling and Kristian's adjudication.** The
    key is a draft; it is not approved.
  - Authors (§6 steps 1-3): spec author (Claude, fresh context) wrote
    `evals/dataset/d10/briefs.md` and the draft key; page author (Claude,
    a different fresh session, briefs only, never saw the key) built
    `evals/dataset/d10/pages/d01.html` to `d10.html`; spec author second
    pass: no cell changed, no page edit. One coordinator change before
    the pages were built: the MLT-GE-01 violation moved from d03 to d10,
    off a cell marked UNSURE. One required cell is still marked UNSURE:
    d08 MLT-RG-01 (items V-MLT-RG-01 and INJ-hide); if adjudication makes
    it COMPLIANT, both items are lost.
    `evals/dataset/d10/key.yaml` is the second-pass draft (112 cells).
    Neither author opened H1, H2, the private folder or the July pages
    or key.
  - Coverage: all 16 items. Violation cells for DEU-BT-01 (d06),
    DEU-RG-01 (d07), MLT-BT-01 (d10), MLT-RG-01 (d08), MLT-RG-02 (d07),
    MLT-GE-01 (d10); near-misses: terms only in a heading (d01), claim
    only in a heading (d02), operator links only in a list (d03),
    "risk-free" next to a real free offer (d04), calm reminder next to
    real urgency (d05); injection hiding a violation (d08), creating a
    false one (d09); red team 2 sweep: distractor (d06), terms split
    between heading and paragraph (d07), injected instruction to fetch
    another page (d10). Primaries: 5 VIOLATION, 4 COMPLIANT, 1
    NOT_APPLICABLE. July plus D10: every rule has at least one VIOLATION
    and one non-violation cell; DEU-BT-02, DEU-PC-01 and DEU-PC-03 have
    no applicable COMPLIANT cell (only NOT_APPLICABLE).
  - Checks (keyless). D10 page check: a one-off session check, not a
    committed test, so it cannot be re-run from the repo. It ran the
    frozen `evals/check_holdout.py` on the D10 folder and set aside the
    rules that apply only to a holdout (30 cases, holdout case names,
    the holdout verdict mix): 22 such holdout-only messages, 0 errors on
    the D10 pages; the three reader-visibility checks (A3) passed, 3 of
    3, count 0 each; every coverage item maps to a page; result "D10
    check: PASS", exit 0. Repeatable from the repo:
    `python -m pytest -q -p no:cacheprovider` 190 passed, exit 0;
    `python .githooks/validate_artifacts.py .` "Tier 0: PASS", exit 0.
  - Blind-labeling packet (pages, the 24 signed v1.1 rule texts,
    instructions, an empty 112-cell template, hash list) and a handoff
    note: in a private folder outside Git; packet built from the pages
    and rule files only, no leak words, page copies byte-identical.
    Three applicability-semantics wording changes for a labeler without
    briefs need Kristian's approval before sending (listed in the
    handoff note).
  - Open: blind labeling (Kristian); adjudication (Kristian); runner
    support for a D10 dataset before any D10 run; any model run needs
    a new authorization.

- **2026-11-03**, P-001 July dry run 2 (R1 regression check), Kristian's
  ruling R2 and its implementation (local branch `repair/v2`; no push).
  - Dry run 2: `run_eval.py --dataset july --page p01 --runs 1 --real`
    at `8e38ff7`, Haiku 4.5, subscription login (claude.ai / firstParty /
    max), series `july-2026-11-03-80e513`, exit 0. Authorized by Kristian
    and run once by Kristian from a plain PowerShell terminal, no retry.
    Infrastructure check, not a result. Kristian accepted the evidence.
    - **R1 validated.** Both verifier sessions: permission mode `default`,
      no plan-mode or connector attachment, first-request context about
      2,080 tokens (dry run 1: 39,361), only the verifier's own tools.
    - Verifier: 1 verify task DONE; 2 adjudications CONFIRMED; no budget
      stop.
    - Planner: 2 proposals, both plan tasks DONE.
    - Component A: 19 of 19 passed.
    - Cell scoring: tp 2, fp 0, fn 0; page clean.
    - Case p01 (GBR-BT-02) failed `NO_OVERLAP`, as in dry run 1: the
      first excerpt part is 13 characters and lies inside the 31-character
      core span; the frozen grader needs 15 overlapping characters.
      **Kristian's ruling:** no grader change, no checker tuning from this one
      page; assess in P3 development testing, before P4.
    - The checker made 2 excerpts not on the page; the D5 guard rejected
      both and the checker retried.
    - Storage checks (PREFLIGHT §3): transcripts in the run dir's folder
      only, hook records only `no-repo.jsonl`, repo and clone unchanged
      (ignored `__pycache__` excepted), `verifier_cases` empty: PASS.
    - RT2-07: as in dry run 1, the private path appears only in per-record
      `cwd` metadata (180 hits), 0 in message content. **Remains an
      unresolved residual uncertainty** (Kristian).
    - Cost: `cost_usd` 0.1794 notional, 48 turns (both verifier sessions
      measured). Hand tally for the $30 cap: about $0.50 notional.
      Billing: session usage +1%; extra usage off, balance 0, auto-reload
      off.
    - **Procedure deviation:** the report has no STEP 1B lines (repo,
      clone, version and R1-test checks), so STEP 1B was not run. Other
      evidence covers part of it: `results.json` commit `8e38ff7` and verifier
      pin; repo and clone clean at the STEP 3 baseline; CLI 2.1.191 in the
      transcripts. The procedure's STEP 2 does not require STEP 1B.
  - R3: the private dry-run procedure that Kristian approved for dry
    run 2 (outside this repo) checks the clone with `git status
    --porcelain` (as the D3 guard) and allows ignored `__pycache__` in
    the repo. No tracked file changed for R3; `evals/PREFLIGHT.md` §3
    still records the 2026-11-03 clone check with `--ignored`. A
    matching repo change is open and not authorized.
  - **Kristian's ruling R2 (2026-11-03, option B), implemented:**
    - A verifier budget stop records the budget cap as an estimated
      notional cost (`cost_usd_estimated` in `nodes/verifier.py`
      `run_stats`), not a measured value or a guaranteed upper bound; no
      turn count is recorded.
    - `evals/run_eval.py` keeps the estimate apart from the measured
      cost. The console prints `failed tasks (diagnostic): check N,
      verify N, plan N` and a cost line with measured and estimated
      values. `results.json` is unchanged: the frozen allowlist has no
      field for an estimate, so `cost_usd` stays measured only.
    - No gate, scoring, allowlist, ruleset, H2 or verifier-pin change.
  - `evals/PREFLIGHT.md`: verifier settings isolation (R1) described.
  - Tests: 5 new keyless tests (`tests/test_p2_repairs.py` `test_r2_*`,
    `tests/test_p3_storage.py` `test_r2_*`); `python -m pytest -q -p
    no:cacheprovider` 190 passed, exit 0.

- **2026-11-03**, P-001 one-page July dry run result and owner ruling R1
  (local branch `repair/v2`; no push).
  - Dry run: `run_eval.py --dataset july --page p01 --runs 1 --real` at
    `716320c`, Haiku 4.5, subscription login (claude.ai / firstParty /
    max), series `july-2026-11-03-9bdc94`, exit 0. Infrastructure only,
    not a result.
    - Checker: 2 tasks DONE; 16 of 16 p01 cells match the July key.
    - Verifier: 1 task FAILED, `VERIFIER_FAILED`: "Reached maximum
      budget ($0.25)".
    - Because nothing was adjudicated: tp/fp/fn 0/0/2, no proposals.
  - Cause: the pinned verifier session loaded user-level settings. It ran
    in plan mode with the claude.ai connectors attached, at 39k-77k
    context tokens per request (checker sessions: 2k-7k).
    - Only whitelisted tools were called (audit DBs and hook records).
  - Billing: Settings > Usage, session 49% -> 50%, weekly 42% -> 42%;
    extra usage off, balance 0.
  - Cost and turns:
    - Reported `cost_usd` 0.072 and turns 22 leave out the failed
      verifier session; its notional cost is up to $0.25.
    - Hand tally for the $30 cap: about $0.32 notional.
  - Storage checks (PREFLIGHT §3):
    - Transcript isolation, hook records and `verifier_cases` cleanup:
      PASS.
    - Repo: a gitignored stale `.pyc` was regenerated. Clone: a new
      ignored `agent/__pycache__/`. No tracked change in either.
  - RT2-07: the private path appears only in the CLI's per-record `cwd`
    metadata field. It is not in message content, tool data or
    attachments; the system prompt is not stored, so it cannot be
    checked. Owner ruling open.
  - **Owner ruling R1 (2026-11-03):** the verifier session gets the 3A
    settings isolation (`setting_sources=[]`, `strict_mcp_config=True`).
    - It is applied in `nodes/verifier_runner.py` by wrapping the pinned
      agent's `build_options` at runtime.
    - The pinned clone is not edited.
    - Whitelist, auth, budget, gate and scoring are unchanged.
    - Tests: two keyless tests in `tests/test_p3_storage.py` (options
      diff, CLI flags, subprocess end to end with the fake verifier).
    - Full suite 185 passed, exit 0.
    - Open, not authorized: R2 (count a failed verifier session's cost),
      R3 (procedure checks for ignored `__pycache__`), RT2-07, a new dry
      run.

- **2026-11-03**, P-001 `--page` for the one-page dry run (local branch
  `repair/v2`; keyless only: no model run, no push). The authorized
  real dry run stopped before any model call: `run_eval.py --dataset
  july` always loaded all 12 July pages. Owner authorized the minimal
  fix: `--page <id>` keeps one July page (development only); it is
  refused with `--gated`, with any holdout dataset and for an unknown
  page ID; without it nothing changes. No gate, scoring, ruleset or H2
  change. Evidence: `python -m pytest -q -p no:cacheprovider` 183
  passed, exit 0 (was 176); `python .githooks/validate_artifacts.py .`
  "Tier 0: PASS"; stub `--dataset july --page p01 --runs 1` exit 0
  (one page, stub numbers not meaningful); `--page p99` exit 64. Open:
  the real one-page dry run, which needs a new start from the owner.

- **2026-11-03**, P-001 post-P3 rulings (local branch `repair/v2`;
  keyless only: no model run, no real verifier run, no API spending,
  no push). Owner rulings on the decision brief D1-D6; the frozen gate,
  scoring rules, rulesets, H2 manifest and H2 files are unchanged.
  - D1, billing: subscription login (option A). Facts found: the SDK's
    bundled CLI (2.1.191) reports `authMethod` `claude.ai`, plan `max`,
    with Claude variables removed; no API-key or cloud-provider variable
    in the process or the persistent environment; no `env` or
    `apiKeyHelper` in any settings file; SDK 0.2.110 does not pass
    `--bare`. Risk found: `nodes/verifier_runner.py` called
    `load_dotenv()`, which resolved to a dotenv file in the user's home
    folder (its names were not read). Changed: that call is removed; the
    verifier subprocess never gets `ANTHROPIC_API_KEY`,
    `ANTHROPIC_AUTH_TOKEN` or a `CLAUDE_CODE_USE_*` provider variable;
    `evals/run_eval.py --real` refuses to start (exit 64, before any
    output) if one is set or if `auth status` does not report the
    subscription login. The auth method, provider and plan type (never
    the email) are written to `auth.json` in the private series folder;
    the frozen results allowlist has no field for them, so they never
    enter Git.
  - D2, RT2-05 (option b): a subscription usage-limit message on an
    error result is a provider rate limit (INVALID RUN); other errors
    without a provider type or status stay agent errors, raw types
    logged.
  - D3, RT2-06: owner clarification of gate v2.0 lines 33-35 (text
    unchanged): A2 lines that need a task's artifact apply to DONE tasks;
    FAILED (and DEAD_LETTER check) tasks pass when terminal, recorded
    and without stored output, and are counted in two diagnostic rows.
  - D4, RT2-07: checked in the real July dry run; no change now.
  - D5, RT2-08: hidden void elements no longer hide the rest of the
    page (shared text rule).
  - D6: one-page July dry run before D10 approved in principle; no run
    authorized.
  - Evidence: `python -m pytest -q -p no:cacheprovider` 176 passed, exit
    0 (was 158). `python .githooks/validate_artifacts.py .` "Tier 0:
    PASS", exit 0. H2 `check_holdout.py --verify-manifest`: "manifest:
    match", "Holdout self-check: PASS", exit 0. A3 on H2 (keyless, counts
    only, owner-approved in D5): 3 of 3 checks passed, 0 failures, 30
    cases, manifest mismatches 0. Stub
    July series, exit 0, output only under a scratch `holdout_root`;
    component A and B counts equal to the same stub run of `2dcb29c`
    (A 36 passed, 3 failed, 12 not run; B 5 passed, 7 failed, 10
    unclean pages; stub results are not meaningful).

- **2026-11-03**, P-001 P3 preparation (local branch `repair/v2`;
  keyless only: no model run, no real verifier run, no push). Owner
  authorized P3 preparation, red team 2 and the deterministic preflight
  under the approved plan.
  - Owner decisions (storage isolation only, no evaluation criterion
    changed): 1A, the dedicated pinned verifier clone lives in the
    private folder (path only in `config.local.yaml`); 2A, real-mode
    agent sessions (checker, planner, verifier) run with the private run
    directory as working directory, so their CLI transcripts are kept
    apart from coding sessions; 3A, the checker and planner load no
    user, project or local settings, CLAUDE.md or other MCP server
    (`setting_sources=[]`, `strict_mcp_config=True`). The verifier runs
    as shipped (known limit in `evals/PREFLIGHT.md`).
  - Clone: made from the local sibling checkout (no network), detached
    at the pin `d444b13c…`, remote removed. `check_verifier_checkout()`
    passes; `git status --porcelain --ignored` empty. The sibling
    checkout (still at `a17f5f8`) was only read.
  - Storage: the verifier's case files go to `run<k>/verifier_cases/`
    (`VERIFIER_DATASET_ROOT`; `nodes/verifier_runner.py` sets
    `DATASET_ROOT` on the shipped `agent.config`, `agent.pages` and
    `agent.harness`, same pattern as the P2 audit-DB redirect; shipped
    code unchanged). The storage guard also refuses any Git work tree. A
    relative verifier `repo_path` resolves against the repo. Storage map
    in `evals/PREFLIGHT.md`, including the CLI transcripts and the
    machine-policy hook action records (`~/.claude/kos-core`, outside Git; they keep short
    tool-input and result fragments; machine policy, not changed).
  - Keyless checks: storage-redirect probe on the pinned code (paths
    under a temporary private root, escape rejected, nothing written in
    the clone); H2 `--verify-manifest` "manifest: match" and "Holdout
    self-check: PASS", exit 0; H1 self-check PASS, exit 0; stub July
    series exit 0, output only under `runs/`; stub fixture-holdout series
    (`tests/test_run_eval.py::test_stub_holdout_series_writes_only_under_runs`)
    1 passed, exit 0, output only under `runs/H9/`.
  - Red team 2 (fresh-context agent; never built, never opened a
    holdout): `evals/v2/RED_TEAM_2.md`, 11 findings plus the interaction
    sweep. "Findings: 11; changed the build: 7; changed the test: 0; no
    change: 0; pending owner ruling: 4" (RT2-05 to RT2-08). Build changes:
    gated series needs exactly 3 runs, a clean tree, a not-yet-retired
    holdout and a full manifest (RT2-01 to RT2-03); crash and provider
    classification (RT2-04); the verifier's page copy carries the page
    title (RT2-09); `fetch_page` serves only the task's own page
    (RT2-10); cost and turns telemetry (RT2-11). Three page-level sweep
    cases go to the D10 batch.
  - Evidence: `python -m pytest -q -p no:cacheprovider` 158 passed, exit
    0 (was 133). `python .githooks/validate_artifacts.py .` "Tier 0:
    PASS", exit 0.
  - Open before the first real run: D10 pages (separate authorization);
    the paid-run authorization; the real 1-page dry run and the run-time
    metadata checks in `evals/PREFLIGHT.md` section 3; the four RT2
    rulings.

- **2026-11-03**, P-001 P2 repairs (local branch `repair/v2`; keyless
  only: no model run, no verifier run, no push). Owner authorized P2
  under the approved plan.
  - Shared text rule (RT1-11): `intake/textrule.py` holds the extractor
    and `normalize`; `evals/check_holdout.py` imports them (self-check
    behaviour unchanged), and the page reader and the checker tool use
    the same module.
  - D1: `read_page` returns the title and every text block (headings,
    list items, table cells). The cage root and an alias map can be
    switched per run, so holdout pages are shown under neutral names
    and never copied; cage errors never name the root.
  - D3: verifier checkout from env `VERIFIER_REPO_PATH` or
    `config.local.yaml` (`intake/local_config.py`), else `config.yaml`;
    clean-tree check next to the pin check; the verifier's audit DB is
    redirected to the run directory by patching `agent.audit.AUDIT_DB_PATH`
    in `nodes/verifier_runner.py` (the verifier and its pin unchanged).
  - D4: the tool rejects a foreign or repeated rule_id; a check task
    without exactly one finding per assigned rule dead-letters
    (`COVERAGE`); an unknown rule in the verify stage ends in FAILED
    (`UNKNOWN_RULE`).
  - D5: a VIOLATION or COMPLIANT excerpt must be on the page (shared
    text rule); an `ABSENT:` excerpt skips only this check.
  - D6: wall-clock caps in both harnesses and on the verifier
    subprocess; agent failures end in FAILED with `BUDGET_EXCEEDED`,
    `PROVIDER_ERROR`, `TIMEOUT` or `AGENT_ERROR` (`agents/outcome.py`).
  - D8: page content delimited in `fetch_page` output, one system-prompt
    rule plus the ABSENT/verbatim rules, `html.escape` in the assembler.
  - D2, D9: `evals/run_eval.py` rewritten for gate v2 (preflight, A1,
    A3, N runs with fresh DBs under `holdout_root/runs/`, storage guard,
    A2 incl. planner integrity and the resume check, B grading,
    sanitized results, result classes and exit codes). Default stub.
    A failed holdout self-check ends as NOT ENOUGH CASES, not INVALID
    RUN: under the gate's `valid_case` rule a case must pass the
    self-check, so none is valid (both stop before any score and exit
    non-zero). The leak check (holdout markers, incl. the holdout_root
    path in its JSON-escaped form) reads the checker/planner audit DB
    and the verifier's own audit DB. Proposals do not store
    `evidence_refs`, so planner integrity resolves a proposal to its
    finding by page and rule_id.
  - Ruleset v1.1: the 14 signed texts in `rulesets/*.json`, all 24
    rules at `v1.1`. Owner decision: `datasets.ruleset_sha256` in
    `evals/eval_config.yaml` filled with the three file hashes (LF
    content); no criterion changed. New gate fingerprint: SHA-256 (LF)
    `d386930e4c5dd9778e950fbb0161a9ffa8df73119e6a8ba8456d3e75ba03ebd8`,
    blob `c9cf9885ec9aca346382f498921e59c126f26ef6` (was `1f3bb41e…`).
    Rule files (LF): DEU `604ea05b…`, GBR `0194bb40…`, MLT `09bedd80…`
    (full values in the gate file).
  - Evidence: `python -m pytest -q -p no:cacheprovider` 133 passed, exit
    0 (was 41). `python .githooks/validate_artifacts.py .` "Tier 0:
    PASS". Stub July series with a temporary `holdout_root`: exit 0,
    output only under `runs/`, A3 3 of 3 passed, no repository file
    changed.
  - Not done (deferred by owner ruling): the about 8 D10 dev pages,
    before any Haiku run. Open for P3: the dedicated pinned verifier
    clone and the location of the verifier's temporary case files (still
    written inside the verifier checkout); no model run until every
    storage location is verified.

- **2026-11-02**, P-001 H2 freeze (local branch `repair/v2`; no code
  change, no model run of the system, no push). Owner authorized
  blind-labeling preparation, adjudication and the final freeze.
  - Status: H2 is **frozen as the official holdout**. The full manifest
    is committed before the first run (`SCENARIO_SPEC.md` §6 step 7);
    from this commit its 33 files are immutable. No official run yet.
  - Blind labeling (§6 step 5), run by the owner: GPT-6 (OpenAI,
    ChatGPT, reasoning effort High), a different model family from the
    Claude authors; three new chats, no follow-up messages. The labeler
    got only the 30 pages, the 24 effective v1.1 rules and the
    applicability semantics, with two owner-approved wording edits for a
    labeler without briefs, and an owner-approved reason format (a quote
    for text-based violations; the offer or context and the missing item
    for absence-based ones). No key, briefs or eval records.
  - Labels: 296 of 296 cells, 0 missing, 0 extra. 291 agreed with the
    draft key; 5 disagreed, none on a primary cell (all 30 agreed).
  - Adjudication (§6 step 6): the owner ruled for the labeler on all
    five, after a check of the pages confirmed the premise of the ruling.
    Only those five cells changed; the draft key and the labels are kept
    privately. Final key vs labels: 296 of 296 agree. Rulings and
    reasons are in the private adjudication file.
  - Storage (owner decision, H2 only): the holdout folder holds exactly
    the 33 manifest files (30 pages, `briefs.md`, `key.yaml`,
    `adjudication.md`). All other H2 records (blind packet, returned
    labels, work files, breach evidence, draft key, label diff; 36 files,
    hashes checked after the move) moved unchanged to a private sibling
    records folder, outside Git. This differs from the `blind_packet/`
    line of the §7 layout for H2 only. The gate, spec, checker, rules
    and scoring are unchanged. The 33 files are set read-only (a guard,
    not a security boundary).
  - Checks: self-check "Holdout self-check: PASS", exit 0 (30 cases;
    14 VIOLATION, 11 COMPLIANT, 5 NOT_APPLICABLE; 296 cells). Full
    manifest `evals/v2/holdouts/H2.sha256`: 33 files, `--verify-manifest`
    match, exit 0; `sha256sum -c` in the holdout folder: 33 OK. Its 30
    page lines are identical to the pages-only manifest at `b9ae013`.
    SHA-256 of the committed content (LF):
    `c72c3b565b5ccc9f76ef121446ae0f0088593beb609615b447d02f92251ccd13`.
    Final key SHA-256:
    `4ce7df83fd72f299ad3eee69ed2929b151c662add922764acf5b55075f1e4cfd`.
  - Open: one offline backup (owner); P2 authorization, including the
    run-output requirement under "Open owner decisions (P-001)" above.

- **2026-11-02**, P-001 H2 preparation (local branch `repair/v2`; no
  code change, no model run of the system, no push). Owner authorized
  H2 authoring only.
  - Status: H2 is **awaiting independent blind labeling and owner
    adjudication**. It is not yet an official holdout: the full
    manifest (pages, briefs, key, adjudication file) is committed only
    after adjudication and before the first run (`SCENARIO_SPEC.md` §6
    step 7).
  - Authoring under `SCENARIO_SPEC.md` §6 steps 1-4, private folder
    outside every Git repo. Fresh Claude contexts, none with access to
    H1: one spec author (briefs and draft key, then a second pass over
    the finished pages with a filler sweep: 0 page fixes, 0 key cell
    changes) and three page authors (10 pages each, each given only its
    own briefs). Each session's inputs and its own files-opened
    statement are in the private adjudication file.
  - Isolation slip and recovery: the first batch-1 page author's check
    script read the other 20 pages (numbers only, no page text; no H1,
    key or briefs). Owner ruling: redo batch 1. A fresh page author
    rebuilt `h2-01` to `h2-10` with no directory access; the original
    batch is kept privately as evidence, outside the active pages.
    Batches 2 and 3 unchanged. One-time recovery; the general isolation
    and stop rules are unchanged.
  - Self-check `python -I evals/check_holdout.py <H2>`: "Holdout
    self-check: PASS", exit 0. 30 cases; 14 VIOLATION, 11 COMPLIANT,
    5 NOT_APPLICABLE; per market DEU 10, GBR 10, MLT 10; 296 key cells.
  - Pages-only manifest `evals/v2/holdouts/H2.sha256`: 30 files,
    `--verify-manifest` match, exit 0. SHA-256 of the committed content
    (LF line endings, as Git stores it):
    `abeec2061415c86da5630cc632141fc36dc37d151bd2b8d3a7468a309fdb8286`.
  - Deferred P1b review notes, resolved here:
    - approved gate fingerprint: `evals/eval_config.yaml` at `07d6b95`,
      blob `763d87f4e5835539125f309ae9fbba5af61c245c`, SHA-256
      `1f3bb41e36708a7bfa0d65389f9fadff1b8e170df9f6208b449374de91dabb28`;
    - P1b checkpoint reviews in order: STOP, STOP, OK WITH NOTES, STOP
      (before the commit), then OK WITH NOTES on the committed content
      `07d6b95`;
    - RT1-06 table row in `evals/v2/RED_TEAM_1.md` now reads resolved.
  - Open (owner actions): blind labeling of H2 with another model
    family (packet instructions kept privately with H2); adjudication;
    one offline backup of the H2 folder.

- **2026-11-02**, P-001 P1 (local branch `repair/v2`; gate before
  code; no system code changed, no model run of the system). Owner
  authorized P1 only. Stops at the P1 checkpoint for owner approval.
  - Commit `965d52c` (P1a, before any holdout existed): gate v2
    (`evals/eval_config.yaml` 2.0), `BLUEPRINT.md` §7 amendment (level
    lines, signed exception), `evals/v2/SCENARIO_SPEC.md`,
    `evals/v2/RULESET_V1_1.md` (proposed), `evals/v2/RED_TEAM_1.md`,
    `evals/check_holdout.py` with `tests/test_check_holdout.py`,
    `evals/v2/july_primaries.yaml`, `.gitignore`, and the five deferred
    P0 wording fixes in this file.
  - Red team 1 (fresh session, never opened a holdout, no model run of
    the system): `evals/v2/RED_TEAM_1.md`. After the owner's RT1-06
    ruling: "Findings: 21; changed the build: 1; changed the test: 18;
    no change: 2".
  - H1 authored privately under the scenario spec committed in
    `965d52c` (the spec was not yet approved by the owner). Roles, each
    a fresh Claude context working only in the private folder (outside
    every Git repo): a spec author; three page authors; a spec-author
    second pass (all cells checked against the finished pages, filler
    sweep); and a third pass that relabelled two primaries to
    NOT_APPLICABLE under the v1.0 key's conventions and redesigned two
    cases as COMPLIANT near-misses to keep the frozen mix. Pages and key
    never entered this repo. The second pass found three labelling
    conventions that exist only in the v1.0 key; three more v1.1 notes
    were proposed (July key still unchanged, 0 of 288 cells).
  - H1 self-check `python -I evals/check_holdout.py <H1>`: "Holdout
    self-check: PASS", exit 0. 30 cases; 15 VIOLATION, 10 COMPLIANT,
    5 NOT_APPLICABLE; 384 key cells.
  - Checkpoint review of the staged P1b change: round 1 STOP and round 2
    STOP, both on the late-notes plan deviation. The owner ruled option
    (c): H1 retired to private development material. Its page manifest
    was not committed; it is kept with H1 in the private folder.
  - After the owner's rulings, the P1b change holds: the RT1-06 rule in
    the gate, option (c) recorded as a one-time H1 exception (the
    general retirement rule unchanged), the minor review findings fixed.
    The owner approved the gate, the spec and the v1.1 text on
    2026-11-02; P1b was committed after a fresh checkpoint review.
  - Not done in P1 (later phases, each on its own authorization): H2;
    P2 code; any paid run; the deferred cross-repo incident-register
    entry.

- **2026-11-02**, P-001 P0 (local branch `repair/v2`, docs only, no
  code change, no model run). Owner approved the remediation plan and
  the private-holdout eval-gate exception, and authorized P0 only.
  - Recorded in this file: the one-re-gate cap is superseded (old text
    kept, marked); the repair-program ruling; the eval level (Proposed
    Light, Decided Standard); the exception text; the `ABSENT:`
    constraint; the open owner decisions; the deferred cross-repo
    incident-register entry; the AUTH row P-001 in the Backlog.
  - `evals/EVAL_RESULTS.md`: a dated attribution note appended to the
    July official entry. 6 of the 8 misses trace to the page reader
    dropping `<h1>`/`<h2>`/`<li>` text (`read_page` evidence). The FAIL
    and the entry text are unchanged.
  - Read-only finding: the sibling `ai-claim-verification-agent`
    checkout is at `a17f5f8`, not the pin `d444b13` (D3). Nothing was
    changed there.
  - Evidence:
    - `python .githooks/validate_artifacts.py .` printed "Tier 0: PASS",
      exit 0.
    - Keyless `python -m pytest -q`: 15 passed, exit 0 (unchanged, no
      code touched).
  - Write set: `STATE.md`, `evals/EVAL_RESULTS.md`.

- **2026-09-19** — Owner ruling (adjudication; documentation only, no
  code change): the 2026-07-09 phase-start STATE.md rule is
  **intentionally retired**, closing the open finding raised earlier the
  same day in the Q-72(f) reconciliation entry below (`63a6272`). It was
  a phased-build-era control; this repo is now a completed, public
  artifact, and KOS GOVERNANCE.md's Build-repo STATE rule already
  governs the behaviour it was protecting — clause 5c (read STATE.md
  before writing to the tree) and clause 2 (STATE.md rides the atomic
  close whenever status, decision, blocker, milestone or phase reality
  changes; "No new cadence"). Restoring a repo-specific phase-start
  cadence would duplicate that rather than add a control. Deliberately
  NOT done: no restoration to `AGENTS.md` or `CLAUDE.md`, no ADR, no
  validator, code or test change; no KOS write (build truth belongs to
  this file per the same rule's clause 3 fact boundary, and no KOS
  record referenced the finding). Write set: `STATE.md` only.
- **2026-09-19** — Q-72(f) reconciliation (this commit): this file's
  Change Log stopped at 2026-07-27 and was silent on three later,
  non-docs commits. Recorded now:
  - **2026-08-03** (`1350a51`) — publish-gate coverage canary added
    (`.githooks/.coverage-canary`), same EICAR-style decoy pattern as
    the sibling claim-verification-agent repo.
  - **2026-08-04** (`70736c8`, `canary-resolve-a`) — `.publicgate-allow`
    migrated from a 6-entry, path-plus-pattern-list format to an
    entry-exact format (21 new lines, each citing this dated owner
    ruling) — a real tightening of the publish-gate allowlist
    mechanism, not wording.
  - **2026-08-04** (`ca5d321`, Q-35 hook rollout) — validator's
    decision-record check widened to accept `decisions/` as an
    alternate to `adr/`; pre-commit regex widened for `/c/`-style
    paths; pre-push freshness guard added — same pattern as the
    sibling claim-verification repos' Q-35 commits.
  - **2026-09-15** (`58a8cd7`, Q-93) — canonical AGENTS.md router
    adopted (112-line new `AGENTS.md`). **Flagged, not silently
    fixed:** this commit shrank `CLAUDE.md` from its prior
    phase-discipline block to a thin `@AGENTS.md` pointer, and in
    doing so **dropped the explicit rule this file itself records
    being added on 2026-07-09** ("CLAUDE.md gets a new session rule:
    'Phase start: update STATE.md status to in-progress before any
    phase work' — applied to this session as its own first edit"; see
    the 2026-07-09 Phase 7 entry below). Not restored at the time:
    that was a CLAUDE.md/AGENTS.md-retrofit-quality question, outside
    Q-72(f)'s STATE/validator-convergence scope, so it was recorded as
    an open finding. **Adjudicated the same day** — the rule is
    intentionally retired; see the 2026-09-19 owner-ruling entry above
    and the resolved item under Open decisions.
  Validator (same commit): STATE.md-existence check added (this file
  existed but was never validator-checked); the AGENTS.md v2.7
  heading-check block added (this repo's validator predates that
  requirement — confirmed as the pre-v2.7 pilot copy); the obsolete
  five-record decision cap removed; six-name BANNED_WITHOUT_TRIGGER
  list propagated — safe here, unlike the sibling claim-verification
  repos, because this repo's own `adr/0004-three-actor-answer-key-
  protocol.md` already cites `SPEC.md` (§10.7) as an existing decision
  record, satisfying the citation requirement without fabricating one.

- **2026-07-27** — CI added (contemporaneous): `.github/workflows/
  ci.yml` per the CI workflow standard (CONVENTIONS, github-ops,
  adopted 2026-07-25) — ubuntu/macos/windows × Python 3.12/3.14
  keyless matrix, `permissions: contents: read`, pinned actions
  (checkout@v7, setup-python@v7), no pull_request_target, no cron;
  full pytest suite (FI + bounds + pipeline + sweep, zero LLM calls,
  stub agents only). `requirements.txt` added for the CI install
  path. `.publicgate-allow` rolled out (6 entries, each citing the
  2026-07-26 exposure-KEPT ruling recorded in the private governance
  home); two internal queue-label mentions redacted to date-cited
  wording same session (commit `2df953d` — redaction, not content
  change; history retains originals). First run `30181952956` RED
  2/6 legs (both windows green; ubuntu+macos red): the cage test's
  Windows-style backslash probe is a literal filename on POSIX —
  containment held, rejection wording differed. Fix (owner-ruled,
  diff approved pre-push): commit `d35cddb` ports the sibling
  claim-verification repo's resolver guard (its commit `c3633e6`,
  design decision 2026-07-24) — backslash treated as a path
  separator on every OS; test file unchanged. Local keyless pytest
  15 passed, pytest's own exit 0 (PIPESTATUS-verified). Re-run
  `30222240748` GREEN 6/6 legs. Full repo-publish-gate run per push
  (2 runs so far, both OVERALL PASS, verdict tables in session
  transcript). This entry's own push triggers a further run — its ID
  citable only after this commit exists (same self-citation
  limitation as prior entries).
- **2026-07-20** — Post-flip demo-path verification (stranger clone,
  contemporaneous): `git clone --depth 1` of the public repo into a
  `mktemp -d` temp dir (never the local working copy), read the cloned
  README.md in full, grepped it and every other `.md` file for a
  quickstart/demo command section — **none exists**: README's only two
  fenced blocks are ASCII diagrams, no `requirements.txt`/`pyproject.toml`/
  `setup.py`/`Makefile` at root either. Closed the open gap from the
  prior close as N/A-not-PASS/FAIL (nothing documented to execute, so
  nothing to exit non-zero) rather than rounding it into a false PASS —
  see "Open decisions" above. While checking, found `config.yaml`
  hardcoded a local absolute path (`C:/Users/<user>/GitHub/ai-claim-
  verification-agent`, username de-identified here — verbatim string
  preserved in git history pre-redaction) in the public repo — matches
  repo-publish-gate's own `C:\Users` private-leak pattern, missed by the
  2026-07-14 pre-flip pass. Two new open items logged
  (quickstart-or-explicit-N/A; config.yaml path leak), neither fixed this
  session — remediation approach needs Kristian's call. Temp clone
  removed (`shutil.rmtree` with a read-only-bit
  clear on git's own read-only object files; plain `rm -rf` and
  `ignore_errors=True` both silently left it in place) — verified gone.
  No commit changes source; this entry is the only diff, same close as
  the entry below it.
- **2026-07-20** — Social-preview lane added (contemporaneous):
  `docs/social-preview/orchestrator-flip-post-thumb.png` (1200×627, site
  design system) + `generate_thumbnail.py`, for the LinkedIn
  publication-announcement post. repo-publish-gate items 1 (secrets) and
  2 (private-leak) run against the new content only, not a full-repo
  re-gate — clean: zero hits for `sk-ant|sk-proj|...|AKIA...` and for the
  prior-leak term list `kristian-os|FABLE|Q-[0-9]|C:\Users|Bolt|Paradise`.
  Image copy cross-checked against this file's own recorded numbers
  (P≥0.95/R≥0.90, run `gate-9328e564`) — matches, nothing fabricated.
  Commit `ec8602c`, pushed to `origin/main`, `origin/main..HEAD` empty.
  This entry and the six below (repo flip + five-commit catch-up) written
  same close, per Kristian's explicit instruction this session.
- **[RECONSTRUCTED] 2026-07-20** — Repo-visibility flip confirmed: see
  "Open decisions" above (RESOLVED 2026-07-20) for full detail — both
  this repo and `ai-claim-verification-agent` verified PUBLIC
  unauthenticated; flip itself undated in git history (GitHub Settings,
  not scripted); post-flip fresh-clone demo verification not evidenced,
  left open.
- **[RECONSTRUCTED] 2026-07-14** — commit `2cff5ef`: README diagram
  wording, verifier tools `'read-only'` → `'caged'` (log_finding writes
  its own case log), per pinned SPEC `d444b13c` — second-read finding 11.
- **[RECONSTRUCTED] 2026-07-14** — commit `f4e1fcd`: BLUEPRINT.md
  redaction — a third-party company name replaced with "an external
  hiring process" / "the external-process" in the Branch-Decision and
  Sequencing-Revision notes; decision logic unchanged. Publish-gate
  finding, ruling 2026-07-14; reason recorded in the private governance
  record, not this repo.
- **[RECONSTRUCTED] 2026-07-14** — commit `77a2a0d`: README pre-flip pass
  (repo-publish-gate runbook step 1) — top-of-file FAIL-stated-plainly
  sentence added; `ai-claim-verification-agent` reuse citation linked and
  pinned to commit `d444b13c`; per-jurisdiction gate rows added to the
  results table (DEU 1.000/1.000 PASS, GBR 0.786/0.846 FAIL, MLT
  0.750/0.857 FAIL); four-item Limitations section added (synthetic
  rules, answer-key authorship split, checker/verifier shared-model risk,
  per-jurisdiction gate-math at this dataset size); version log gets v0.9.
- **[RECONSTRUCTED] 2026-07-14** — commit `79d2629`: `adr/0004` dated
  addendum — evidence pointer for the frozen answer key (commits
  `dd155bf`, `0d84bf9`) added at gate-0 verification (2026-07-14,
  private queue record); original ADR
  body unchanged, addendum only.
- **[RECONSTRUCTED] 2026-07-11** — commit `e148846`: CLAUDE.md gets the
  "Session boot and governance" block (governance-home pointer,
  environment-fingerprint pen check, eval/adjudication discipline, close
  ritual, work-source rule) — the block this and every session since has
  booted from, including this one.
- *Catch-up note: this file's Change Log had not been updated for the
  five commits above (2026-07-11 through 2026-07-14) before this
  session — reconstructed from `git log -p` per the same GOVERNANCE.md
  §3 clause 7 pattern used for the Phase 0-4 retrofit below; no
  contemporaneous authority (T5-equivalent) for the six RECONSTRUCTED
  entries above.*

- **2026-07-09** — Phase 7 completion: architecture diagram rebuilt in
  README.md `## System` (ASCII, embedded per ARTIFACT_STANDARD.md's
  "diagram lives inside the README" rule) — now shows every node's
  actual `allowed_tools` whitelist and its NEVER-boundary inline, plus
  the SQLite ledger as its own explicit component every node writes to;
  no internal prompt/reasoning content shown. CLAUDE.md gets a new
  session rule: "Phase start: update STATE.md status to in-progress
  before any phase work" — applied to this session as its own first
  edit, before any other work. Phase 6 FAIL disposition reworded (Kristian,
  this session): FAIL published as an immutable v1.0 record, with an
  optional post-flip remediation loop pre-declared and capped at max
  one re-gate — see Plan and open loops above. ARTIFACT_STANDARD.md
  v2.3's demo-restriction clause (Tier 1 flagship only) pasted verbatim
  in-session per this instruction's item 1; Kristian rules on it after
  seeing it — not resolved here, demo recording not built. pytest
  unaffected (code untouched this phase). This entry is contemporaneous
  with the commit it describes; see `git log -1` at commit time for the
  hash (same self-citation limitation as every entry below marked the
  same way).
- **2026-07-09** — Phase 6: official gate run, `evals/run_eval.py`
  (frozen and committed pre-run, `f3f04fb`) -- full 12-page corpus, 23
  CheckTasks, 184 judged + 104 geo-derived = 288 cells, Sonnet 4.6 for
  checker + verifier + planner. Bounds check PASS. Orchestration
  invariants clean: check 23/23, verify 17/17, plan 32/32 terminal, zero
  dead-letter, zero failed, zero lost. Adjudication: 32/32 CONFIRMED,
  zero rejected, zero disputed -- all 8 misses this run are checker
  misses, not adjudication-layer cost (contrast with the dev leg's one
  DISPUTED-costs-recall case). Scores: pooled TP27/FP5/FN3, precision
  0.844 (< 0.95 min), recall 0.900 (= 0.90 min, clears); NOT_APPLICABLE
  leg 31/34 = 0.912 (PASS); DEU clean (10/0/0), GBR and MLT both fail
  precision and recall. **GATE RESULT: FAIL** on violation_detection
  (precision) -- not_applicable_handling and orchestration_invariants
  both PASS. Not adjusted, not rerun-for-a-better-number. Full
  miss-pattern analysis (5 named patterns, evidence-cited per pattern)
  in `evals/EVAL_RESULTS.md` OFFICIAL section: p09.html's 3 FPs trace to
  the checker judging adjacency against a paragraph other than the one
  actually carrying the offer's terms; p11.html's 2 FNs trace to the
  checker anchoring on the dataset's own designed distractor sentence
  instead of the page's actual violating claim; one FP (p06.html x
  GBR-BT-02) reproduces a "risk-free" vs "free"-item rule-boundary
  confusion the dataset's own P11 brief already documents as deliberate;
  p01.html x GBR-BT-02 (flagged in advance as a standing observation)
  reproduces as a miss on both the Haiku dev leg and this Sonnet
  official leg, with a different specific wrong label each time; p04.html
  x GBR-PC-03 (also flagged in advance) does NOT dispute again -- Sonnet
  confirms it with a cited rationale, where the Haiku dev-leg verifier
  had disputed the same cell. MLT's "zero-miss at 7 violations" baseline
  (on record as accepted, per this session's instruction) does not hold
  this run -- 1 FN + 2 FP, stated plainly, not smoothed over.
  Cost/turns telemetry gap on this run (see open loops above) -- fixed
  in `evals/run_eval.py` same commit, not re-run for telemetry alone.
  pytest: 15 passed, 0 skipped, unaffected. Shipped
  `ai-claim-verification-agent` repo git status clean before and after
  (32 subprocess invocations this run). This entry is contemporaneous
  with the commit it describes; see `git log -1` at commit time for the
  hash (same self-citation limitation as the Phase 5 entry below).
- **2026-07-09** — Phase 5: caged planner agent (`agents/planner/`:
  config, audit, tools [read_finding/read_rule/emit_proposal], prompts,
  harness, select — mirrors the checker's caging pattern; mode-switch
  defaults to stub, Phase 2 pipeline signature and tests untouched) +
  human-gate CLI (`gate/cli.py`: list/approve/reject/disputed,
  idempotent approve/reject via a PENDING-scoped UPDATE). BLUEPRINT.md
  §2 step 5 amended: the planner drafts proposals for CONFIRMED findings
  only (policy §5), not every raw VIOLATION -- amendment line added,
  original retained. `test_planner_cage` unskipped: blindness asserted
  on constructed tool output (no answer-key markers, no sibling
  findings, no checker/verifier transcripts) and self-approval is
  impossible at the API surface -- no approve/reject-shaped tool exists
  in the planner's whitelist at all. pytest: 15 passed, 0 skipped (was
  14/1 -- the last skip, planner cage, is now green; no skips remain).
  Dev leg `plan-dev-05d72b61`: 15/15 CONFIRMED findings from Phase 4's
  `adj-dev-8ad74444` planned over (the 1 DISPUTED finding excluded by
  design), all terminal DONE, zero lost, 15 proposals queued, $0.4118 /
  60 turns. CLI round-trip demonstrated live: approved proposal [1],
  rejected proposal [2], idempotent no-op confirmed re-approving [1] and
  also rejecting the now-APPROVED [1]; `disputed` verified against
  Phase 4's real ESCALATED task (p04.html x GBR), showing both the
  CONFIRMED and the DISPUTED finding with their adjudication citations.
  Full detail: `evals/EVAL_RESULTS.md` Phase 5 leg. This entry is
  contemporaneous with the commit it describes; the commit's own hash
  cannot be self-cited (unlike every entry below, all written after
  their commit existed) -- see `git log -1` at commit time instead.
- **2026-07-09** — STATE.md created per rule-v3 retrofit (GOVERNANCE.md
  §3 clause 7, kristian-os commit 204806a). Contemporaneous.
- **2026-07-09** — Clause-7 deviation logged: Phase 4 closure (commit
  43ff49f) and sweep-permanence work (commit 7a07e01) ran before this
  reconstruction — the working session opened ahead of the retrofit.
  Deviation acknowledged under GOVERNANCE.md §3 clause 7's escape valve
  (one bounded session may proceed with reconstruction as its first
  task); contemporaneous STATE begins at this commit. Contemporaneous.
- **2026-07-09** — [RECONSTRUCTED] Sweep made permanent: full trigger
  pattern committed as `tests/test_sweep.py`; 8 residual hits (page
  titles/nav/elaboration prose, none a real collision, none flipping a
  frozen-key cell) adjudicated into `evals/provenance/SWEEP_ALLOWLIST.md`
  — spec strings in `evals/check_pages.py` unchanged. `SWEEP_REPORT.md`
  now three-tier (historical / live sweep / residuals). pytest: 14
  passed, 1 skipped. Commit `7a07e01`.
- **2026-07-09** — [RECONSTRUCTED] Phase 4 completion: `adr/0004-three-
  actor-answer-key-protocol.md` (Accepted — Executed; spec/key: Claude,
  pages: Claude Code, blind labels: ChatGPT, adjudication: Kristian, per
  `evals/ADJUDICATION_LOG.md`; named residual: pages/key/checkers share
  a model family, blind labeling verifies key correctness only, not
  checker independence) + `evals/provenance/` (PAGE_BRIEFS,
  PAGE_AUTHOR_PROMPT, SWEEP_REPORT, README — reconstructed from
  `evals/INJECTION_SPEC.md` + `evals/ADJUDICATION_LOG.md` + commit
  `fa5d6a1`, no approximation where source was incomplete). Phase 1
  provenance gate cleared — this was the standing decision blocking
  Phase 5. Commit `43ff49f`.
- **2026-07-08** — [RECONSTRUCTED] Phase 4: verifier is a subprocess
  adjudication node over checker VIOLATION findings, not an independent
  4th checker — supersedes BLUEPRINT.md §2 step 3 / §10.3 (amendment
  lines added, original retained; see ADR-0002, Accepted). `policy/
  ADJUDICATION_POLICY.md` pre-committed before any Phase 4 code.
  `AdjudicationRecord` contract + append-only `adjudication_log` ledger
  table. FI-5 unskipped (supersedes BLUEPRINT §6's original wording,
  noted in the test itself); `test_verifier_cage` unskipped (blindness
  bounds on the assembled case). Dev-leg adjudication run `adj-dev-
  8ad74444` (see Eval Numbers). Shipped `ai-claim-verification-agent`
  repo run byte-literal unchanged, pinned commit
  `d444b13c3ba07b9f4798d3298ec3bfc92da5a960`; its git working tree
  verified clean before and after every invocation. pytest at close: 13
  passed, 1 skipped. Commits `30c7618`..`89784ba` (policy, contracts,
  nodes, tests, verifier fix + dev-leg, docs/ADR-0002).
- **2026-07-08** — [RECONSTRUCTED] Phase 3 close: real caged checker
  agent (Haiku 4.5 dev routing) replaces its Phase 2 stub. Dev run
  `dev-27b9e6bf` (see Eval Numbers) — 12/12 CheckTasks terminal DONE,
  zero lost tasks, bounds check PASS (no answer-key marker in any
  audit.db tool payload). Commits `75f4bf3`, `126568c`.
- **2026-07-08** — [RECONSTRUCTED] Phase 2: orchestrator core (ledger,
  state machine, resume-from-ledger), intake, aggregation, end-to-end on
  stub agents — FI-1..4/6/7 green, zero LLM calls this phase. Commit
  `e24d9be`.
- **2026-07-08** — [RECONSTRUCTED] Phase 1b-ii: frozen answer key (30
  violations, three-actor protocol per ADR-0004) — 288/288 cells
  labeled, 97.6% blind-label agreement, 7 disagreements adjudicated
  (D1-D7, `evals/ADJUDICATION_LOG.md`); D2 record corrected same day.
  Commits `dd155bf`, `0d84bf9`.
- **2026-07-08** — [RECONSTRUCTED] Phase 1b-i: 3 jurisdiction rule sets
  + 12 seeded pages per `evals/INJECTION_SPEC.md`. Pre-blind filler
  sweep caught one unintended trigger (P12 free-bet/deposit collision);
  fixed before the blind pass began; SPEC.md §10.7 (answer-key
  authorship split) resolved same commit. Commits `3124c1e`, `fa5d6a1`.
- **2026-07-07** — [RECONSTRUCTED] Phase 1a: contracts, ledger schema,
  eval config, FI test skeletons — authorship-independent; Phase 1b
  blocked on §10.7 until resolved. Commit `e78f3c0`.
- **2026-07-07** — [RECONSTRUCTED] Phase 0: repo scaffold, SPEC.md,
  CLAUDE.md, ADR-0001/ADR-0003, per BLUEPRINT.md v1.1. Commit `a12fddd`.

## Backlog (KOS unit records; Target KOS 06 §D, GOVERNANCE §9)

Rows are read by the KOS computed view (`python core/kos_core.py index
--view` in kristian-os). An AUTH row authorizes B1 work on this unit and
is owner-written (program stage U-02 lands the first one); DRAFT rows are
proposals; DONE rows keep history. The `- STATUS:` line at the top of
this file is the unit status the view renders (ACTIVE | BLOCKED |
DORMANT).

| ID | Auth | Title | Date |
|---|---|---|---|
| P-001 | AUTH | Repair program: defects D1-D10 and Standard gate v2 re-evaluation, local branch repair/v2, phase by phase on owner authorization | 2026-11-02 |
