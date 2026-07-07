"""Subprocess wrapper around the shipped ai-claim-verification-agent, run
as an optional fourth checker on the claim-accuracy dimension: published
claims vs operator source pages. JSON stdin/stdout contract; the shipped
repo stays untouched (ADR-0002, drafted Phase 4). Contract:
contracts.schemas.AccuracyFinding reuses the shipped agent's existing
verdict schema (SUPPORTED | CONTRADICTED | UNVERIFIABLE) verbatim.

Implemented Phase 4, replacing its stub from Phase 2 (BLUEPRINT.md §9).
"""
