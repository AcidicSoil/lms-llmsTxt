"""Optional RLM-style exploration evaluation scaffolding.

This module does not implement or require a recursive language model. Instead,
it provides deterministic budget enforcement and comparison reporting for an
optional RLM-style exploration candidate so the path can be evaluated before any
optimizer or model-specific integration is adopted.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from .evaluation import BenchmarkComparison, BenchmarkRepository, compare_generation_paths
from .graph_models import RepoSkillGraph
from .models import LLMsDocument
from .repo_digest import RepoDigest


@dataclass(frozen=True, slots=True)
class ExplorationLimits:
    """Hard limits for optional recursive exploration."""

    max_depth: int
    max_files: int
    max_total_chars: int

    def __post_init__(self) -> None:
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        if self.max_files <= 0:
            raise ValueError("max_files must be positive")
        if self.max_total_chars <= 0:
            raise ValueError("max_total_chars must be positive")


@dataclass(frozen=True, slots=True)
class ExplorationCandidate:
    """A file-level exploration candidate with deterministic cost metadata."""

    path: str
    depth: int
    estimated_chars: int
    priority: float = 0.0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ExplorationBudgetReport:
    """Result of applying hard exploration limits to candidate files."""

    limits: ExplorationLimits
    selected_paths: tuple[str, ...]
    skipped_paths: tuple[str, ...]
    total_chars: int
    estimated_tokens: int
    depth_limit_hits: int
    file_limit_hit: bool
    char_limit_hit: bool

    @property
    def within_limits(self) -> bool:
        """Whether selected exploration stayed within every configured hard limit."""

        return (
            len(self.selected_paths) <= self.limits.max_files
            and self.total_chars <= self.limits.max_total_chars
            and self.depth_limit_hits >= 0
        )

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable budget report."""

        return {
            "limits": {
                "max_depth": self.limits.max_depth,
                "max_files": self.limits.max_files,
                "max_total_chars": self.limits.max_total_chars,
            },
            "selected_paths": list(self.selected_paths),
            "skipped_paths": list(self.skipped_paths),
            "total_chars": self.total_chars,
            "estimated_tokens": self.estimated_tokens,
            "depth_limit_hits": self.depth_limit_hits,
            "file_limit_hit": self.file_limit_hit,
            "char_limit_hit": self.char_limit_hit,
            "within_limits": self.within_limits,
        }


@dataclass(frozen=True, slots=True)
class PathCost:
    """Comparable runtime and token-cost signals for one evaluated path."""

    latency_ms: int = 0
    token_count: int = 0

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")

    def as_dict(self) -> dict[str, int]:
        return {"latency_ms": self.latency_ms, "token_count": self.token_count}


