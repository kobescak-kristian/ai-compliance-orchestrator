# EVAL_RESULTS

*Dated runs per BLUEPRINT §7: cost + turns recorded per run. The official
gate run (Sonnet 4.6, full 12-page corpus, thresholds enforced) is recorded
below as the OFFICIAL section (Phase 6, 2026-07-09) — result: **FAIL**
(violation-detection precision). Gates were not adjusted; the dev-leg
sections above remain leg reports, not gate results.*

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
