# STATE — ai-compliance-orchestrator

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
day): FAIL published as an immutable v1.0 record.** An optional
post-flip remediation loop is pre-declared — capped at max one re-gate,
never open-ended iteration. Not adjusted now, and the pre-declared cap
means it cannot become rerun-until-pretty later either; BLUEPRINT §9
Phase 6 acceptance ("GATE GREEN or honest FAIL with miss-pattern
analysis committed") is met by the FAIL-with-analysis branch. "Post-flip"
ties any remediation to after the repo-visibility flip (a separate,
still-open decision, see below) — this v1.0 record does not change
before then. Phase 7 (README/diagram/demo) now in progress —
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
  (2026-07-14, last pre-flip commit) and today. **Gap, stated plainly:**
  repo-publish-gate's post-flip step 2 also calls for running the
  README's stated demo path from a fresh unauthenticated clone (exit 0
  required) — no evidence of that run exists in either repo's history;
  not performed this session either, so not closed by this entry.
  Originally recorded here: both repos PRIVATE as of commit 43ff49f, the
  reuse claim unverifiable until both flipped, repo-visibility flip
  tracked as a separate cross-domain decision requiring the
  repo-publish-gate skill first — that skill ran (see Change Log,
  2026-07-14 entries) before the flip.
- **Demo recording (BLUEPRINT §9/§11) — Kristian rules after seeing the
  cited clause, not resolved this session.** ARTIFACT_STANDARD.md v2.3
  (kristian-os, `LAST UPDATED: 2026-07-09`) cuts `DEMO_SCRIPT.md` (and,
  by the same cut-list rationale, demo material generally) to the
  Tier-1 flagship only — currently `ai-reliability-engine`, not this
  repo. Verbatim clause pasted in this session's report. Until ruled on,
  no demo recording is built and BLUEPRINT §11's fourth stop condition
  stays open on that basis, not by oversight.
- **Post-flip re-gate, pre-declared and capped:** if remediation happens
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
  `dd155bf`, `0d84bf9`) added at gate-0 verification (Q-24); original ADR
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
