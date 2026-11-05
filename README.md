# ai-compliance-orchestrator

[![CI](https://github.com/kobescak-kristian/ai-compliance-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/kobescak-kristian/ai-compliance-orchestrator/actions/workflows/ci.yml)

Multi-jurisdiction iGaming compliance surveillance, built to demonstrate
**orchestration**: bounded agents fanning out across a deterministic
control plane, with contract-enforced handoffs, SQLite records of every
task state and agent tool call, and a human gate that nothing in the
system can bypass.

**Latest official result: gate v2.1 PASS on November 5, 2026. 29 of 30
synthetic compliance scenarios passed in all 3 runs, and one failed. The
earlier July 2026 gate v1.0 run failed; that result stays published.**

This repository publishes the evaluation record: the gate configuration,
the official results (including the failed run), and the analysis. It does
not ship a runnable demo; the committed configs and result tables are the
artifact. The July record is committed with its answer key, test pages and
miss analysis. The November test pages and keys are private by design, so
that result is published as sanitized results with a hash manifest.

## Problem

The motivating challenge: iGaming content — operator sites and affiliate
sites alike — can fall under several regulatory regimes at once (MGA,
UKGC, German GlüStV-style themes). Content compliant in one jurisdiction
can violate another, rules change, manual review is hard to scale, and a
single unbounded agent "checking compliance" is hard to trust or audit.
Every finding needs to trace back to a specific rule and a specific piece
of evidence, or it isn't worth anything.

**Rule-fidelity, stated up front:** all three jurisdictions' rule sets
are synthetic — modeled on publicly known regulatory *themes*, not
transcribed from real regulatory text, and not reviewed by counsel
(`adr/0003-synthetic-simplified-rulesets.md`). This system demonstrates
the orchestration architecture; it does not claim legal accuracy.

## Solution

One bounded checker agent per jurisdiction evaluates a page against its
own committed rule set only — it never sees another jurisdiction's
rules. A second agent, the shipped [`ai-claim-verification-agent`](https://github.com/kobescak-kristian/ai-claim-verification-agent)
(reused unmodified, not forked, pinned to commit
[`d444b13c`](https://github.com/kobescak-kristian/ai-claim-verification-agent/commit/d444b13c3ba07b9f4798d3298ec3bfc92da5a960)), adjudicates each checker's VIOLATION
findings as CONFIRMED / REJECTED / DISPUTED before anything counts as an
assertion. A third agent drafts remediation proposals for confirmed
violations only. Each proposal stays pending until a human approves or
rejects it through a CLI. Everything around the agents — task state,
severity ranking, schema enforcement, dead-lettering, resume-from-crash —
is deterministic Python with no model in the loop. Nothing in the system
can modify a page.

## System

Nodes, their tool boundaries, and what each may never do — not just
labels, the actual `allowed_tools` whitelist enforced in code
(`agents/checker/harness.py`, `agents/planner/harness.py`; boundary tests
in `tests/test_bounds.py`). No internal prompt or reasoning content is
shown; this is structure only.

```
                         PUBLISHED PAGES  +  RULE SETS
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  INTAKE — deterministic, no LLM │
                    │  builds one CheckTask per        │
                    │  (page × targeted jurisdiction)  │
                    └────────────────┬──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
     │ CHECKER (MLT)      │ │ CHECKER (GBR)      │ │ CHECKER (DEU)      │
     │ agent, caged       │ │ agent, caged       │ │ agent, caged       │
     │ tools: fetch_page, │ │ tools: fetch_page, │ │ tools: fetch_page, │
     │ read_ruleset (own  │ │ read_ruleset (own  │ │ read_ruleset (own  │
     │ jurisdiction only),│ │ jurisdiction only),│ │ jurisdiction only),│
     │ emit_finding       │ │ emit_finding       │ │ emit_finding       │
     │ NEVER: see another │ │ NEVER: see another │ │ NEVER: see another │
     │ jurisdiction, write│ │ jurisdiction, write│ │ jurisdiction, write│
     │ files, or network  │ │ files, or network  │ │ files, or network  │
     └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                └─────────────────────────┼─────────────────────────┘
                                          ▼
                    ┌───────────────────────────────┐
                    │  VERIFIER — shipped agent,       │
                    │  subprocess, byte-literal          │
                    │  unchanged, pinned commit hash    │
                    │  tools: its own 4, caged            │
                    │  NEVER: edit a finding, add one    │
                    │  the checker missed, see the key   │
                    └────────────────┬──────────────────┘
                                    │  CONFIRMED findings only
                                    ▼
                    ┌───────────────────────────────┐
                    │  PLANNER — agent, caged            │
                    │  tools: read_finding, read_rule,   │
                    │  emit_proposal                     │
                    │  NEVER: fetch a page, write a      │
                    │  file, approve its own proposal    │
                    │  (no such tool exists)             │
                    └────────────────┬──────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │  HUMAN GATE — deterministic CLI    │
                    │  list / approve / reject /         │
                    │  disputed                          │
                    │  NEVER: modify a page — nothing    │
                    │  upstream can either                │
                    └───────────────────────────────┘

   The system records to three SQLite databases:
   ┌─────────────────────────────────────────────────────────────────┐
   │  LEDGER DB: task_ledger (state machine, every stage) ·          │
   │  findings · proposals · adjudication_log (append-only, never    │
   │  overwritten) · dead_letter (invalid payloads) · audit_log /    │
   │  path_access_log                                                │
   │  AUDIT DB: tool_calls (checker and planner, every tool call,    │
   │  written before its result is ever used)                        │
   │  VERIFIER AUDIT DB: the shipped agent's tool_calls record       │
   └─────────────────────────────────────────────────────────────────┘
```

**Pipeline, one pass** (tools and limits are in the diagram):

1. **Intake** (deterministic): one CheckTask per page and targeted
   jurisdiction.
2. **Check** (agents, fan-out): COMPLIANT / VIOLATION / NOT_APPLICABLE per
   rule, with an evidence excerpt and a rationale.
3. **Verify** (the shipped agent, as an adjudicator): tests each VIOLATION
   claim and its evidence excerpt against the rule text and a fresh read of
   the page, blind to the checker's reasoning, to sibling findings and to
   the answer key. `nodes/verifier_runner.py` sets its storage paths and
   settings isolation at runtime; the pinned code is not edited.
4. **Plan** (agent): for every **CONFIRMED** finding only, drafts a
   RemediationProposal: offending text → proposed compliant text.
5. **Human gate** (deterministic CLI): approve and reject write ledger state
   only, idempotently.

**Severity ranking** (deterministic, outside this pass):
`orchestrator/aggregation.py` ranks pages by a score computed strictly from
rule metadata. No LLM.

**The cage, every agent, no exceptions:** an explicit `allowed_tools`
whitelist, a `max_turns` cap, a per-run budget ceiling plus an
in-process call-count circuit breaker, and PreToolUse/PostToolUse hooks
writing to a SQLite audit trail *before* a result is ever used. Built on
the same bounded-AI pattern as the shipped `ai-claim-verification-agent`
this system reuses as its adjudicator.

## Outcome

**Latest official result: November 5, 2026, gate v2.1 PASS**
(`evals/EVAL_RESULTS.md`, `evals/results/H2-2026-11-05-a7871a.json`, series
`H2-2026-11-05-a7871a` at commit `91105ca`, claude-sonnet-5-5, 3 runs per
scenario):

| Measure | Result | Gate limit | Outcome |
|---|---|---|---|
| Synthetic compliance scenarios passed in all 3 runs | 29 of 30 | at most 2 may fail | PASS |
| Deterministic reliability and planner-integrity checks | 52 of 52 | all must pass | PASS |
| Pages with a repeated material error on another rule | 0 of 30 | at most 6 | PASS |

One scenario failed on evidence overlap: in `h2-22` (`DEU-PC-03`) the
violation was found and CONFIRMED in all 3 runs, but the evidence excerpt
did not overlap the key's core span. The cause was not examined.

Under the predeclared binomial calculation, this supports a pass rate of
at least 80% (one-sided 95%) for scenarios drawn under
`evals/v2/SCENARIO_SPEC.md`, if those scenarios are a representative random
sample. The 30 scenarios are a deliberately balanced, purpose-authored
synthetic set, which does not establish representative random sampling.
The result does not show 30 of 30, perfect accuracy, production readiness,
legal compliance or whole-page screening.

**What changed after July.** A review on 2026-11-02 traced 6 of the 8 July
misses to the page reader, which dropped headings and list items. A repair
program addressed ten defects (D1 to D10, `STATE.md`), including that
reader, evidence-excerpt checks, timeouts and the prompt-injection
boundary, and re-evaluated under a new gate on a new private test set with
a new model and revised rule text. The two results are not directly
comparable.

**Historical result: July 9, 2026, gate v1.0 FAIL** (Sonnet 4.6,
`evals/EVAL_RESULTS.md`, run `gate-9328e564`, full 12-page corpus, 288
scored cells):

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Precision (pooled) | 0.844 | ≥ 0.95 | **FAIL** |
| Recall (pooled) | 0.900 | ≥ 0.90 | PASS (exactly at the line) |
| Precision / Recall (DEU) | 1.000 / 1.000 | ≥ 0.95 / ≥ 0.90 | PASS |
| Precision / Recall (GBR) | 0.786 / 0.846 | ≥ 0.95 / ≥ 0.90 | **FAIL** |
| Precision / Recall (MLT) | 0.750 / 0.857 | ≥ 0.95 / ≥ 0.90 | **FAIL** |
| NOT_APPLICABLE handling | 0.912 | ≥ 0.90 | PASS |
| Orchestration invariants | 100% terminal, zero lost, zero dead-letter | 100% | PASS |

**GATE RESULT: FAIL**, on violation-detection precision. Published as
the result, not adjusted and not re-run for a better number. The miss
analysis is in `evals/EVAL_RESULTS.md`, documented cell by cell. It first
attributed the misses to checker anchoring; its dated 2026-11-02 note
corrects the cause of 6 of the 8 misses to the page reader. DEU scored
clean (10/0/0); GBR and MLT carried every miss.

The orchestration mechanics passed in that run, across 23 check, 17 verify
and 32 plan tasks. The adjudicator ran the shipped agent unmodified across
32 live findings with its own repo verified clean before and after; the
failure-injection suite (`tests/test_failures.py`, FI-1 through FI-7)
and every agent-cage and blindness bound (`tests/test_bounds.py`) passed
in a 15-test suite, 0 skipped. The keyless suite is now 249 tests.

**Out of scope (deliberately, not yet):** real regulatory text
ingestion, legal-accuracy claims of any kind, live-web fetching at
scale, CMS/publishing integration, scheduled daemon runs, dashboards,
operator API integrations, multi-tenant anything.

## Limitations

1. Rules are synthetic, modeled on public regulatory themes — this
   system demonstrates the governance pattern, not legal coverage
   (`adr/0003-synthetic-simplified-rulesets.md`).
2. Answer-key authorship split — committed three-actor roles
   (spec/key: Claude · pages: Claude Code · blind labels: ChatGPT ·
   human adjudication, per `evals/ADJUDICATION_LOG.md`, frozen at
   `dd155bf`) removes key-authorship leakage; the page author still
   knows what it planted (`adr/0004`). Pages, key, and checkers share
   a model family; the blind cross-model label pass verifies the
   key's correctness, not the dataset's style-independence.
3. Checker and verifier share a model; adjudication guards against
   per-finding error, not model-family blind spots.
4. Gate v1.0 per-jurisdiction math at the July dataset size: frozen counts are
   MLT 7 / GBR 13 / DEU 10 violations (30 total,
   `evals/answer_key.yaml`). At recall ≥ 0.90 per jurisdiction, MLT
   tolerates zero misses before failing gate, an accepted baseline;
   GBR and DEU each tolerate exactly one miss. MLT's zero-miss
   tolerance did not hold in the official run (1 FN + 2 FP) —
   consistent with the quantization risk at this dataset size.
5. The November result is one series on one holdout. Its pages and keys
   are private, so it cannot be recomputed from a public clone. Holdout
   author isolation was by instruction, and blind labels came from a
   different model family (`evals/v2/SCENARIO_SPEC.md` §6).
6. Model runs do not repeat exactly: 4 rule cells changed verdict between
   the 3 November runs, all COMPLIANT vs NOT_APPLICABLE
   (`evals/EVAL_RESULTS.md`).

## Version Log

| Version | Date | Change |
|---|---|---|
| v0.1 | 2026-07-07 | Phase 0 — scaffold, SPEC.md, ADR-0001/0003, branch lock (compliance surveillance). |
| v0.2 | 2026-07-08 | Phase 1 — contracts, ledger schema, 3 rule sets, 12-page eval dataset, three-actor frozen answer key (30 violations, `adr/0004`). |
| v0.3 | 2026-07-08 | Phase 2 — deterministic orchestrator core, intake, aggregation, end-to-end on stub agents; FI-1..4/6/7 green. |
| v0.4 | 2026-07-08 | Phase 3 — real caged checker agent (Haiku dev leg): 12/12 terminal, pooled P 1.000 / R 0.941. |
| v0.5 | 2026-07-08–09 | Phase 4 — verifier as subprocess adjudicator (`adr/0002`), `policy/ADJUDICATION_POLICY.md`, FI-5, dev-leg adjudication table. |
| v0.6 | 2026-07-09 | Phase 5 — caged planner agent + human-gate CLI; dev leg: 15/15 proposals, CLI approve/reject round-trip. |
| v0.7 | 2026-07-09 | Phase 6 — official gate run, Sonnet 4.6, full corpus: **GATE FAIL** on precision, published with full miss-pattern analysis. |
| v0.8 | 2026-07-09 | Phase 7 — README, architecture diagram, Tier 0 documentation. |
| v0.9 | 2026-07-14 | Pre-publication README: FAIL statement first screen, Limitations (all four), reuse pin cited, per-jurisdiction gate rows. |
| v0.10 | 2026-11-05 | Repair program P-001 (D1 to D10), gate v2.1 on private holdout H2: **PASS**, 29 of 30 scenarios, 1 failed. July FAIL retained as historical evidence. |