@dataclass(frozen=True, slots=True)
class OptionalRLMEvaluationReport:
    """Side-by-side quality, latency, and token-cost comparison."""

    comparison: BenchmarkComparison
    budget: ExplorationBudgetReport
    baseline_cost: PathCost
    rlm_cost: PathCost

    @property
    def latency_delta_ms(self) -> int:
        """RLM-style latency minus baseline latency."""

        return self.rlm_cost.latency_ms - self.baseline_cost.latency_ms

    @property
    def token_delta(self) -> int:
        """RLM-style token count minus baseline token count."""

        return self.rlm_cost.token_count - self.baseline_cost.token_count

    @property
    def quality_delta(self) -> float:
        """RLM-style quality score minus baseline quality score."""

        return self.comparison.score_delta

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable evaluation report."""

        return {
            "comparison": self.comparison.as_dict(),
            "budget": self.budget.as_dict(),
            "baseline_cost": self.baseline_cost.as_dict(),
            "rlm_cost": self.rlm_cost.as_dict(),
            "quality_delta": self.quality_delta,
            "latency_delta_ms": self.latency_delta_ms,
            "token_delta": self.token_delta,
        }


def candidates_from_digest(digest: RepoDigest) -> tuple[ExplorationCandidate, ...]:
    """Create deterministic RLM-style exploration candidates from a repo digest."""

    candidates: list[ExplorationCandidate] = []
    entry_points = set(digest.entry_points)
    seen_paths: set[str] = set()

    for subsystem_index, subsystem in enumerate(digest.subsystems):
        for path_index, path in enumerate(subsystem.get("paths", ())):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            summary = str(subsystem.get("summary", ""))
            key_symbols = subsystem.get("key_symbols", ())
            priority = _candidate_priority(path, path in entry_points, subsystem_index, path_index)
            candidates.append(
                ExplorationCandidate(
                    path=path,
                    depth=_path_depth(path),
                    estimated_chars=max(1_000, len(summary) * 8 + len(key_symbols) * 120),
                    priority=priority,
                    reason=f"subsystem:{subsystem.get('name', 'unknown')}",
                )
            )

    return tuple(sorted(candidates, key=lambda candidate: (-candidate.priority, candidate.path)))


def apply_exploration_limits(
    candidates: tuple[ExplorationCandidate, ...],
    limits: ExplorationLimits,
) -> ExplorationBudgetReport:
    """Apply hard depth, file-count, and total-character limits."""

    selected: list[str] = []
    skipped: list[str] = []
    total_chars = 0
    depth_limit_hits = 0
    file_limit_hit = False
    char_limit_hit = False

    for candidate in sorted(candidates, key=lambda item: (-item.priority, item.path)):
        if candidate.depth > limits.max_depth:
            skipped.append(candidate.path)
            depth_limit_hits += 1
            continue
        if len(selected) >= limits.max_files:
            skipped.append(candidate.path)
            file_limit_hit = True
            continue
        if total_chars + candidate.estimated_chars > limits.max_total_chars:
            skipped.append(candidate.path)
            char_limit_hit = True
            continue

        selected.append(candidate.path)
        total_chars += candidate.estimated_chars

    return ExplorationBudgetReport(
        limits=limits,
        selected_paths=tuple(selected),
        skipped_paths=tuple(skipped),
        total_chars=total_chars,
        estimated_tokens=_estimate_tokens(total_chars),
        depth_limit_hits=depth_limit_hits,
        file_limit_hit=file_limit_hit,
        char_limit_hit=char_limit_hit,
    )


def evaluate_optional_rlm_path(
    benchmark: BenchmarkRepository,
    *,
    baseline_document: LLMsDocument,
    rlm_document: LLMsDocument,
    exploration_candidates: tuple[ExplorationCandidate, ...],
    limits: ExplorationLimits,
    graph: RepoSkillGraph | None = None,
    baseline_cost: PathCost | None = None,
    rlm_latency_ms: int = 0,
) -> OptionalRLMEvaluationReport:
    """Compare baseline output with an optional bounded RLM-style candidate."""

    budget = apply_exploration_limits(exploration_candidates, limits)
    resolved_baseline_cost = baseline_cost or PathCost()
    resolved_rlm_cost = PathCost(latency_ms=rlm_latency_ms, token_count=budget.estimated_tokens)
    comparison = compare_generation_paths(
        benchmark,
        baseline=baseline_document,
        candidate=rlm_document,
        graph=graph,
        baseline_name="selective-planning-baseline",
        candidate_name="optional-rlm-style",
    )
    return OptionalRLMEvaluationReport(
        comparison=comparison,
        budget=budget,
        baseline_cost=resolved_baseline_cost,
        rlm_cost=resolved_rlm_cost,
    )


def _candidate_priority(path: str, is_entry_point: bool, subsystem_index: int, path_index: int) -> float:
    priority = 100.0 - subsystem_index - (path_index / 10)
    if is_entry_point:
        priority += 50.0
    if "/test" in path or path.startswith("tests/"):
        priority -= 10.0
    return priority


def _path_depth(path: str) -> int:
    return max(0, path.strip("/").count("/"))


def _estimate_tokens(total_chars: int) -> int:
    return ceil(total_chars / 4)
