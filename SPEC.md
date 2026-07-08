# SPEC — ai-compliance-orchestrator

*Condensed from BLUEPRINT.md v1.1 (2026-07-07). Full context, architecture,
and rationale live in BLUEPRINT.md — this file is the behavioral contract
for execution.*

## Non-negotiables (BLUEPRINT §3)

- Orchestrator is deterministic Python — no LLM in the control plane.
  Bounded-AI rule v2: deterministic logic executes, routes, and ranks; AI
  analyzes and recommends; AI never controls execution, state transitions,
  or severity scoring.
- Every agent is caged like the shipped verifier: explicit `allowed_tools`
  whitelist, `max_turns` cap, per-run budget ceiling + in-process
  call-count circuit breaker, PreToolUse/PostToolUse hooks → audit.db
  before results are used. Reuse `agent/audit.py` pattern directly.
- No network access for any agent. v1 corpus is local seeded HTML.
  Real-web variant (fetch-and-freeze) is post-v1.
- Handoffs are typed contracts (Pydantic v2), enforced at the boundary. A
  payload that fails schema validation is rejected into a dead-letter
  table — never silently coerced, never silently dropped.
- Every task reaches a terminal state: QUEUED → RUNNING → DONE | FAILED |
  DEAD_LETTER | ESCALATED. Zero lost tasks is a gated invariant, not an
  aspiration.
- Eval gate + failure-injection suite committed before agent code.
- Rule sets are versioned artifacts. Every finding references rule_id +
  ruleset_version; a finding that can't cite its rule is schema-invalid.
- Verifier is reused, not forked: subprocess node with JSON stdin/stdout
  contract; the shipped repo stays untouched.
- Secrets: `.env` local + gitignored only; placeholder-key trap applies —
  key-absent mode must be explicit and logged, never silently degrading.

## Agent boundaries (BLUEPRINT §4)

| Node | Type | Tools (whitelist) | May never |
|---|---|---|---|
| Intake | deterministic | filesystem read on pages + rule sets | call any model |
| Checker (×3) | LLM agent | `fetch_page`, `read_ruleset` (own jurisdiction only), `emit_finding` | see other jurisdictions' rules, write files, network |
| Verifier | LLM agent (shipped) | its existing 4 read-only tools | anything outside its dataset dir (existing bounds suite) |
| Planner | LLM agent | `read_finding`, `read_rule`, `emit_proposal` | fetch pages, write files, approve its own proposal |
| Aggregator | deterministic | ledger read/write | call any model |
| Human gate | deterministic CLI | ledger read/write | modify any page content |

## Phase discipline (BLUEPRINT §9)

One phase per session. Stop at each phase's acceptance criteria; do not
proceed into the next phase in the same session unless explicitly told.

| Phase | Deliverable | Accept when |
|---|---|---|
| 0 | Private repo, scaffold, SPEC.md (condensed from this), CLAUDE.md, ADR-0001/0003 drafts, BLUEPRINT.md committed | Repo pushed; structure matches §8; §10 decisions recorded in SPEC |
| 1 | Contracts (§5) + ledger schema + rule sets + full eval dataset + answer key + eval_config + FI test skeletons | Kristian approved rule sets, dataset + gates; committed; **no agent code exists yet** |
| 2 | Orchestrator core + intake + aggregation, end-to-end with **stub agents** (deterministic fakes returning fixture payloads) | Full pipeline green on stubs; FI-1..FI-4, FI-6, FI-7 pass with stubs; zero LLM calls so far |
| 3 | Checker agent (caged, jurisdiction-parameterized) replacing its stubs | Checker gate leg green on dev model; bounds + rule-isolation tests green |
| 4 | Verifier subprocess node (ADR-0002) replacing its stub | Shipped agent runs unmodified inside pipeline; FI-5 implemented + green |
| 5 | Planner agent + human-gate CLI | Proposal queue populated from a full run; approve/reject round-trip in ledger |
| 6 | Official gate run (Sonnet 4.6) + EVAL_RESULTS.md + FI suite full green | GATE GREEN or honest FAIL with miss-pattern analysis committed |
| 7 | README (house structure, '## System' heading) + architecture diagram + demo recording | Stop conditions met |

**Amendment (2026-07-07):** Phase 1 split by Kristian's decision into 1a
(contracts + ledger schema + eval config + FI test skeletons,
authorship-independent) and 1b (rule sets + seeded pages + answer key,
per the §10.7 authorship split). 1a DONE (e78f3c0). 1b-i DONE (3124c1e):
rule sets + 12 pages. **1b-ii DONE — Phase 1 COMPLETE (frozen key,
adjudication log).**

Phase 2 is deliberate: orchestration is proven deterministically before any
model is invoked — the multi-agent claim is tested at its own layer,
cheaply, and the stubs remain as fixtures for the FI suite forever.

## Decisions (BLUEPRINT §10, resolved 2026-07-07 unless overridden at Phase 0 paste)

1. **Branch:** B — compliance surveillance. LOCKED (rule fired).
2. **Repo name:** `ai-compliance-orchestrator` (T0; rename at flip is
   near-free for a private repo).
3. **Verifier integration:** subprocess + JSON contract, as optional
   fourth checker (claim-accuracy dimension), Phase 4.
4. **Gate thresholds:** 0.95 / 0.90 pooled and per jurisdiction;
   NOT_APPLICABLE ≥ 0.90.
5. **Dataset sizing:** 3 jurisdictions × ~8 rules; 12 pages; ~25
   violations + distractors.
6. **Positioning (deferred):** flagship question reopens after first
   external signal; not decided here.
7. **RESOLVED 2026-07-07:** Option A — three-actor split (spec author:
   strongest model; page author: Code; blind labeler: ChatGPT;
   adjudicator: Kristian). Protocol in evals/INJECTION_SPEC.md.

## Gate (BLUEPRINT §7, summary)

VIOLATION detection: precision ≥ 0.95, recall ≥ 0.90 — pooled AND per
jurisdiction. NOT_APPLICABLE handling ≥ 0.90. Orchestration invariants at
100%: every task terminal; zero lost tasks; FI-1..FI-7 green; idempotent
re-run. Official gate run on Sonnet 4.6, dev on Haiku 4.5. Gates never
adjusted post-run — report FAIL honestly rather than gate-shop.

## Out of scope (BLUEPRINT §12 — README "production upgrades" section only)

Real regulatory text ingestion · legal-accuracy claims of any kind ·
live-web fetching at scale · CMS/publishing integration · scheduled
daemon runs · dashboards · operator API integrations · multi-tenant
anything · more than the four node types.
