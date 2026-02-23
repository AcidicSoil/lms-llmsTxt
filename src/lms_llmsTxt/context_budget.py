from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class BudgetDecision(str, Enum):
    APPROVED = "approved"
    NEEDS_COMPACTION = "needs_compaction"
    REJECTED = "rejected"


@dataclass(slots=True)
class ContextBudget:
    max_context_tokens: int
    reserved_output_tokens: int
    headroom_ratio: float
    estimated_prompt_tokens: int = 0
    available_tokens: int = 0
    decision: BudgetDecision = BudgetDecision.APPROVED
    component_estimates: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover
    tiktoken = None


def estimate_tokens(text: str) -> int:
    data = text or ""
    if not data:
        return 0
    if tiktoken is None:
        return max(1, len(data) // 4)
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(data))
    except Exception:
        return max(1, len(data) // 4)


def _truncate_chars(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def _trim_file_tree(tree: str, max_lines: int) -> str:
    if max_lines <= 0:
        return ""
    lines = tree.splitlines()
    if len(lines) <= max_lines:
        return tree
    return "\n".join(lines[:max_lines])


def build_context_budget(config: Any, material: Any) -> ContextBudget:
    max_context_tokens = int(getattr(config, "max_context_tokens", 32768))
    reserved_output_tokens = int(getattr(config, "max_output_tokens", 4096))
    headroom_ratio = float(getattr(config, "context_headroom_ratio", 0.15))

    file_tree = _trim_file_tree(
        str(getattr(material, "file_tree", "") or ""),
        int(getattr(config, "max_file_tree_lines", 1200)),
    )
    readme = _truncate_chars(
        str(getattr(material, "readme_content", "") or ""),
        int(getattr(config, "max_readme_chars", 24000)),
    )
    packages = _truncate_chars(
        str(getattr(material, "package_files", "") or ""),
        int(getattr(config, "max_package_chars", 18000)),
    )

    component_estimates = {
        "file_tree": estimate_tokens(file_tree),
        "readme_content": estimate_tokens(readme),
        "package_files": estimate_tokens(packages),
    }

    estimated = sum(component_estimates.values())
    headroom_tokens = int(max_context_tokens * headroom_ratio)
    available = max(0, max_context_tokens - reserved_output_tokens - headroom_tokens)

    budget = ContextBudget(
        max_context_tokens=max_context_tokens,
        reserved_output_tokens=reserved_output_tokens,
        headroom_ratio=headroom_ratio,
        estimated_prompt_tokens=estimated,
        available_tokens=available,
        component_estimates=component_estimates,
    )
    budget.decision = validate_budget(budget)
    return budget


def validate_budget(budget: ContextBudget) -> BudgetDecision:
    if budget.estimated_prompt_tokens <= budget.available_tokens:
        return BudgetDecision.APPROVED
    if budget.available_tokens > 0 and budget.estimated_prompt_tokens <= budget.available_tokens * 2:
        return BudgetDecision.NEEDS_COMPACTION
    return BudgetDecision.REJECTED
