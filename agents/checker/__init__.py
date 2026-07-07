"""Caged checker agent, parameterized by jurisdiction. One instance per
jurisdiction; each evaluates its assigned pages against its own rule set
only (contracts.schemas.CheckTask -> ViolationFinding, verdict
COMPLIANT | VIOLATION | NOT_APPLICABLE with evidence excerpt + rationale).

Tool whitelist (BLUEPRINT.md §4): fetch_page, read_ruleset (own
jurisdiction only), emit_finding. May never see another jurisdiction's
rules, write files, or reach the network.

Implemented Phase 3, replacing its stub from Phase 2 (BLUEPRINT.md §9).
"""
