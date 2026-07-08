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
