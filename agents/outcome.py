"""Maps how an agent run ended to the exception the stage runners
classify (D6; orchestrator/pipeline.py _error_class). Shared by the
checker and planner harnesses. Pure function of the SDK's message
fields, so it is testable without a model call.
"""
from __future__ import annotations

from orchestrator.pipeline import BudgetExceededError, ProviderError

BUDGET_SUBTYPES = {"error_max_turns", "error_max_budget_usd"}
# AssistantMessage.error values that are provider-side, not the agent's.
PROVIDER_ASSISTANT_ERRORS = {"authentication_failed", "rate_limit", "billing_error"}
# ResultMessage.api_error_status codes: auth, forbidden, rate limit, overload.
PROVIDER_STATUS_CODES = {401, 403, 429, 529}


class AgentRunError(Exception):
    """An agent run ended in error for any other reason (AGENT_ERROR)."""


def raise_for_outcome(label: str, result, assistant_errors: list[str]) -> None:
    """Raise the matching exception if the run did not end cleanly.
    result is the run's ResultMessage (or None); assistant_errors are the
    non-empty AssistantMessage.error values seen during the run."""
    for err in assistant_errors:
        if err in PROVIDER_ASSISTANT_ERRORS:
            raise ProviderError(f"{label}: provider error {err}")
    if result is None:
        if assistant_errors:
            raise AgentRunError(f"{label}: run ended with assistant error {assistant_errors[-1]}")
        return
    status = getattr(result, "api_error_status", None)
    if status in PROVIDER_STATUS_CODES:
        raise ProviderError(f"{label}: provider api_error_status={status}")
    if not result.is_error:
        return
    if result.subtype in BUDGET_SUBTYPES:
        raise BudgetExceededError(f"{label}: run ended in error: {result.subtype}")
    raise AgentRunError(f"{label}: run ended in error: {result.subtype}")
