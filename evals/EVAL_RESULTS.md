# EVAL_RESULTS

## Latest official result

**November 5, 2026: gate v2.1 PASS.** Official series
`H2-2026-11-05-a7871a` on claude-sonnet-5-5: 30 synthetic compliance scenarios
from private holdout H2, 3 runs each. Each scenario is scored as one case.

| Measure | Result | Gate limit |
|---|---|---|
| Scenarios passed in all 3 runs | 29 of 30 | at most 2 may fail |
| Component A deterministic checks | 52 of 52 | all must pass |
| Unclean pages | 0 of 30 | at most 6 |

One scenario failed on evidence overlap. In `h2-22` (`DEU-PC-03`) the violation
was found and CONFIRMED in all 3 runs, but the evidence excerpt did not
overlap the key's core span (NO_OVERLAP). The cause was not examined.

Limitations:

- This is one series on one holdout. Pages and rule sets are synthetic, and
  no legal accuracy is claimed.
- Under the predeclared binomial calculation, the result supports a pass rate
  of at least 80% (one-sided 95%) for scenarios drawn under
  `evals/v2/SCENARIO_SPEC.md`, if those scenarios are a representative random
  sample. The 30 scenarios are a deliberately balanced, purpose-authored
  synthetic set, which does not establish representative random sampling.
- The result does not show 30 of 30 cases, perfect accuracy, production
  readiness, legal compliance or whole-page screening.
- Holdout pages and keys are private, so this result cannot be recomputed from
  a public clone.

The July 2026 gate v1.0 FAIL (`gate-9328e564`) remains below as historical
evidence, with its original findings. It used a different gate, test set, rule
text and model, so the two results are not directly comparable.

## OFFICIAL: gate v2.1 series (claude-sonnet-5-5, private holdout H2)

### 2026-11-05: series H2-2026-11-05-a7871a

Sanitized results, with per-case and per-page detail:
`evals/results/H2-2026-11-05-a7871a.json` (fields limited by
`sanitized_results_allowlist` in `evals/eval_config.yaml`). Its SHA-256 as
Git stores it (LF) is
`788f79f1b67c09d922b8100b56c2d5152b6de06da1d7375c5dd93871d31fb9fc`. Holdout
pages and keys are private and are not in this repository
(`evals/v2/SCENARIO_SPEC.md` §7), so this result cannot be recomputed from a
public clone.

| Item | Value |
|---|---|
| Result | **PASS**, runner exit 0 |
| Series window | 2026-11-05, 00:43:55 to 01:51:39 local, one series, no retry |
| Commit | `91105caeb7178f744cbc91c5a1ea04bb33e672a0` |
| Gate | v2.1, `evals/eval_config.yaml`, SHA-256 (LF) `e2b16c2a005911846ba834b00605c737e315110ebe958b9ff3b84f2d6764de24` |
| Dataset | holdout H2, 30 cases (10 DEU, 10 GBR, 10 MLT), 3 runs each; manifest `evals/v2/holdouts/H2.sha256`, SHA-256 (LF) `c72c3b565b5ccc9f76ef121446ae0f0088593beb609615b447d02f92251ccd13` |
| Ruleset | v1.1; file hashes in the results file, equal to `evals/eval_config.yaml` |
| Model | claude-sonnet-5-5: checker, verifier and planner |
| Verifier pin | `d444b13c3ba07b9f4798d3298ec3bfc92da5a960` |
| Earlier official series under gate v2 | 0 |

#### Gate result

| Gate item | Result | Limit | Outcome |
|---|---|---|---|
| Component A checks | 52 of 52 passed | 100% | PASS |
| Valid cases | 30 | at least 30 | PASS |
| Failing cases | 1 (29 of 30 passed in all 3 runs) | at most 2 | PASS |
| Unclean pages | 0 of 30 | at most 6 | PASS |
| **GATE** | | | **PASS** |

