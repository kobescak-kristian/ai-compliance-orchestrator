"""Caged checker agent, parameterized by jurisdiction. One instance per
jurisdiction; each evaluates its assigned pages against its own rule set
only (contracts.schemas.CheckTask -> ViolationFinding, verdict
COMPLIANT | VIOLATION | NOT_APPLICABLE with evidence excerpt + rationale).

Tool whitelist (BLUEPRINT.md §4): fetch_page, read_ruleset (own
jurisdiction only), emit_finding. May never see another jurisdiction's
rules, write files, or reach the network.

Real agent implemented Phase 3 (harness.py, tools.py, config.py, pages.py,
audit.py, prompts.py). stub.py from Phase 2 remains the pipeline default;
the real checker is opt-in behind a switch until Phase 6's gate run
(BLUEPRINT.md §9).
"""
