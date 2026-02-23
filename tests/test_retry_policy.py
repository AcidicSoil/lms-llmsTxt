from lms_llmsTxt.context_budget import ContextBudget
from lms_llmsTxt.retry_policy import ErrorClass, classify_generation_error, next_retry_budget


def test_error_classification():
    assert classify_generation_error(Exception("context_length_exceeded")) == ErrorClass.CONTEXT_LENGTH
    assert classify_generation_error(Exception("413 payload too large")) == ErrorClass.PAYLOAD_LIMIT
    assert classify_generation_error(Exception("429 too many requests")) == ErrorClass.RATE_LIMIT
    assert classify_generation_error(Exception("other")) == ErrorClass.UNKNOWN


def test_next_retry_budget_scales_values():
    budget = ContextBudget(
        max_context_tokens=1000,
        reserved_output_tokens=100,
        headroom_ratio=0.1,
        estimated_prompt_tokens=800,
        available_tokens=700,
        component_estimates={"a": 100},
    )
    reduced = next_retry_budget(budget, 0)
    assert reduced is not None
    assert reduced.max_context_tokens == 700
    assert reduced.component_estimates["a"] == 70
    assert next_retry_budget(budget, 5) is None
