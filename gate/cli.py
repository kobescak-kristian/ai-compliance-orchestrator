"""Human review queue CLI: list / approve / reject
contracts.schemas.RemediationProposal rows. Deterministic; approve/reject
updates ledger state only -- nothing in this module, or anywhere in the
system, can modify a page.

Implemented Phase 5, alongside the planner agent (BLUEPRINT.md §9).
"""
