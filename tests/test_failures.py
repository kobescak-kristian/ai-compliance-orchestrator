"""Failure-injection suite, FI-1..FI-7 (BLUEPRINT.md §6). Each row of that
table is a test here, not a README promise:

FI-1  Agent budget/turn cap trips mid-task -> FAILED, run completes, zero lost tasks
FI-2  Schema-invalid agent payload -> rejected at boundary -> DEAD_LETTER, raw payload preserved
FI-3  Orchestrator killed mid-run, restarted -> resumes from ledger, no re-run, no duplicates
FI-4  One jurisdiction's rule set missing/corrupt -> others proceed; MISSING_RULESET recorded, not silent
FI-5  Conflicting findings on the same excerpt -> ESCALATED, both artifacts surfaced, never auto-resolved
FI-6  Full re-run on identical input -> idempotent, zero duplicate findings/proposals
FI-7  Path escape / cross-jurisdiction rule-set request -> rejected, audit row written

Committed before any agent code exists (BLUEPRINT.md §3, §9). Skeletons
only until Phase 1 contracts + ledger schema land.
"""
