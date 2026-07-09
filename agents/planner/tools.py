"""The 3 in-process MCP tools available to the planner agent
(BLUEPRINT.md §4): read_finding, read_rule, emit_proposal. Built fresh
per finding via build_tools() so each run is bound to exactly one
CONFIRMED VIOLATION finding and its rule -- there is no way for a tool
call to reach a sibling finding, another rule, a page, or the
filesystem.

Blindness (this Phase-5 instruction, mirroring the verifier's own
policy/ADJUDICATION_POLICY.md §2 bounds, applied here to the planner):
read_finding never returns the checker's rationale or any verifier
citation -- only page_path, jurisdiction, rule_id, and the verbatim
evidence excerpt, the bare anchor a remediation needs. read_rule rejects
any rule_id other than the bound finding's own, so a sibling finding's
rule is never reachable through this tool either.

Read-only by construction except emit_proposal, which only ever appends
to an in-memory slot: nothing here can fetch a page, write a file, or
approve/reject anything -- there is no such tool in this module, so
self-approval is impossible at the API surface, not merely forbidden by
instruction.
"""
from __future__ import annotations

from claude_agent_sdk import tool
from pydantic import ValidationError

from contracts.schemas import ComplianceRule, RemediationProposal, ViolationFinding

from .config import MAX_TOOL_CALLS

# Populated by emit_proposal during a run; harness.py reads it after
# query() completes. Reset by reset_run_state() before each run -- safe
# as module state because findings are processed sequentially, never
# concurrently (same rationale as the checker's tools.py).
proposal: dict | None = None

_tool_call_count = 0
_circuit_breaker_tripped_flag = False


def reset_run_state() -> None:
    """Call before each finding's run: clears the proposal slot and the
    circuit-breaker counter/flag."""
    global proposal, _tool_call_count, _circuit_breaker_tripped_flag
    proposal = None
    _tool_call_count = 0
    _circuit_breaker_tripped_flag = False


def circuit_breaker_tripped() -> bool:
    """Read after a run completes: True if MAX_TOOL_CALLS was hit during
    it. harness.py uses this to raise BudgetExceededError (FI-1)."""
    return _circuit_breaker_tripped_flag


def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}], "is_error": True}


def _check_circuit_breaker() -> dict | None:
    """Hard backstop on total tool calls for this run, independent of
    max_turns (BLUEPRINT.md §3: "call-count circuit breaker")."""
    global _tool_call_count, _circuit_breaker_tripped_flag
    _tool_call_count += 1
    if _tool_call_count > MAX_TOOL_CALLS:
        _circuit_breaker_tripped_flag = True
        return _error(
            f"Circuit breaker tripped: tool-call ceiling ({MAX_TOOL_CALLS}) "
            "reached for this run. No further tool calls will be served."
        )
    return None


def build_tools(finding: ViolationFinding, rule: ComplianceRule, run_id: str):
    """Build the 3 tools bound to exactly one finding/rule/run. Neither
    the finding nor the rule can be swapped for another at call time,
    whatever the agent asks for.
    """

    @tool(
        "read_finding",
        "Read the compliance finding you have been assigned to remediate. "
        "Returns its page path, jurisdiction, rule ID, and the verbatim "
        "evidence excerpt that violates the rule. Takes no arguments.",
        {},
    )
    async def read_finding(args):
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped
        text = (
            f"page_path: {finding.page_path}\n"
            f"jurisdiction: {finding.jurisdiction}\n"
            f"rule_id: {finding.rule_id}\n"
            f"evidence_excerpt: {finding.evidence_excerpt}"
        )
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "read_rule",
        "Read the full text of the rule this finding violates. The "
        "rule_id argument must equal the finding's own rule_id -- "
        "requesting any other rule is rejected and logged.",
        {"rule_id": str},
    )
    async def read_rule(args):
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped
        requested = args.get("rule_id")
        if requested != rule.rule_id:
            return _error(
                f"rule_id {requested!r} is not the assigned finding's rule "
                f"({rule.rule_id!r}) -- rejected."
            )
        text = f"{rule.rule_id} | {rule.category.value} | {rule.severity.value} | {rule.rule_text}"
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "emit_proposal",
        "Record your remediation for this finding: the proposed compliant "
        "replacement text for the offending excerpt. Call this once, "
        "after reading the finding and its rule, then stop.",
        {"proposed_text": str},
    )
    async def emit_proposal(args):
        global proposal
        tripped = _check_circuit_breaker()
        if tripped:
            return tripped

        raw = {
            "page_path": finding.page_path,
            "rule_id": finding.rule_id,
            "offending_text": finding.evidence_excerpt,
            "proposed_text": args.get("proposed_text"),
            "evidence_refs": [finding.task_id],
            "created_by_run_id": run_id,
        }
        try:
            RemediationProposal(**raw)
        except ValidationError as e:
            # Tool-boundary validation (BLUEPRINT.md §3): reject immediately
            # so the agent can retry within its turn budget. The orchestrator
            # re-validates independently at the plan-stage boundary.
            return _error(f"Invalid proposal, not recorded: {e}")

        proposal = raw
        return {"content": [{"type": "text", "text": "Proposal recorded."}]}

    return [read_finding, read_rule, emit_proposal]
