"""LLM agent nodes: checker (per-jurisdiction) and planner (proposal-only).
Every agent here is caged: allowed_tools whitelist, max_turns cap,
per-run budget ceiling + call-count circuit breaker, PreToolUse/PostToolUse
audit hooks (BLUEPRINT.md §3, reusing the ai-claim-verification-agent
agent/audit.py pattern directly).
"""
