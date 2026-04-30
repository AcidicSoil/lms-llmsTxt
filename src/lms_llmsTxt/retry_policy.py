from __future__ import annotations

from dataclasses import replace
from enum import Enum

from .context_budget import ContextBudget


class ErrorClass(str, Enum):
    CONTEXT_LENGTH = "context_length"
    PAYLOAD_LIMIT = "payload_limit"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


_CONTEXT_PATTERNS = (
    "context_length_exceeded",
    "maximum context",
    "context window",
    "too many tokens",
    "input too long",
)
_PAYLOAD_PATTERNS = (
    "413",
    "payload too large",
    "request entity too large",
)
_RATE_LIMIT_PATTERNS = (
    "429",
    "rate limit",
    "too many requests",
)


def classify_generation_error(exc: Exception) -> ErrorClass:
    msg = str(exc).lower()
    if any(token in msg for token in _CONTEXT_PATTERNS):
        return ErrorClass.CONTEXT_LENGTH
    if any(token in msg for token in _PAYLOAD_PATTERNS):
        return ErrorClass.PAYLOAD_LIMIT
    if any(token in msg for token in _RATE_LIMIT_PATTERNS):
        return ErrorClass.RATE_LIMIT
    return ErrorClass.UNKNOWN


def next_retry_budget(
    previous_budget: ContextBudget,
    step: int,
    reduction_steps: tuple[float, ...] | list[float] = (0.70, 0.50),
) -> ContextBudget | None:
    if step >= len(reduction_steps):
        return None
    ratio = float(reduction_steps[step])
    if ratio <= 0 or ratio >= 1:
        return None

    next_components = {
        k: max(1, int(v * ratio)) if v > 0 else 0
        for k, v in previous_budget.component_estimates.items()
    }
    return replace(
        previous_budget,
        max_context_tokens=max(1, int(previous_budget.max_context_tokens * ratio)),
        estimated_prompt_tokens=max(1, int(previous_budget.estimated_prompt_tokens * ratio)),
        available_tokens=max(1, int(previous_budget.available_tokens * ratio)),
        component_estimates=next_components,
    )
