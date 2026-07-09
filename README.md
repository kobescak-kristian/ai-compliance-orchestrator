# ai-compliance-orchestrator

Multi-jurisdiction iGaming compliance surveillance, built to prove one
thing the rest of the portfolio doesn't: **orchestration** — bounded
agents fanning out across a deterministic control plane, with
contract-enforced handoffs, a full audit trail, and a human gate that
nothing in the system can bypass.

## Problem

iGaming content — operator sites and affiliate sites alike — is published
under multiple regulatory regimes at once (MGA, UKGC, German
GlüStV-style themes). Content compliant in one jurisdiction violates
another; rules change; manual review doesn't scale; and a single
unbounded agent "checking compliance" can't be trusted or audited. Every
finding needs to trace back to a specific rule and a specific piece of
evidence, or it isn't worth anything.

**Rule-fidelity, stated up front:** all three jurisdictions' rule sets
are synthetic — modeled on publicly known regulatory *themes*, not
transcribed from real regulatory text, and not reviewed by counsel
(`adr/0003-synthetic-simplified-rulesets.md`). This system demonstrates
the orchestration architecture; it does not claim legal accuracy.

## Solution

One bounded checker agent per jurisdiction evaluates a page against its
own committed rule set only — it never sees another jurisdiction's
rules. A second agent, the shipped `ai-claim-verification-agent`
(reused unmodified, not forked), adjudicates each checker's VIOLATION
findings as CONFIRMED / REJECTED / DISPUTED before anything counts as an
assertion. A third agent drafts remediation proposals for confirmed
violations only. A human approves or rejects every proposal through a
CLI. Every step in between — task state, severity ranking, schema
enforcement, dead-lettering, resume-from-crash — is deterministic Python
with no model in the loop. Nothing in the system can modify a page. Ever.

## System

```
                      ┌──────────────────────────────────────────────┐
                      │        ORCHESTRATOR (deterministic)           │
                      │ task ledger · state machine · queues          │
                      │ schema enforcement · dead-letter · resume     │
                      │ severity aggregation (from rule metadata)     │
                      └──┬───────────┬───────────┬───────────┬───────┘
                         │           │           │           │
                   ┌─────▼────┐ ┌────▼─────┐ ┌───▼──────┐ ┌──▼───────┐
  published pages →│ INTAKE   │ │ CHECKERS │ │ VERIFIER │ │ PLANNER  │
  + rule sets      │ (no LLM) │ │ (1 agent │ │ (shipped │ │ (agent,  │
                   │ inventory│ │ per juris│ │ agent as │ │ proposals│
                   └──────────┘ │ -diction)│ │subprocess)│ │ only)    │
                                └──────────┘ └──────────┘ └────┬─────┘
                                                      ┌─────────▼───────┐
                                                      │ HUMAN GATE (CLI)│
                                                      │ approve/reject  │
                                                      └─────────────────┘
  Every box writes to SQLite: task ledger + agent audit trails.
```

**Pipeline, one pass:**

1. **Intake** (deterministic) — inventories pages, builds one CheckTask
   per (page × targeted jurisdiction). No LLM.
2. **Check** (agents, fan-out) — one bounded checker agent per
   jurisdiction: `fetch_page`, `read_ruleset` (own jurisdiction only),
   `emit_finding`. COMPLIANT / VIOLATION / NOT_APPLICABLE, with an
   evidence excerpt and a rationale, per rule.
3. **Verify** (the shipped agent, as an adjudicator) — the shipped
   `ai-claim-verification-agent` runs byte-literal unchanged, pinned to
   a specific commit, as a subprocess. It re-derives each VIOLATION
   finding from the rule text and the page alone — blind to the
   checker's reasoning, to sibling findings, and to the answer key —
   and returns CONFIRMED / REJECTED / DISPUTED. It can challenge a
   finding; it can never add one the checker missed.
4. **Aggregate** (deterministic) — ranks pages by a severity score
   computed strictly from rule metadata. No LLM.
5. **Plan** (agent) — for every **CONFIRMED** finding only, a bounded
   planner agent drafts a RemediationProposal: offending text →
   proposed compliant text. It can only emit proposals — it can never
   fetch a page, write a file, or approve its own work (there is no
   such tool in its whitelist).
6. **Human gate** (deterministic CLI) — `list` / `approve` / `reject` /
   `disputed`. Approve/reject write ledger state only, idempotently.
   Nothing here, or anywhere upstream, can touch a page.

**The cage, every agent, no exceptions:** an explicit `allowed_tools`
whitelist, a `max_turns` cap, a per-run budget ceiling plus an
in-process call-count circuit breaker, and PreToolUse/PostToolUse hooks
writing to a SQLite audit trail *before* a result is ever used. Built on
the same bounded-AI pattern as the shipped `ai-claim-verification-agent`
this system reuses as its adjudicator.

## Outcome

**Official gate run — Sonnet 4.6, 2026-07-09** (`evals/EVAL_RESULTS.md`,
run `gate-9328e564`, full 12-page corpus, 288 scored cells):

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Precision (pooled) | 0.844 | ≥ 0.95 | **FAIL** |
| Recall (pooled) | 0.900 | ≥ 0.90 | PASS (exactly at the line) |
| NOT_APPLICABLE handling | 0.912 | ≥ 0.90 | PASS |
| Orchestration invariants | 100% terminal, zero lost, zero dead-letter | 100% | PASS |

**GATE RESULT: FAIL**, on violation-detection precision. Published as
the result, not adjusted, not re-run for a better number — 5 of the 8
misses trace to two concrete, evidenced failure patterns (the checker
anchoring its judgment on the wrong paragraph, or on the dataset's own
designed distractor sentence), documented cell-by-cell with root cause
in `evals/EVAL_RESULTS.md`'s OFFICIAL section. DEU scored clean (10/0/0);
GBR and MLT carried every miss.

What passed cleanly, and is the actual claim of this build: the
orchestration mechanics. Every one of 23 check tasks, 17 verify tasks,
and 32 plan tasks reached a terminal state; zero tasks were lost; zero
dead-lettered; the adjudicator ran the shipped agent unmodified across
32 live findings with its own repo verified clean before and after;
the full failure-injection suite (`tests/test_failures.py`, FI-1
through FI-7) and every agent-cage/blindness bound
(`tests/test_bounds.py`) pass — 15 tests, 0 skipped. The system is
honest about what it got wrong on detection *because* the plumbing that
makes that honesty possible — typed contracts enforced at every
boundary, an append-only adjudication ledger, a scorer frozen before the
run it scores — held up under a full, real, paid run.

**Out of scope (deliberately, not yet):** real regulatory text
ingestion, legal-accuracy claims of any kind, live-web fetching at
scale, CMS/publishing integration, scheduled daemon runs, dashboards,
operator API integrations, multi-tenant anything.

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