Component A: 4 checks on the frozen commit (A1 keyless suite, 3 A3 reader
checks) and 16 checks in each of the 3 runs (A2). The results file holds 6
more rows, diagnostic counts with no pass or fail value; all are 0.

#### Failed case and miss analysis

| Case | Market | Rule | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|---|
| `h2-22` | DEU | `DEU-PC-03` | NO_OVERLAP | NO_OVERLAP | NO_OVERLAP |

The same miss in all 3 runs: the violation was found and CONFIRMED, but the
evidence excerpt did not overlap the key's core span, so the case failed
evidence grading. The cause was not examined. No holdout content was opened
for this record. Any later page-level analysis treats H2 as development data.

#### Diagnostics (recorded, not gated; cells clustered by page, no binomial claim)

| Measure | Value |
|---|---|
| TP / FP / FN | 42 / 0 / 0, pooled over all cells and all 3 runs |
| Precision / recall | 1.000 / 1.000 |
| Adjudication | 42 CONFIRMED, 0 REJECTED, 0 DISPUTED |
| NOT_APPLICABLE accuracy | 0.9804 |
| Flips between runs | 4 cells, all COMPLIANT vs NOT_APPLICABLE (derived: every cell was decided, and FP, FN, REJECTED and DISPUTED are all 0) |
| One-off off-target errors | 0 |
| Failed tasks | check 0, verify 0, plan 0 |

Precision and recall count assertions only; they do not grade evidence. The
3 `h2-22` misses count as TP here, so recall 1.000 does not mean every case
passed. The gated number is the case result above.

#### Execution and isolation

- Sessions: 195 model sessions, 65 per run (37 checker, 14 verifier, 14
  planner per run). All served claude-sonnet-5-5, 0 API errors. Runner
  stderr empty.
- Machine-policy record hook: no refusal line appears in the runner output.
  This is not a separately measured zero: the runner prints a line only when
  it counts at least one refusal, and it saves no count. An unrecovered
  refusal would have made the series INVALID RUN, and it did not. No INVALID
  RUN condition applied.
- Login: subscription (claude.ai, first party). No other Claude process ran
  at series start.
- Frozen inputs: commit, gate, ruleset and manifest hashes in the results
  file match the commit. Repository clean at series start; the only Git-visible
  change after the series is the results file (2 ignored `tests/__pycache__`
  files also changed).
- Holdouts: H1 and H2, 77 files, fingerprint `073bc869600b761d` before and
  after the series and again on 2026-11-05 at recording. H2 matches its
  committed manifest.
- Verifier clone at the pin; Git status unchanged, and no change apart from
  any ignored `__pycache__` files. `verifier_cases` empty after each run.
  Transcripts stayed in the three transcript folders named for the runs. Hook
  records changed only in the no-repository record file and its index file.
- Exposure: no holdout page, key, brief, adjudication file or transcript is
  tracked or in Git history (309 blobs compared with the manifest hashes,
  0 matches; no such path in history). The results file has only allowlisted
  fields.

#### Cost and time

- Cost: 13.9717 USD, notional, as the CLI reports it. The CLI has no price
  entry for this model and may use a fallback rate, so this is not a measured
  charge. The series ran on a subscription login.
- Turns: 1,620.
- Wall clock: 3963.3 s, the sum of the 3 runs; about 4,064 s for the whole
  series with A1 and A3.

#### Changed variables and newly broken cases

Against the previous official entry (`gate-9328e564`): gate v1.0 to v2.1
(case pass rate, 3 runs per case); July pages to private holdout H2; ruleset
text to v1.1; model claude-sonnet-4-6 to claude-sonnet-5-5; repairs D1 to D9
and the D10 development changes (`STATE.md`). The two results are not like
for like, and the July v1.0 FAIL stands under its own gate.

Newly broken cases: not applicable. This is the first series on H2.

#### What this result supports

