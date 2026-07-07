# BLUEPRINT — ai-compliance-orchestrator
*v1.1 — 2026-07-07. Branch B LOCKED (multi-jurisdiction compliance surveillance). Authoritative build document; SPEC.md is condensed from this at Phase 0. Written for Claude Code (executor). House patterns apply throughout: eval gate committed before code, truth on disk, done means checked (exit-code-0 + ledger status), bounded-AI rule v2, secrets never in transcripts.*

**BRANCH DECISION (resolved 2026-07-07):** Rule was "Paradise Media
second-stage confirmation before Phase 0 → A (offer-sync); otherwise →
B." Paradise timeline reported as 3–4 weeks, Phase 0 starting now → rule
fires → **Branch B.** Branch A (offer-sync) archived as §13 note; may be
revived as a v2 skin — the control plane is shared.

**SEQUENCING REVISION (recorded 2026-07-07):** The original gate "Phase 0
blocked behind claim-verification-agent flip" is REVISED — removed by
explicit decision (reason: Paradise timeline uncertainty; recording
deprioritized). The recording/flip remains an open item on its own track
in kristian-os STATE. This is a formal lock revision, not drift.

Classification: PROJECT. Named reader: recruiters/hiring managers at
iGaming operators and affiliates (majority of active applications).
Trigger: multi-agent slot decision + branch lock, 2026-07-07.
Timebox: ~2 weekends.

---

## 1. Problem

iGaming content — operator sites and affiliate sites alike — is
published under multiple regulatory regimes at once (e.g. MGA, UKGC,
German GlüStV). Each regime has its own rules on bonus-term
transparency, responsible-gambling messaging, prohibited claims, and geo
eligibility. Pages that are compliant in one jurisdiction violate
another; rules change; manual review doesn't scale; and a single
unbounded agent "checking compliance" cannot be trusted or audited.
This system is the orchestration layer: one bounded checker agent per
jurisdiction, each loaded with a committed rule set, coordinated by
deterministic code, with typed handoff contracts, severity-ranked
findings, a full audit trail, and a human gate. Nothing publishes,
nothing auto-remediates; every finding is traceable to a rule ID and an
evidence excerpt.

**What this proves that the existing portfolio does not:** orchestration.
The five engines are single systems; ai-claim-verification-agent is a
single bounded agent. This is the first artifact with agent-to-agent
fan-out, contract-enforced boundaries, aggregation, and failure modes
committed as tests.

**Rule-fidelity stance (ADR-0003, written at Phase 0):** the rule sets
are synthetic and deliberately simplified — modeled on publicly known
regulatory themes, NOT real regulatory text, and the README says so
explicitly. The system demonstrates the architecture for compliance
surveillance; it does not claim legal accuracy. This is the honest
version of the eval and the mitigation for domain-literate reviewers.

## 2. What it does (one pass, v1)

Input: a set of **published pages** (seeded local HTML, v1) and three
**committed jurisdiction rule sets** (versioned JSON).

Pipeline (per run):
1. **Intake (deterministic):** inventory pages, build CheckTasks —
   one per (page × jurisdiction). No LLM.
2. **Check (agents, fan-out):** one bounded checker agent per
   jurisdiction evaluates each assigned page against its rule set only.
   Per rule: COMPLIANT | VIOLATION | NOT_APPLICABLE, with evidence
   excerpt and rationale. A checker never sees another jurisdiction's
   rules.
3. **Verify (the shipped agent, optional node, Phase 4):**
   ai-claim-verification-agent runs unmodified as a fourth checker on
   the claim-accuracy dimension — published claims vs operator source
   pages; CONTRADICTED findings map into the same finding flow as a
   distinct category. Kept as designed reuse of shipped work.
4. **Aggregate (deterministic):** collect findings, rank pages by
   severity score computed from rule metadata (severity classes are in
   the rule sets, not decided by any model). No LLM.
5. **Plan (agent):** for each VIOLATION, a bounded planner agent drafts
   a RemediationProposal (offending text → proposed compliant text +
   rule ref). It can only emit proposals — never writes, edits,
   publishes.
6. **Human gate (deterministic):** proposals + ranked findings land in
   a review queue (SQLite + CLI). Approve/reject updates ledger state
   only. Nothing in the system can modify a page. Ever.

Output: severity-ranked compliance report per page/jurisdiction +
proposal queue + full SQLite audit trail (every agent tool call, every
handoff, every state transition).

## 3. Non-negotiables

- **Orchestrator is deterministic Python — no LLM in the control plane.**
  Bounded-AI rule v2: deterministic logic executes, routes, and ranks;
  AI analyzes and recommends; AI never controls execution, state
  transitions, or severity scoring.
