from __future__ import annotations

from lms_llmsTxt import analyzer
from lms_llmsTxt.repo_digest import RepoDigest


def test_build_dynamic_buckets_uses_default_branch_and_filters_dead_links(monkeypatch):
    recorded = []

    def fake_construct(repo_url, path, ref=None, style="blob"):
        recorded.append((repo_url, path, ref, style))
        return f"https://example.com/{ref or 'none'}/{path}"

    monkeypatch.setattr(analyzer, "construct_github_file_url", fake_construct)
    monkeypatch.setattr(analyzer, "_url_alive", lambda url: "keep" in url)

    file_tree = "docs/keep.md\nREADME.md\ntrash/missing.md"
    buckets = analyzer.build_dynamic_buckets(
        "https://github.com/example/repo",
        file_tree,
        default_ref="custom-branch",
        validate_urls=True,
    )

    # Only the URL containing 'keep' should remain after validation.
    assert any("keep.md" in url for _, items in buckets for _, url, _ in items)
    assert all("missing.md" not in url for _, items in buckets for _, url, _ in items)
    # construct_raw_url should receive the explicit default branch.
    assert all(ref == "custom-branch" for _, _, ref, _ in recorded if ref is not None)


def test_repository_analyzer_handles_sparse_digest_predictions(monkeypatch):
    class Empty:
        pass

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo_digest", lambda **_: Empty())
    monkeypatch.setattr(ra, "generate_examples", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(analyzer, "build_dynamic_buckets", lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])])

    digest = RepoDigest(
        topic="Demo",
        architecture_summary="Service-oriented Flask app with auth and API routes.",
        primary_language="python",
        subsystems=[{"name": "src/api", "paths": ["src/api/app.py"]}],
        key_dependencies=["flask", "sqlalchemy"],
        entry_points=["src/api/app.py"],
        test_coverage_hint="has_tests",
        digest_id="digest-1234",
    )
    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="src/api/app.py\nREADME.md",
        readme_content="# Demo\n\nA sample project.",
        package_files="flask==3.0.0",
        default_branch="main",
        repo_digest=digest,
    )
    assert hasattr(result, "llms_txt_content")
    assert "Service-oriented Flask app" in result.llms_txt_content
    assert "src/api" in result.llms_txt_content or "flask" in result.llms_txt_content


def test_repository_analyzer_handles_sparse_non_digest_predictions(monkeypatch):
    class Empty:
        pass

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: Empty())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: Empty())
    monkeypatch.setattr(ra, "generate_examples", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(analyzer, "build_dynamic_buckets", lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])])

    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="README.md\nsrc/main.py",
        readme_content="# Demo\n\nPrimary service for processing events.",
        package_files="",
        default_branch="main",
    )
    assert hasattr(result, "llms_txt_content")
    assert "Primary service for processing events" in result.llms_txt_content
