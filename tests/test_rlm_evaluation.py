import pytest

from lms_llmsTxt.evaluation import BenchmarkRepository
from lms_llmsTxt.models import LLMsDocument, LLMsLinkEntry, LLMsSection
from lms_llmsTxt.repo_digest import RepoDigest
from lms_llmsTxt.rlm_evaluation import (
    ExplorationCandidate,
    ExplorationLimits,
    PathCost,
    apply_exploration_limits,
    candidates_from_digest,
    evaluate_optional_rlm_path,
)


def _doc(*sections: LLMsSection) -> LLMsDocument:
    return LLMsDocument(
        project_name="Large Repo",
        project_purpose="Evaluate exploration quality",
        remember_bullets=[],
        sections=list(sections),
    )


def test_apply_exploration_limits_enforces_depth_file_and_char_budgets():
    candidates = (
        ExplorationCandidate("src/api.py", depth=1, estimated_chars=1_000, priority=10),
        ExplorationCandidate("src/deep/nested/worker.py", depth=3, estimated_chars=500, priority=9),
        ExplorationCandidate("src/service.py", depth=1, estimated_chars=900, priority=8),
        ExplorationCandidate("src/too-large.py", depth=1, estimated_chars=2_000, priority=7),
    )
    limits = ExplorationLimits(max_depth=2, max_files=2, max_total_chars=1_800)

    report = apply_exploration_limits(candidates, limits)

    assert report.selected_paths == ("src/api.py",)
    assert "src/deep/nested/worker.py" in report.skipped_paths
    assert "src/service.py" in report.skipped_paths
    assert "src/too-large.py" in report.skipped_paths
    assert report.depth_limit_hits == 1
    assert report.char_limit_hit is True
    assert report.file_limit_hit is False
    assert report.total_chars == 1_000
    assert report.estimated_tokens == 250
    assert report.within_limits is True


def test_candidates_from_digest_prioritizes_entry_points_and_deduplicates_paths():
    digest = RepoDigest(
        topic="Example",
        architecture_summary="API and worker",
        primary_language="python",
        subsystems=[
            {
                "name": "worker",
                "paths": ["src/worker.py", "src/api.py"],
                "summary": "Worker subsystem",
                "key_symbols": ["run"],
            },
            {
                "name": "api",
                "paths": ["src/api.py", "tests/test_api.py"],
                "summary": "API subsystem",
                "key_symbols": ["generate"],
            },
        ],
        key_dependencies=[],
        entry_points=["src/api.py"],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    candidates = candidates_from_digest(digest)

    assert [candidate.path for candidate in candidates].count("src/api.py") == 1
    assert candidates[0].path == "src/api.py"
    assert all(candidate.estimated_chars >= 1_000 for candidate in candidates)


def test_evaluate_optional_rlm_path_reuses_benchmark_metrics_and_records_costs():
    benchmark = BenchmarkRepository(
        name="large-python-repo",
        expected_sections=("API", "Worker"),
        required_links=("src/api.py", "src/worker.py"),
        expected_api_terms=("generate", "run"),
        large_repo_min_sections=2,
    )
    baseline = _doc(
        LLMsSection(
            name="API",
            entries=[LLMsLinkEntry("API", "src/api.py", "generate output")],
        )
    )
    rlm_candidate = _doc(
        LLMsSection(
            name="API",
            entries=[LLMsLinkEntry("API", "src/api.py", "generate output")],
        ),
        LLMsSection(
            name="Worker",
            entries=[LLMsLinkEntry("Worker", "src/worker.py", "run background jobs")],
        ),
    )
    candidates = (
        ExplorationCandidate("src/api.py", depth=1, estimated_chars=1_000, priority=10),
        ExplorationCandidate("src/worker.py", depth=1, estimated_chars=1_200, priority=9),
    )

    report = evaluate_optional_rlm_path(
        benchmark,
        baseline_document=baseline,
        rlm_document=rlm_candidate,
        exploration_candidates=candidates,
        limits=ExplorationLimits(max_depth=2, max_files=5, max_total_chars=5_000),
        baseline_cost=PathCost(latency_ms=100, token_count=200),
        rlm_latency_ms=250,
    )

    assert report.comparison.baseline.path_name == "selective-planning-baseline"
    assert report.comparison.candidate.path_name == "optional-rlm-style"
    assert report.quality_delta > 0
    assert report.latency_delta_ms == 150
    assert report.token_delta == 350
    assert report.budget.selected_paths == ("src/api.py", "src/worker.py")
    assert report.as_dict()["budget"]["within_limits"] is True


@pytest.mark.parametrize(
    "limits",
    [
        {"max_depth": -1, "max_files": 1, "max_total_chars": 1},
        {"max_depth": 1, "max_files": 0, "max_total_chars": 1},
        {"max_depth": 1, "max_files": 1, "max_total_chars": 0},
    ],
)
def test_exploration_limits_reject_invalid_values(limits):
    with pytest.raises(ValueError):
        ExplorationLimits(**limits)