Frozen claim (`public_claim_wording`, N = 29, k = 0):

> 29 of 30 separately briefed synthetic compliance scenarios (at most 2
> failed) got their predeclared decision right in all 3 runs, with evidence
> checked for text violations. This supports a pass rate of at least 80%
> (one-sided 95%) for scenarios drawn under this spec. At most 6 of 30 pages
> showed a repeated material error on another cell (wrong in at least 2 of 3
> runs), and all deterministic reliability and planner-integrity checks
> passed. Earlier official series: 0, all recorded.

Observed unclean pages: 0. "Earlier official series" counts gate v2 only.

This result does not show 30 of 30 cases, perfect accuracy, production
readiness, legal compliance, legal accuracy or whole-page screening.

Limits:

- One series on one holdout. Pages and rule sets are synthetic.
- The holdout was authored for this spec, so the claim covers scenarios drawn
  under it, not real marketing pages.
- The agent sessions probably received the startup text of a machine-level
  session hook outside this repository, as in the development trial
  (inference, not measured).
- H2 is retired under `result_rules.holdout_retirement` and is now local
  development data. A later version needs a fresh holdout.

## Historical record: July 2026, gate v1.0 (FAIL)

*Dated runs per BLUEPRINT §7: cost + turns recorded per run. The official
gate run (Sonnet 4.6, full 12-page corpus, thresholds enforced) is recorded
below as the OFFICIAL section (Phase 6, 2026-07-09) — result: **FAIL**
(violation-detection precision). Gates were not adjusted; the dev-leg
sections further below remain leg reports, not gate results.*

## OFFICIAL — Phase 6 gate run (Sonnet 4.6, full 12-page corpus)

### 2026-07-09 — run_id gate-9328e564

Full dataset: 12 pages, all targeted jurisdictions, 23 CheckTasks, 184
judged cells (checker) + 104 geo-derived cells (intake never asks —
correctly NOT_APPLICABLE by construction, SPEC.md Phase 2 ruling) = 288
cells scored, per `evals/run_eval.py` (frozen and committed at `f3f04fb`,
before this run — commit hash below).

- Model: **claude-sonnet-4-6**, checker + verifier (subprocess adjudicator)
  + planner. Planner included so the run produces the complete artifact;
  proposals are not scored (BLUEPRINT.md §2 step 6, this instruction).
- Scorer semantics frozen pre-run (commit `f3f04fb`): (a) assertions =
  CONFIRMED findings only, policy §5 — rejected-true and disputed-true both
  score FN; (b) full 288-cell accounting (184 judged + 104 geo-derived);
  (c) NOT_APPLICABLE leg measured over rule-level N/A cells only; (d)
  pooled AND per-jurisdiction PASS/FAIL, mechanical, against
  `evals/eval_config.yaml`'s committed thresholds.
- Bounds check: **PASS** — no `answer_key.yaml` marker in any audit.db tool
  payload for this run.

#### Orchestration invariants

| Stage | Terminal | Dead-letter | Failed | Zero lost |
|---|---|---|---|---|
| check | 23/23 | 0 | 0 | yes |
| verify | 17/17 | 0 | 0 | yes |
| plan | 32/32 | 0 | 0 | yes |

All tasks reached a terminal state across all three stages. 32 VIOLATION
findings emitted by the checker; all 32 adjudicated; all 32 CONFIRMED
findings drafted a proposal. Idempotent re-run is a structural property
proven by the FI-6 unit test (`test_fi6_idempotent_rerun`), not re-run live
against this specific expensive official leg.

#### Violation detection — pooled and per jurisdiction

| Jurisdiction | TP | FP | FN | Precision | Recall | PASS (≥0.95 / ≥0.90) |
|---|---|---|---|---|---|---|
| DEU | 10 | 0 | 0 | 1.000 | 1.000 | **PASS** |
| GBR | 11 | 3 | 2 | 0.786 | 0.846 | **FAIL** |
| MLT | 6 | 2 | 1 | 0.750 | 0.857 | **FAIL** |
| **POOLED** | **27** | **5** | **3** | **0.844** | **0.900** | **FAIL** |

