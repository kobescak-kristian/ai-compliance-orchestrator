"""Real checker agent entry point (BLUEPRINT.md §4, §9 Phase 3): builds
the caged ClaudeAgentOptions, runs one query() per CheckTask, and returns
the collected findings in the same list[dict] shape agents.checker.stub
returns -- so it drops into orchestrator.pipeline.run_check_stage
unchanged, just swapped in for checker_fn.
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

from contracts.schemas import CheckTask
from orchestrator.pipeline import BudgetExceededError

from . import tools
from .audit import audit_hook, init_audit_db, set_run_context
from .config import MAX_BUDGET_USD, MAX_TURNS, MCP_SERVER_NAME, MODEL, QUALIFIED_TOOL_NAMES
from .prompts import build_system_prompt, build_user_prompt

# Populated after each real_checker() call: the ResultMessage from the
# most recent run, for cost/turns reporting (dev-eval leg).
last_result: ResultMessage | None = None


def build_options(
    task: CheckTask,
    ledger_conn: sqlite3.Connection,
    *,
    model: str = MODEL,
    max_budget_usd: float = MAX_BUDGET_USD,
) -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name=MCP_SERVER_NAME, version="1.0.0", tools=tools.build_tools(task, ledger_conn)
    )
    return ClaudeAgentOptions(
        model=model,
        system_prompt=build_system_prompt(task.jurisdiction),
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


async def _run_checker_async(
    task: CheckTask, ledger_conn: sqlite3.Connection, run_id: str, model: str, max_budget_usd: float
) -> list[dict]:
    global last_result
    init_audit_db()
    task_id = f"{task.page_path}::{task.jurisdiction}"
    set_run_context(run_id, task_id)
    tools.reset_run_state()

    options = build_options(task, ledger_conn, model=model, max_budget_usd=max_budget_usd)
    prompt = build_user_prompt(task.page_path, task.jurisdiction, task.assigned_rules)

    result: ResultMessage | None = None
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage):
            result = msg
    last_result = result

    if tools.circuit_breaker_tripped():
        raise BudgetExceededError(f"checker circuit breaker tripped for {task_id}")
    if result is not None and result.is_error:
        raise BudgetExceededError(f"checker run ended in error for {task_id}: {result.subtype}")

    return list(tools.findings)


def real_checker(
    task: CheckTask,
    ledger_conn: sqlite3.Connection,
    run_id: str = "dev-run",
    *,
    model: str = MODEL,
    max_budget_usd: float = MAX_BUDGET_USD,
) -> list[dict]:
    """Signature-compatible with agents.checker.stub.stub_checker once
    ledger_conn/run_id are bound (functools.partial at wiring time):
    (task) -> list[dict].
    """
    return anyio.run(_run_checker_async, task, ledger_conn, run_id, model, max_budget_usd)