- **Every agent is caged like the verifier:** explicit `allowed_tools`
  whitelist, `max_turns` cap, per-run budget ceiling + in-process
  call-count circuit breaker, PreToolUse/PostToolUse hooks → audit.db
  before results are used. Reuse `agent/audit.py` pattern directly.
- **No network access for any agent.** v1 corpus is local seeded HTML.
  Real-web variant = fetch-and-freeze (separate deterministic fetcher;
  frozen pages local-only/gitignored; only the run report goes public) —
  post-v1.
- **Handoffs are typed contracts (Pydantic v2), enforced at the boundary.**
  A payload that fails schema validation is rejected into a dead-letter
  table — never silently coerced, never silently dropped.
- **Every task reaches a terminal state.** QUEUED → RUNNING →
  DONE | FAILED | DEAD_LETTER | ESCALATED. "Zero lost tasks" is a gated
  invariant, not an aspiration.
- **Eval gate + failure-injection suite committed before agent code.**
- **Rule sets are versioned artifacts.** Every finding references
  rule_id + ruleset_version; a finding that can't cite its rule is
  schema-invalid.
- **Verifier is reused, not forked:** subprocess node with JSON
  stdin/stdout contract; the shipped repo stays untouched.
- **Secrets:** `.env` local + gitignored only; placeholder-key trap from
  the engine audits applies — key-absent mode must be explicit and
  logged, never silently degrading.

## 4. Architecture

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

Agent boundaries (who may do what — enforced, not documented):
| Node | Type | Tools (whitelist) | May never |
|---|---|---|---|
| Intake | deterministic | filesystem read on pages + rule sets | call any model |
| Checker (×3) | LLM agent | `fetch_page`, `read_ruleset` (own jurisdiction only), `emit_finding` | see other jurisdictions' rules, write files, network |
| Verifier | LLM agent (shipped) | its existing 4 read-only tools | anything outside its dataset dir (existing bounds suite) |
| Planner | LLM agent | `read_finding`, `read_rule`, `emit_proposal` | fetch pages, write files, approve its own proposal |
| Aggregator | deterministic | ledger read/write | call any model |
| Human gate | deterministic CLI | ledger read/write | modify any page content |

## 5. Handoff contracts (Pydantic v2 — committed Phase 1, frozen before agent code)

- `ComplianceRule`: jurisdiction, rule_id, category (BONUS_TERMS |
  RG_MESSAGING | PROHIBITED_CLAIMS | GEO_ELIGIBILITY), severity
  (CRITICAL | MAJOR | MINOR), rule_text (simplified), ruleset_version.
- `CheckTask`: page_path, jurisdiction, ruleset_version, assigned_rules[].
- `ViolationFinding`: page_path, jurisdiction, rule_id,
  ruleset_version, verdict (COMPLIANT | VIOLATION | NOT_APPLICABLE),
  evidence_excerpt, rationale, task_id.
- `AccuracyFinding`: reuses the verifier's existing verdict schema
  verbatim (claim, verdict SUPPORTED/CONTRADICTED/UNVERIFIABLE, source,
  evidence) + task linkage. The contract adapts to the shipped agent,
  not the other way around.
- `SeverityReport` (deterministic output): page_path, findings[],
  severity_score, rank, computed_from ruleset_version(s).
- `RemediationProposal`: page_path, rule_id, offending_text,
  proposed_text, evidence_refs[], status (PENDING | APPROVED |
  REJECTED | ESCALATED), created_by_run_id.
- Ledger row (every task, every stage): task_id, stage, state, attempt,
  started_at, ended_at, exit_code, error_class, payload_ref.

## 6. Failure modes — designed in, committed as the failure-injection suite

Each row is a test in `tests/test_failures.py`, not a README promise.

| ID | Injected failure | Required behavior (asserted) |
|---|---|---|
| FI-1 | Agent budget/turn cap trips mid-task | Task → FAILED with error_class; run completes; zero lost tasks |
| FI-2 | Agent emits schema-invalid payload (e.g. finding without rule_id) | Rejected at boundary → DEAD_LETTER row with raw payload; downstream never sees it |
| FI-3 | Orchestrator killed mid-run, restarted | Resumes from ledger; completed tasks not re-run; zero duplicate findings/proposals |
| FI-4 | One jurisdiction's rule set missing/corrupt | Other jurisdictions proceed; MISSING_RULESET recorded per affected task; aggregation proceeds with explicit gap, not silent success |
| FI-5 | Conflicting findings on the same excerpt (checker: COMPLIANT; verifier: CONTRADICTED — or two rules colliding) | Task → ESCALATED, surfaced in human queue with both artifacts — never auto-resolved |
| FI-6 | Full re-run on identical input | Idempotent: zero duplicate findings/proposals (dedup on content hash + rule_id) |
| FI-7 | Path escape attempt in any agent tool input; checker requests another jurisdiction's rule set | Rejected; audit row written (extends the verifier's bounds test to all agents + rule-isolation check) |

