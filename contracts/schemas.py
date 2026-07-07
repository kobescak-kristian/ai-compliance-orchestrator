"""Pydantic v2 handoff contracts (BLUEPRINT.md §5): ComplianceRule,
CheckTask, ViolationFinding, AccuracyFinding, SeverityReport,
RemediationProposal, and the ledger row schema. Enforced at every
orchestrator boundary; a payload that fails validation is rejected into
a dead-letter table, never silently coerced or dropped.

Frozen before any agent code exists — committed Phase 1 (BLUEPRINT.md §9).
"""