Threshold: precision ≥ 0.95 AND recall ≥ 0.90, pooled AND every
jurisdiction (`eval_config.yaml`). Pooled recall clears the bar exactly
(0.900); pooled precision does not (0.844 vs 0.95). **violation_detection:
FAIL.**

#### NOT_APPLICABLE leg (rule-level N/A cells only — the 104 geo-derived
cells are excluded from this leg per this instruction's semantics (c); they
are always correct by construction and are reported as a coverage fact
below, not a measured leg)

| Correct | Total | Accuracy | Threshold | Result |
|---|---|---|---|---|
| 31 | 34 | 0.912 | ≥ 0.90 | **PASS** |

Coverage fact: 104/104 geo-derived cells correctly NOT_APPLICABLE by
construction (no CheckTask, no finding, no assertion possible) — not part
of the 34-cell denominator above.

#### Adjudication table

| Verdict | Count | Detail |
|---|---|---|
| CONFIRMED | 32 | all 32 VIOLATION findings confirmed — zero rejected, zero disputed this run |
| REJECTED | 0 | rejected-correct: 0 · rejected-wrong: 0 |
| DISPUTED | 0 | 0 |

Every VIOLATION finding the checker emitted was adjudicated CONFIRMED. The
adjudication layer added no precision protection this run (nothing was
rejected) and cost no recall (nothing was disputed) — unlike the dev leg
(1 DISPUTED), the official run's 5 FPs and 3 FNs are **entirely checker
misses**, not adjudication-layer costs. See miss-pattern analysis below.

#### Cost + turns

**Not captured for this run — logged as a defect, not a rerun trigger.**
`evals/run_eval.py`'s pipeline runner did not wrap the checker stage to
accumulate `agents.checker.harness.last_result` across all 23 tasks (it
only ever held the *most recent* call), and the verifier/planner stages'
own `run_stats` accumulators (`nodes.verifier.run_stats`,
`agents.planner.harness.run_stats`) were populated correctly during the
run but never read before the driving process exited — so that in-memory
data is unrecoverable after the fact. This did not abort the run (BLUEPRINT
§9 Phase 6 acceptance requires a harness defect to *abort* before a rerun
is warranted; this one didn't — the run completed cleanly end to end with
fully valid scoring data) and it does not affect precision/recall/PASS-FAIL
in any way, so per this instruction's own rule ("the numbers look wrong is
never a harness defect... no rerun-until-pretty") a second ~$15-30, ~50
minute Sonnet run solely to re-capture telemetry was judged not warranted.
Fixed in `evals/run_eval.py` (commit after this entry) for every future
run. Wall clock is known: check 915s, verify 1372s, plan 802s, total 3088s
(~51.5 min). A weak proxy: `audit.db` recorded 652 tool-call rows (326
Pre/Post pairs) across 55 checker+planner task_ids for this run_id — this
is not equivalent to the SDK's own turns/cost metric and is reported only
as a rough activity signal, not a substitute.

#### GATE RESULT: **FAIL**

| Leg | Result |
|---|---|
| violation_detection | **FAIL** (pooled precision 0.844 < 0.95; GBR and MLT both fail precision and recall) |
| not_applicable_handling | PASS (0.912 ≥ 0.90) |
| orchestration_invariants | PASS (all terminal, zero lost, zero dead-letter, FI-1..7 green) |
| **GATE** | **FAIL** — any leg failing fails the gate (`eval_config.yaml`: "GATE GREEN iff ... all pass") |

Gates were not adjusted to produce this result and will not be adjusted
after it. This is the honest result of the official run.

#### Miss-pattern analysis (required — gate FAILED)

