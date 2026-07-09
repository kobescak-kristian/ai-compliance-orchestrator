"""Real planner agent entry point (BLUEPRINT.md §4, §9 Phase 5): builds
the caged ClaudeAgentOptions, runs one query() per finding, and returns
its proposal (or None) as the same dict|None shape agents.planner.stub
returns -- so it drops into orchestrator.pipeline.run_plan_stage
unchanged, just swapped in for planner_fn via agents.planner.select.
"""
from __future__ import annotations

import sqlite3

import anyio
from claude_agent_sdk import (
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    create_sdk_mcp_server,
    query,
)

from contracts.schemas import ComplianceRule, ViolationFinding
from orchestrator.pipeline import BudgetExceededError

from . import tools
from .audit import audit_hook, init_audit_db, set_run_context
from .config import MAX_BUDGET_USD, MAX_TURNS, MCP_SERVER_NAME, MODEL, QUALIFIED_TOOL_NAMES
from .prompts import build_system_prompt, build_user_prompt

# Populated after each real_planner() call: the ResultMessage from the
# most recent run, for cost/turns reporting (dev-eval leg).
last_result: ResultMessage | None = None

# Populated by every real_planner() call: {finding_id, cost_usd,
# num_turns} -- dev/eval-leg cost+turns reporting only (BLUEPRINT.md
# §7), mirrors nodes/verifier.py's run_stats convention.
run_stats: list[dict] = []


def reset_run_stats() -> None:
    run_stats.clear()


def build_options(
    finding: ViolationFinding,
    rule: ComplianceRule,
    run_id: str,
    *,
    model: str = MODEL,
    max_budget_usd: float = MAX_BUDGET_USD,
) -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name=MCP_SERVER_NAME, version="1.0.0", tools=tools.build_tools(finding, rule, run_id)
    )
    return ClaudeAgentOptions(
        model=model,
        system_prompt=build_system_prompt(),
        tools=[],  # disable all built-in tools (no Write, Bash, Edit, Read, ...)
        mcp_servers={MCP_SERVER_NAME: server},
        allowed_tools=list(QUALIFIED_TOOL_NAMES),  # exactly the 3 custom tools
        max_turns=MAX_TURNS,
        max_budget_usd=max_budget_usd,  # SDK-level per-run cost ceiling
        hooks={
            "PreToolUse": [HookMatcher(hooks=[audit_hook])],
            "PostToolUse": [HookMatcher(hooks=[audit_hook])],
        },
    )


async def _run_planner_async(
    finding: ViolationFinding,
    rule: ComplianceRule,
    run_id: str,
    model: str,
    max_budget_usd: float,
) -> dict | None:
    global last_result
    init_audit_db()
    finding_id = f"{finding.task_id}::{finding.rule_id}"
    set_run_context(run_id, finding_id)
    tools.reset_run_state()

    options = build_options(finding, rule, run_id, model=model, max_budget_usd=max_budget_usd)
    prompt = build_user_prompt(finding.rule_id)

    result: ResultMessage | None = None
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage):
            result = msg
    last_result = result
    run_stats.append(
        {
            "finding_id": finding_id,
            "cost_usd": result.total_cost_usd if result is not None else None,
            "num_turns": result.num_turns if result is not None else None,
        }
    )

    if tools.circuit_breaker_tripped():
        raise BudgetExceededError(f"planner circuit breaker tripped for {finding_id}")
    if result is not None and result.is_error:
        raise BudgetExceededError(f"planner run ended in error for {finding_id}: {result.subtype}")

    return tools.proposal


def real_planner(
    finding: ViolationFinding,
    ledger_conn: sqlite3.Connection,
    run_id: str,
    rules_by_id: dict[str, ComplianceRule],
    *,
    model: str = MODEL,
    max_budget_usd: float = MAX_BUDGET_USD,
) -> dict | None:
    """Signature-compatible with agents.planner.stub.stub_planner once
    ledger_conn/run_id/rules_by_id are bound (functools.partial at wiring
    time, agents.planner.select.get_planner_fn): (finding) -> dict|None.
    ledger_conn is accepted for interface symmetry with the checker/
    verifier real_* functions and future audit-table use; the planner's
    own tools write to audit.db directly and do not use it yet.
    """
    rule = rules_by_id[finding.rule_id]
    return anyio.run(_run_planner_async, finding, rule, run_id, model, max_budget_usd)