## 7. Eval gate (committed Phase 1, before any agent code — hard PASS/FAIL in `evals/eval_config.yaml`)

**Dataset (synthetic, ground truth authored first, Kristian approves before freeze):**
- 3 jurisdiction rule sets (synthetic, simplified — per ADR-0003):
  ~8 rules each across the four categories, each with severity class.
- 12 seeded published pages (mix: operator-style + affiliate-style).
- ~25 injected violations across severities and jurisdictions, plus
  compliant near-miss distractors (must NOT be flagged) and
  NOT_APPLICABLE cases (e.g. UKGC rule on a page marked non-UK).
- Answer key committed; bounds test asserts the key never appears in
  any agent input/output (verifier repo pattern, reused).
- **Authorship split (open item, decide before Phase 1 kickoff):** the
  model that writes the seeded pages must not author the answer key —
  shared-author leakage is a named limitation in the verifier's eval;
  this build fixes it by construction, not by caveat.

**Gate:**
- VIOLATION detection: precision ≥ 0.95, recall ≥ 0.90 — pooled AND
  per jurisdiction (a jurisdiction-blind system must not pass on
  averages).
- NOT_APPLICABLE handling: ≥ 0.90 correct (guards against a checker
  that flags everything).
- Orchestration invariants at 100%: every task terminal; zero lost
  tasks; FI-1..FI-7 green; idempotent re-run.
- Cost + turns recorded per run; official gate run on Sonnet 4.6, dev
  on Haiku 4.5 (house model routing; Max plan auth — no per-token key).
- `evals/EVAL_RESULTS.md` with dated runs, miss-pattern analysis on any
  FAIL, gates never adjusted post-run (Context-engine precedent: report
  FAIL honestly rather than gate-shop).

## 8. Repo structure (target)

```
ai-compliance-orchestrator/
├── BLUEPRINT.md / SPEC.md / README.md / CLAUDE.md
├── adr/0001-deterministic-control-plane.md
├── adr/0002-verifier-as-subprocess-node.md
├── adr/0003-synthetic-simplified-rulesets.md
├── orchestrator/        # ledger, state machine, queues, schema enforcement, resume, aggregation
├── contracts/schemas.py # all Pydantic handoff contracts
├── rulesets/            # versioned jurisdiction rule sets (JSON)
├── agents/checker/      # caged checker agent (parameterized by jurisdiction)
├── agents/planner/      # caged planner agent
├── nodes/verifier.py    # subprocess wrapper around ai-claim-verification-agent
├── intake/inventory.py  # deterministic page/rule inventory → CheckTasks
├── gate/cli.py          # human review queue (list / approve / reject)
├── evals/               # dataset, answer key, eval_config.yaml, run_eval.py, EVAL_RESULTS.md
├── tests/test_failures.py  # FI-1..FI-7
├── tests/test_bounds.py    # per-agent cage + rule-isolation checks
└── .githooks/           # Tier 0 validator (canonical '## System' heading)
```

## 9. Build plan — phases with acceptance criteria

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

Phase 2 is deliberate: **orchestration is proven deterministically before
any model is invoked** — the multi-agent claim is tested at its own
layer, cheaply, and the stubs remain as fixtures for the FI suite forever.

## 10. Decisions (resolved 2026-07-07 unless overridden at Phase 0 paste)

1. **Branch:** B — compliance surveillance. LOCKED (rule fired).
2. **Repo name:** `ai-compliance-orchestrator` (T0; rename at flip is
   near-free for a private repo).
3. **Verifier integration:** subprocess + JSON contract, as optional
   fourth checker (claim-accuracy dimension), Phase 4.
4. **Gate thresholds:** 0.95 / 0.90 pooled and per jurisdiction;
   NOT_APPLICABLE ≥ 0.90.
5. **Dataset sizing:** 3 jurisdictions × ~8 rules; 12 pages;
   ~25 violations + distractors.
6. **Positioning (deferred):** flagship question reopens after first
   external signal; not decided here.
7. **OPEN — must be answered before Phase 1 kickoff:** answer-key
   authorship split (§7). Not Code's decision.

## 11. Stop conditions (done means all four)

Gate run recorded (green or honest FAIL + analysis) · README + diagram up ·
FI suite green · one demo recording.

## 12. Out of scope (README "production upgrades" section only)

Real regulatory text ingestion · legal-accuracy claims of any kind ·
live-web fetching at scale · CMS/publishing integration · scheduled
daemon runs · dashboards · operator API integrations · multi-tenant
anything · more than the four node types.

## 13. Archived branch note

Branch A (offer/deal synchronization) — same control plane, different
skin (OfferRecord/ChangeEvent contracts, drift-injection dataset,
verifier as centerpiece). Archived 2026-07-07 when the decision rule
fired for B. Revivable as v2 without architectural change.
