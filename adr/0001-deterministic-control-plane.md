# ADR 0001: Deterministic Control Plane

## Status
Accepted (2026-07-07, Phase 0)

## Date: 2026-07-07

## Context
This is the first artifact in the portfolio with agent-to-agent fan-out:
multiple bounded checker agents (one per jurisdiction), an optional
verifier subprocess, and a planner agent, coordinated across a pipeline
with typed handoffs and a human gate. Multi-agent orchestration is
exactly the layer where "AI decides" can silently expand from analysis
into control — routing, retries, state transitions, or severity ranking
drifting into the model's judgment because it's convenient. Bounded-AI v1
(deterministic executes, AI recommends) specifies who owns individual
actions but not who owns the pipeline itself.

## Decision
The orchestrator — task ledger, state machine, queues, schema enforcement
at every handoff, dead-letter routing, resume-from-ledger, and severity
aggregation — is deterministic Python. No LLM call originates in the
control plane. Every task moves through a fixed set of terminal states
(QUEUED → RUNNING → DONE | FAILED | DEAD_LETTER | ESCALATED), decided by
code, not by a model's output. Agents (checker, verifier, planner)
analyze and recommend only: they emit typed findings and proposals into
the pipeline; they never decide what runs next, what a payload's severity
is, or whether a task is done. Severity scoring is computed from rule
metadata (rule sets carry the severity class), not decided by any model
at evaluation time.

## Consequences
- Every state transition and every finding is reproducible and auditable
  from the ledger alone, independent of any model's non-determinism.
- A misbehaving or budget-capped agent produces a FAILED or DEAD_LETTER
  task, never a silently-lost or silently-miscategorized one — the
  control plane cannot be talked into skipping its own invariants.
- Trade-off: the system cannot adapt its own routing or retry logic based
  on agent output content — any such adaptivity must be designed and
  committed as deterministic code, not learned or inferred at runtime.
  Accepted: this build proves orchestration discipline, not routing
  intelligence.
- This decision is the load-bearing one for every failure-injection test
  in BLUEPRINT §6 (FI-1..FI-7): each asserts the control plane's
  determinism holds under a specific adversarial or degraded condition.
