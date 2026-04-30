"""Deterministic llms.txt benchmark evaluation helpers.

The evaluator is intentionally model-free: it scores already-produced structured
``LLMsDocument`` objects against benchmark expectations and optional graph
artifacts so optimizer work can compare candidate generation paths without
changing artifact contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from .graph_models import RepoSkillGraph
from .models import LLMsDocument


@dataclass(frozen=True, slots=True)
class BenchmarkRepository:
    """Expected quality signals for a repository benchmark case."""

    name: str
    expected_sections: tuple[str, ...] = ()
    required_links: tuple[str, ...] = ()
    expected_subsystems: tuple[str, ...] = ()
    expected_api_terms: tuple[str, ...] = ()
    large_repo_min_sections: int = 0


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Comparable quality metrics for one generated llms.txt document."""

    onboarding_usefulness: float
    api_coverage_quality: float
    doc_link_precision: float
    redundancy_penalty: float
    large_repository_resilience: float
    graph_subsystem_coverage: float
    graph_hotspot_alignment: float
    graph_omission_count: int

    @property
    def overall_score(self) -> float:
        """Aggregate positive quality signals minus the redundancy penalty."""

        positive_scores = (
            self.onboarding_usefulness,
            self.api_coverage_quality,
            self.doc_link_precision,
            self.large_repository_resilience,
            self.graph_subsystem_coverage,
            self.graph_hotspot_alignment,
        )
        return max(0.0, min(1.0, mean(positive_scores) - self.redundancy_penalty))


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Evaluation output for a single benchmark repository and generation path."""

    benchmark_name: str
    path_name: str
    metrics: EvaluationMetrics
    omissions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable representation."""

        return {
            "benchmark_name": self.benchmark_name,
            "path_name": self.path_name,
            "metrics": {
                "onboarding_usefulness": self.metrics.onboarding_usefulness,
                "api_coverage_quality": self.metrics.api_coverage_quality,
                "doc_link_precision": self.metrics.doc_link_precision,
                "redundancy_penalty": self.metrics.redundancy_penalty,
                "large_repository_resilience": self.metrics.large_repository_resilience,
                "graph_subsystem_coverage": self.metrics.graph_subsystem_coverage,
                "graph_hotspot_alignment": self.metrics.graph_hotspot_alignment,
                "graph_omission_count": self.metrics.graph_omission_count,
                "overall_score": self.metrics.overall_score,
            },
            "omissions": list(self.omissions),
        }


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Comparable baseline/refactored evaluation pair."""

    baseline: EvaluationResult
    candidate: EvaluationResult

    @property
    def score_delta(self) -> float:
        """Candidate overall score minus baseline overall score."""

        return self.candidate.metrics.overall_score - self.baseline.metrics.overall_score

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable comparison summary."""

        return {
            "baseline": self.baseline.as_dict(),
            "candidate": self.candidate.as_dict(),
            "score_delta": self.score_delta,
        }


def evaluate_llms_document(
    benchmark: BenchmarkRepository,
    document: LLMsDocument,
    *,
    path_name: str,
    graph: RepoSkillGraph | None = None,
) -> EvaluationResult:
    """Score a structured llms.txt document against deterministic expectations."""

    normalized_sections = tuple(_normalize(section.name) for section in document.sections)
    normalized_links = tuple(_normalize(entry.url) for section in document.sections for entry in section.entries)
    normalized_titles = tuple(_normalize(entry.title) for section in document.sections for entry in section.entries)
    normalized_notes = tuple(_normalize(entry.note) for section in document.sections for entry in section.entries)
    text_terms = normalized_sections + normalized_titles + normalized_notes

    section_coverage, missing_sections = _coverage(benchmark.expected_sections, normalized_sections)
    api_coverage, missing_api_terms = _term_coverage(benchmark.expected_api_terms, text_terms)
    link_precision, missing_links = _link_precision(benchmark.required_links, normalized_links)
    redundancy_penalty = _redundancy_penalty(normalized_links)
    large_repo_resilience = _large_repo_resilience(benchmark.large_repo_min_sections, len(document.sections))
    graph_coverage, graph_alignment, graph_omissions = _graph_metrics(benchmark, text_terms + normalized_links, graph)

    omissions = tuple(missing_sections + missing_api_terms + missing_links + graph_omissions)
    return EvaluationResult(
        benchmark_name=benchmark.name,
        path_name=path_name,
        metrics=EvaluationMetrics(
            onboarding_usefulness=section_coverage,
            api_coverage_quality=api_coverage,
            doc_link_precision=link_precision,
            redundancy_penalty=redundancy_penalty,
            large_repository_resilience=large_repo_resilience,
            graph_subsystem_coverage=graph_coverage,
            graph_hotspot_alignment=graph_alignment,
            graph_omission_count=len(graph_omissions),
        ),
        omissions=omissions,
    )


