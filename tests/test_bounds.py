"""Per-agent cage checks (allowed_tools whitelist, max_turns cap, budget
ceiling, audit-hook coverage) and rule-isolation checks (a checker must
never see another jurisdiction's rule set; FI-7 extends this to a full
failure-injection assertion). Extends the ai-claim-verification-agent
bounds-test pattern to every agent in this system (BLUEPRINT.md §3).

Skeletons only until Phase 3 (checker agent) and Phase 5 (planner agent)
land (BLUEPRINT.md §9).
"""
