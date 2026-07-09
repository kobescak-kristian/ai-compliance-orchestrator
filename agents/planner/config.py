"""Model routing, caps, and paths for the caged planner agent
(BLUEPRINT.md §3, §4). Mirrors agents/checker/config.py -- same house
pattern, own copy per agent so each stays independently cageable.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DB_PATH = REPO_ROOT / "audit.db"  # shared physical file with the checker; rows keyed by run_id/task_id

MODEL = "claude-haiku-4-5-20251001"  # dev iterations (locked models decision, SPEC.md)
EVAL_MODEL = "claude-sonnet-4-6"  # official gate run, Phase 6
MAX_TURNS = 15
MAX_BUDGET_USD = 0.20  # per-finding ceiling for Haiku dev runs
EVAL_MAX_BUDGET_USD = 1.00  # per-finding ceiling for Sonnet gate runs, Phase 6
MAX_TOOL_CALLS = 30  # circuit breaker: hard backstop independent of max_turns

MCP_SERVER_NAME = "planwork"
TOOL_NAMES = ["read_finding", "read_rule", "emit_proposal"]
QUALIFIED_TOOL_NAMES = [f"mcp__{MCP_SERVER_NAME}__{name}" for name in TOOL_NAMES]