def compare_generation_paths(
    benchmark: BenchmarkRepository,
    *,
    baseline: LLMsDocument,
    candidate: LLMsDocument,
    graph: RepoSkillGraph | None = None,
    baseline_name: str = "baseline",
    candidate_name: str = "candidate",
) -> BenchmarkComparison:
    """Evaluate two generation paths with the same benchmark expectations."""

    return BenchmarkComparison(
        baseline=evaluate_llms_document(benchmark, baseline, path_name=baseline_name, graph=graph),
        candidate=evaluate_llms_document(benchmark, candidate, path_name=candidate_name, graph=graph),
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _coverage(expected: tuple[str, ...], observed: tuple[str, ...]) -> tuple[float, list[str]]:
    if not expected:
        return 1.0, []
    observed_set = set(observed)
    missing = [item for item in expected if _normalize(item) not in observed_set]
    return (len(expected) - len(missing)) / len(expected), [f"missing section: {item}" for item in missing]


def _term_coverage(expected_terms: tuple[str, ...], observed_text: tuple[str, ...]) -> tuple[float, list[str]]:
    if not expected_terms:
        return 1.0, []
    missing: list[str] = []
    for term in expected_terms:
        normalized_term = _normalize(term)
        if not any(normalized_term in text for text in observed_text):
            missing.append(term)
    return (len(expected_terms) - len(missing)) / len(expected_terms), [f"missing API term: {item}" for item in missing]


def _link_precision(required_links: tuple[str, ...], observed_links: tuple[str, ...]) -> tuple[float, list[str]]:
    if not observed_links:
        return (0.0 if required_links else 1.0), [f"missing required link: {link}" for link in required_links]

    required = tuple(_normalize(link) for link in required_links)
    if not required:
        return 1.0, []

    matching = sum(1 for link in observed_links if any(required_link in link for required_link in required))
    missing = [link for link in required_links if not any(_normalize(link) in observed for observed in observed_links)]
    return matching / len(observed_links), [f"missing required link: {link}" for link in missing]


def _redundancy_penalty(observed_links: tuple[str, ...]) -> float:
    if not observed_links:
        return 0.0
    duplicates = len(observed_links) - len(set(observed_links))
    return duplicates / len(observed_links)


def _large_repo_resilience(min_sections: int, observed_section_count: int) -> float:
    if min_sections <= 0:
        return 1.0
    return min(1.0, observed_section_count / min_sections)


def _graph_metrics(
    benchmark: BenchmarkRepository,
    document_terms: tuple[str, ...],
    graph: RepoSkillGraph | None,
) -> tuple[float, float, list[str]]:
    if graph is None or not benchmark.expected_subsystems:
        return 1.0, 1.0, []

    subsystem_names = tuple(_normalize(name) for name in benchmark.expected_subsystems)
    graph_labels = tuple(_normalize(node.label) for node in graph.nodes if node.type != "moc")
    graph_node_ids = tuple(_normalize(node.id).replace("-", " ") for node in graph.nodes if node.type != "moc")
    graph_terms = graph_labels + graph_node_ids

    missing_from_graph = [
        subsystem for subsystem in benchmark.expected_subsystems if not any(_normalize(subsystem) in term for term in graph_terms)
    ]
    covered_by_document = [
        subsystem for subsystem in subsystem_names if any(subsystem in term for term in document_terms)
    ]

    graph_coverage = (len(subsystem_names) - len(missing_from_graph)) / len(subsystem_names)
    graph_alignment = len(covered_by_document) / len(subsystem_names)
    omissions = [f"graph omission: {item}" for item in missing_from_graph]
    omissions.extend(
        f"document omits graph subsystem: {item}"
        for item in benchmark.expected_subsystems
        if _normalize(item) not in covered_by_document
    )
    return graph_coverage, graph_alignment, omissions
