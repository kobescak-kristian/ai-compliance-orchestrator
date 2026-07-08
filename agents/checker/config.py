"""Model routing, caps, and paths for the caged checker agent
(BLUEPRINT.md §3, §4). Numbers reused from ai-claim-verification-agent's
agent/config.py -- SPEC.md non-negotiable: "Reuse agent/audit.py pattern
directly," applied to the whole cage, not just the audit table.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PAGES_ROOT = (REPO_ROOT / "evals" / "dataset" / "pages").resolve()
RULESETS_DIR = (REPO_ROOT / "rulesets").resolve()
AUDIT_DB_PATH = REPO_ROOT / "audit.db"

MODEL = "claude-haiku-4-5-20251001"  # dev iterations (locked models decision, SPEC.md)
EVAL_MODEL = "claude-sonnet-4-6"  # official gate run, Phase 6
MAX_TURNS = 20
MAX_BUDGET_USD = 0.25  # per-task ceiling for Haiku dev runs
EVAL_MAX_BUDGET_USD = 1.50  # per-task ceiling for Sonnet gate runs, Phase 6
MAX_TOOL_CALLS = 60  # circuit breaker: hard backstop independent of max_turns

MCP_SERVER_NAME = "compliancecheck"
TOOL_NAMES = ["fetch_page", "read_ruleset", "emit_finding"]
QUALIFIED_TOOL_NAMES = [f"mcp__{MCP_SERVER_NAME}__{name}" for name in TOOL_NAMES]
