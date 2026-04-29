from lms_llmsTxt.evaluation import BenchmarkRepository, compare_generation_paths, evaluate_llms_document
from lms_llmsTxt.graph_builder import build_repo_graph
from lms_llmsTxt.models import LLMsDocument, LLMsLinkEntry, LLMsSection
from lms_llmsTxt.repo_digest import RepoDigest


def _doc(*sections: LLMsSection) -> LLMsDocument:
    return LLMsDocument(
        project_name="Example",
        project_purpose="Example purpose",
        remember_bullets=["Start with onboarding."],
        sections=list(sections),
    )


def test_evaluate_llms_document_scores_expected_metrics_with_graph_artifacts():
    benchmark = BenchmarkRepository(
        name="python-service",
        expected_sections=("Getting Started", "API Reference", "Testing"),
        required_links=("docs/getting-started.md", "src/api.py"),
        expected_subsystems=("api", "tests"),
        expected_api_terms=("RepositoryAnalyzer", "generate"),
        large_repo_min_sections=3,
    )
    document = _doc(
        LLMsSection(
            name="Getting Started",
            entries=[LLMsLinkEntry("Quickstart", "docs/getting-started.md", "Start here")],
        ),
        LLMsSection(
            name="API Reference",
            entries=[LLMsLinkEntry("RepositoryAnalyzer", "src/api.py", "Use generate for llms.txt output")],
        ),
        LLMsSection(
            name="Testing",
            entries=[LLMsLinkEntry("Pytest", "tests/test_api.py", "Regression tests")],
        ),
    )
    graph = build_repo_graph(
        RepoDigest(
            topic="Example",
            architecture_summary="API and tests",
            primary_language="python",
            subsystems=[
                {"name": "api", "paths": ["src/api.py"], "summary": "API layer", "key_symbols": ["generate"]},
                {"name": "tests", "paths": ["tests/test_api.py"], "summary": "Tests", "key_symbols": []},
            ],
            key_dependencies=[],
            entry_points=["src/api.py"],
            test_coverage_hint="has_tests",
            digest_id="abc123",
        )
    )

    result = evaluate_llms_document(benchmark, document, path_name="current", graph=graph)

    assert result.metrics.onboarding_usefulness == 1.0
    assert result.metrics.api_coverage_quality == 1.0
    assert result.metrics.doc_link_precision == 2 / 3
    assert result.metrics.large_repository_resilience == 1.0
    assert result.metrics.graph_subsystem_coverage == 1.0
    assert result.metrics.graph_hotspot_alignment == 1.0
    assert result.metrics.graph_omission_count == 0
    assert result.omissions == ()
    assert result.as_dict()["metrics"]["overall_score"] > 0.8


def test_evaluate_llms_document_surfaces_omissions_and_redundancy():
    benchmark = BenchmarkRepository(
        name="large-repo",
        expected_sections=("Subsystem A", "Subsystem B"),
        required_links=("docs/subsystem-b.md",),
        expected_subsystems=("subsystem b",),
        expected_api_terms=("configure",),
        large_repo_min_sections=4,
    )
    document = _doc(
        LLMsSection(
            name="Subsystem A",
            entries=[
                LLMsLinkEntry("Overview", "docs/subsystem-a.md", "Overview"),
                LLMsLinkEntry("Duplicate", "docs/subsystem-a.md", "Duplicate"),
            ],
        )
    )
    graph = build_repo_graph(
        RepoDigest(
            topic="Example",
            architecture_summary="Only subsystem A is present",
            primary_language="python",
            subsystems=[
                {"name": "subsystem a", "paths": ["src/a.py"], "summary": "A", "key_symbols": []},
            ],
            key_dependencies=[],
            entry_points=[],
            test_coverage_hint="partial",
            digest_id="def456",
        )
    )

    result = evaluate_llms_document(benchmark, document, path_name="baseline", graph=graph)

    assert result.metrics.onboarding_usefulness == 0.5
    assert result.metrics.api_coverage_quality == 0.0
    assert result.metrics.doc_link_precision == 0.0
    assert result.metrics.redundancy_penalty == 0.5
    assert result.metrics.large_repository_resilience == 0.25
    assert result.metrics.graph_subsystem_coverage == 0.0
    assert result.metrics.graph_hotspot_alignment == 0.0
    assert result.metrics.graph_omission_count == 2
    assert "missing section: Subsystem B" in result.omissions
    assert "missing API term: configure" in result.omissions
    assert "missing required link: docs/subsystem-b.md" in result.omissions
    assert "graph omission: subsystem b" in result.omissions
    assert "document omits graph subsystem: subsystem b" in result.omissions


def test_compare_generation_paths_reports_candidate_score_delta():
    benchmark = BenchmarkRepository(
        name="comparison",
        expected_sections=("API",),
        required_links=("src/api.py",),
        expected_api_terms=("generate",),
    )
    baseline = _doc(LLMsSection(name="Overview", entries=[]))
    candidate = _doc(
        LLMsSection(
            name="API",
            entries=[LLMsLinkEntry("Generator", "src/api.py", "generate output")],
        )
    )

    comparison = compare_generation_paths(benchmark, baseline=baseline, candidate=candidate)

    assert comparison.baseline.path_name == "baseline"
    assert comparison.candidate.path_name == "candidate"
    assert comparison.score_delta > 0
    assert comparison.as_dict()["score_delta"] == comparison.score_delta
