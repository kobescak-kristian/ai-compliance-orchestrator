"""Deterministic control plane (ADR-0001): task ledger, state machine,
queues, schema enforcement at every handoff boundary, resume-from-ledger,
and severity aggregation from rule metadata. No LLM calls originate here.

Ledger states: QUEUED -> RUNNING -> DONE | FAILED | DEAD_LETTER | ESCALATED.

Ledger schema and contracts land Phase 1; core + intake + aggregation
against stub agents land Phase 2 (BLUEPRINT.md §9).
"""