8 total misses (5 FP, 3 FN), zero in DEU, all in MLT/GBR. Every miss is a
**checker** miss (the adjudicator confirmed all 32 VIOLATION calls it was
given, correctly or not) — this run puts the precision problem squarely on
detection, not adjudication.

**Pattern 1 — wrong-paragraph anchoring, 3 of 8 misses, all one page
(p09.html, FP x3: MLT-BT-01, MLT-BT-03, GBR-BT-01).** p09's offer states
its full terms adjacent, in the `<h2>` heading directly under the offer
title: "50% up to €100, 20x wagering, min deposit €10, valid 7 days" — this
satisfies BT-01/BT-03's adjacency requirement per the frozen key (all three
cells are COMPLIANT). The checker's evidence excerpts for all three wrong
VIOLATION calls instead quote a *different*, lower paragraph — a prose
restatement of the same offer with no numeric terms ("Reload your account
and get an extra 50% on top, credited instantly to your bonus balance once
your qualifying deposit clears") or the generic "how it works" section —
and judged adjacency against that sentence in isolation, missing that the
`<h2>` heading two lines above already carries the complete terms for the
same offer. Half of this run's non-DEU false positives come from this one
page, on what reads as a single underlying failure mode reproduced across
three separate rule checks.

**Pattern 2 — distractor anchoring, 2 of 8 misses, one page (p11.html, FN
x2: MLT-PC-01, GBR-PC-01).** p11's actual violating claim is in the page's
own `<h1>`: "Risk-Free Week: play casino all week, lose nothing — we
refund net losses up to €50." — exactly the trigger text
`evals/provenance/PAGE_BRIEFS.md` specifies for both rules. The checker's
evidence excerpt for both wrong COMPLIANT calls instead quotes "Refund
paid as withdrawable cash. No wagering is required..." — which
`evals/provenance/PAGE_BRIEFS.md`'s own P11 brief names explicitly as
the page's **deliberate distractor** ("benign factual term"). The checker
walked past the actual violating claim and anchored its judgment on the
dataset's own designed decoy, on both jurisdiction checks for the same
page.

**Pattern 3 — "risk-free" / "free"-item rule-boundary confusion, 1 FP
(p06.html x GBR-BT-02) plus contributing to Pattern 2's blind spot.**
GBR-BT-02 governs items explicitly labelled "free" that turn out to
require a deposit; "risk-free" wording is a different claim (a risk/PC
matter), and `evals/provenance/PAGE_BRIEFS.md`'s own P11 brief documents
this exact boundary as a deliberate, adjudicated design choice ("GBR-BT-02
governs items described as 'free'; 'Risk-Free' is a risk claim, not a
free-item claim"). At p06, the checker applied BT-02 to "Risk-free first
bet — refund if you lose" anyway, reasoning the "risk-free" framing was
"misleading given the deposit requirement" — collapsing the same
BT-vs-PC boundary the dataset was built to test. This is a rule-semantics
gap, not a reading-comprehension one like Patterns 1-2.

**Pattern 4 — p01.html x GBR-BT-02 reproduces across both model
generations (FN).** Flagged in advance as a standing observation (this
instruction, item 4) — it reproduces. Dev leg (Haiku, `dev-27b9e6bf`):
checker verdict COMPLIANT. Official leg (Sonnet, this run): checker
verdict **NOT_APPLICABLE** — a different wrong label, same missed cell.
The page's violating pattern is "50 Free Spins" (contains the qualifying
word "Free") paired with "Spins credited after first deposit" in a
different sentence; this run's evidence excerpt ("boost your first
deposit") and rationale ("never described as 'free'... no 'free' claim is
present") show the checker read the deposit-contingency sentence but did
not connect it to "Free Spins" stated elsewhere on the same page — the
same disconnected-sentence failure shape as Pattern 1, on a cell that has
now missed on two different model generations.

**Pattern 5 — p10.html x GBR-PC-02 (FP), likely over-generalized
urgency-detection.** The checker flagged "it's worth placing it early
rather than letting it sit in your account" as urgency-pressure wording.
The dataset's actual PC-02 trigger elsewhere (p09.html: "Last chance —
bonus ends in 02:14:33!") is a much more explicit countdown/urgency claim;
p10's phrasing is a soft, generic expiry reminder. Read as the rule being
applied more broadly than the dataset's design intends, not a
comprehension failure.

**Per-jurisdiction quantization, on record:** MLT's key carries 7
violations pooled across the full corpus (tp=6 + fn=1 this run). A
zero-miss MLT result at n=7 is on record as an accepted baseline (per this
session's instruction). This run does not hold that line — MLT shows 1 FN
(p11 x MLT-PC-01, Pattern 2) and, more materially, 2 FP (p09,
Pattern 1) that were not part of the prior baseline's scope at all. At
n=7, a single miss moves recall by ~14 points (0.857 here) — the smallness
of MLT's denominator means this jurisdiction's leg is genuinely
high-variance per-miss, which the pooled table's 27/5/3 obscures; this is
stated plainly, not smoothed into the pooled number.

**What is not a pattern:** DEU shows zero misses (tp=10, fp=0, fn=0) —
the same jurisdiction that also cleared cleanly in every prior dev leg.
Nothing here suggests DEU's rules are easier in any structural sense
already documented; it is reported as a clean leg, not investigated
further, since there is nothing to explain.

#### Standing observations (this instruction, item 4)

- **p01.html × GBR-BT-02 (the Haiku dev-leg miss): reproduces.** Confirmed
  above as Pattern 4 — still a miss on Sonnet, official, full corpus.
  Different specific wrong verdict (NOT_APPLICABLE here vs. COMPLIANT on
  the Haiku dev leg), same missed cell, same underlying disconnected-
  sentence failure shape.
- **p04.html × GBR-PC-03 (the dev-leg DISPUTED finding): does NOT dispute
  again.** Checker verdict VIOLATION (same as the dev leg); this run's
  Sonnet adjudicator returned **CONFIRMED**, with a specific, cited
  rationale ("a named cartoon wizard character... 'students'... primary
  appeal to under-18s, satisfying the violation threshold under
  GBR-PC-03") — not the dev leg's Haiku-verifier "sources don't resolve
  the judgment call" hedge. This cell scores as a correct TP in this run
  (key: VIOLATION), not the honest-insurance FN the dev leg reported. The
  adjudication layer's earlier "n=0 insurance" framing (policy §15) now has
  a second data point in the opposite direction: on this cell, a stronger
  model resolved the same judgment call the dev-leg model could not.

#### 2026-11-02 — Attribution note on gate-9328e564 (appended; the entry above is unchanged)

No rerun. Scores, thresholds and the **FAIL** result above stand as recorded.
This note corrects only the cause given for Patterns 1, 2 and 4 in the
miss-pattern analysis.

The checker's page reader (`agents/checker/pages.py`, `_ParagraphExtractor`)
returns only `<title>` and `<p>` text. All `<h1>`, `<h2>` and `<li>` content is
dropped, both for the checker (`fetch_page`) and for the verifier's assembled
case (`nodes/assembler.py`, which calls the same `read_page`). Checked on
2026-11-02 by calling `read_page` on the frozen pages (no model run):

| Page | Text in a dropped element | Visible to checker and verifier |
|---|---|---|
| p09.html | `<h2>`: "50% up to €100, 20x wagering, min deposit €10, valid 7 days" | no |
| p11.html | `<h1>`: "Risk-Free Week: play casino all week, lose nothing ..." | no |
| p01.html | `<h2>`: "100% up to €200 + 50 Free Spins" | no |

So:

- **Pattern 1** (p09, 3 FP): the checker could not see the heading that
  carries the full terms. The cause is the reader, not wrong-paragraph
  anchoring.
- **Pattern 2** (p11, 2 FN): the violating claim was not in the text the
  checker received. Only the distractor was left. The cause is the reader,
  not distractor anchoring.
- **Pattern 4** (p01 x GBR-BT-02, FN): "Free Spins" was not in the text the
  checker received. The cause is the reader, not a failure to connect
  sentences.

6 of the 8 official misses trace to the reader. Patterns 3 and 5 (p06, p10)
are unaffected by it and stay as written. The adjudication table also needs
this context: the verifier judged the same truncated page text, so its 32/32
CONFIRMED does not show what it would do with the full page.

The repair is planned in the 2026-11-02 repair program (STATE.md, P-001),
under a new gate. It does not change this v1.0 record.

## Dev runs (Phase 3 leg — Haiku 4.5, no thresholds enforced)

### 2026-07-08 — run_id dev-27b9e6bf

First run of the real checker agent (Phase 3 acceptance run).

- Model: claude-haiku-4-5-20251001 (dev routing; Max plan auth, no per-token API key)
- Pages: p01–p06 → 12 CheckTasks (page × targeted jurisdiction), 8 rules each,
  all three jurisdictions covered (MLT ×5, GBR ×4, DEU ×3)
- Terminal states: **12/12 DONE** — zero lost tasks, zero FAILED/DEAD_LETTER
- Bounds check: PASS — no answer_key.yaml marker in any audit.db tool payload
  for this run (key scored harness-side only)
- Findings scored: 96/96 (0 unscored)

| Jurisdiction | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| DEU | 6 | 0 | 0 | 1.000 | 1.000 |
| GBR | 6 | 0 | 1 | 1.000 | 0.857 |
| MLT | 4 | 0 | 0 | 1.000 | 1.000 |
| **POOLED** | **16** | **0** | **1** | **1.000** | **0.941** |

- Cost: **$0.6905** total ($0.058/task avg) · Turns: **132** total (11.0/task avg)
- Wall clock: 447 s
- Miss: 1 FN — p01.html × GBR-BT-02 judged COMPLIANT (key: VIOLATION); GBR recall
  0.857 on n=7. Dev-leg observation only; miss-pattern analysis is owed at
  Phase 6 if it reproduces on the gate model.

Acceptance read (BLUEPRINT §9 Phase 3): leg runs clean — all tasks terminal,
plausible numbers. Green means the leg runs, not that gate thresholds are met.

## Phase 4 leg — adjudication (Haiku 4.5 verifier, dev routing)

### 2026-07-08 — run_id adj-dev-8ad74444

Adjudicates all 16 VIOLATION findings from the Phase 3 dev run (dev-27b9e6bf)
through the shipped ai-claim-verification-agent, run byte-literal unchanged as
a subprocess (nodes/verifier.py, pinned commit `d444b13c3ba07b9f4798d3298ec3bfc92da5a960`),
per policy/ADJUDICATION_POLICY.md.

- Model: claude-haiku-4-5-20251001 (dev routing; Max plan auth, no per-token API key)
- Findings adjudicated: 16/16 — 15 tasks terminal DONE, 1 task terminal ESCALATED
  (policy §11: rejected-only/all-confirmed → DONE, any DISPUTED → ESCALATED)
- Shipped-repo integrity: `git -C ai-claim-verification-agent status` clean
  before this run and clean after (only the pre-existing, unrelated untracked
  `evals/results/` — no case directory left behind; every case removed in
  `nodes/verifier.py`'s `finally` block)

| Verdict | Count | Detail |
|---|---|---|
| CONFIRMED | 15 | all 15 cite the bright-line criterion + page evidence (policy §3) |
| REJECTED | 0 | rejected-correct: 0 · rejected-wrong: 0 — nothing to reject on an FP=0 dataset |
| DISPUTED | 1 | p04.html × GBR-PC-03 — verifier: sources confirm the evidence text exists and cite the rule, but neither source resolves the judgment call ("primary appeal to under-18s"); an honest DISPUTED, not a verifier failure |

**Fallback trigger (policy §13) evaluated:** does **NOT** fire. Condition 1
("wrongly rejects >1 true finding") requires REJECTED findings; there are
zero. Condition 2 (REJECTED citations failing the §3 burden) is vacuous for
the same reason. The shipped agent stays as the adjudicator — no purpose-built
replacement is warranted by this leg.

**Recall cost, stated plainly (not hidden in the "insurance" framing):**
adjudication does not just sit idle here. Scoring only CONFIRMED findings as
assertions (policy §5) turns the one DISPUTED finding into an FN, on top of
the original checker miss (p01.html × GBR-BT-02) — both are genuine true
violations the *checker* found correctly. Pooled, under adjudication:

| | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| Pre-adjudication (checker only, dev-27b9e6bf) | 16 | 0 | 1 | 1.000 | 0.941 |
| Post-adjudication (CONFIRMED-only assertions) | 15 | 0 | 2 | 1.000 | 0.882 |

Precision is unaffected (there was no FP for the verifier to catch — the §15
expectation note holds). Recall drops 0.941 → 0.882: the one DISPUTED finding
is a real cost of this design on this dataset, not merely inert insurance.
This is the honest reading of policy §5's "disputed-true = FN" rule, recorded
here rather than smoothed over.

- Cost: **$0.6790** total ($0.042/finding avg) · Turns: **124** total (7.75/finding avg)
- Wall clock: 629 s

Acceptance read (BLUEPRINT §9 Phase 4): leg runs clean — all 16 findings
adjudicated, terminal states correct, fallback trigger evaluated and did not
fire. Not a gate result (Phase 6 is Sonnet 4.6, full corpus, thresholds
enforced).

## Phase 5 leg — planner (Haiku 4.5, dev routing)

### 2026-07-09 — run_id plan-dev-05d72b61

Drafts a RemediationProposal for each CONFIRMED finding from the Phase 4
dev leg (`adj-dev-8ad74444`) — 15 of the 16 adjudicated findings; the 1
DISPUTED finding (p04.html × GBR-PC-03) is excluded by design (policy §5:
the planner drafts only for the system's assertions, per BLUEPRINT.md §2
step 5's Phase 5 amendment). Real caged planner agent
(`agents/planner/harness.py`), tool whitelist exactly `read_finding`,
`read_rule`, `emit_proposal`.

- Model: claude-haiku-4-5-20251001 (dev routing; Max plan auth, no per-token API key)
- Findings planned over: **15/15** — all terminal DONE, zero lost, zero
  FAILED/DEAD_LETTER
- Proposals in queue: **15** (one per finding; none declined)
- Cost: **$0.4118** total ($0.027/finding avg) · Turns: **60** total (4.0/finding avg)
- Wall clock: 314 s

CLI round-trip (`gate/cli.py`, against this leg's db): approved proposal
`[1]` (p01.html × GBR-GE-01), rejected proposal `[2]` (p02.html ×
DEU-GE-01) — both single-write UPDATEs confirmed via `list --status`.
Idempotency confirmed both ways: re-approving `[1]` after it was already
APPROVED is a no-op ("already APPROVED"), and rejecting an already-
APPROVED proposal is also a no-op, not an overwrite. `disputed` command
verified against Phase 4's real ESCALATED task (p04.html × GBR): shows
both artifacts per finding — the CONFIRMED GBR-RG-01 finding and the
DISPUTED GBR-PC-03 finding, each with its adjudication citation,
never auto-resolved.

Acceptance read (BLUEPRINT §9 Phase 5): proposal queue populated from a
real run (15/15), all tasks terminal, zero lost; approve/reject
round-trip shown in the ledger via the CLI. Not a gate result.
