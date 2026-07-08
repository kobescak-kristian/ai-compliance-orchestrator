# EVAL_RESULTS

*Dated runs per BLUEPRINT §7: cost + turns recorded per run. The official
gate run (Sonnet 4.6, full 12-page corpus, thresholds enforced) is Phase 6
and does not exist yet — nothing below is a gate result.*

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
