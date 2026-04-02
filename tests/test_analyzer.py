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
    monkeypatch.setattr(ra, "plan_sections", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])],
    )

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
    assert result.document.project_name == "Demo"
    assert result.trace.selected_evidence[0]["section"] == "Docs"
    assert result.trace.section_plan[0]["name"] == "Docs"


def test_repository_analyzer_handles_sparse_non_digest_predictions(monkeypatch):
    class Empty:
        pass

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: Empty())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: Empty())
    monkeypatch.setattr(ra, "generate_examples", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(ra, "plan_sections", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])],
    )

    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="README.md\nsrc/main.py",
        readme_content="# Demo\n\nPrimary service for processing events.",
        package_files="",
        default_branch="main",
    )
    assert hasattr(result, "llms_txt_content")
    assert "Primary service for processing events" in result.llms_txt_content
    assert result.document.sections[0].name == "Docs"
    assert result.trace.compaction_reasons


def test_repository_analyzer_promotes_usage_examples_into_structured_document(monkeypatch):
    class RepoAnalysis:
        project_purpose = "CLI toolkit for repository summaries."
        key_concepts = ["CLI", "Artifacts"]

    class StructureAnalysis:
        important_directories = ["src"]
        entry_points = ["src/lms_llmsTxt/cli.py"]
        development_info = "pytest and uv"

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: RepoAnalysis())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: StructureAnalysis())
    monkeypatch.setattr(
        ra,
        "generate_examples",
        lambda **_: analyzer.dspy.Prediction(usage_examples="Run `lmstxt <repo-url>` to generate artifacts."),
    )
    monkeypatch.setattr(ra, "plan_sections", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])],
    )

    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="README.md\nsrc/lms_llmsTxt/cli.py",
        readme_content="# Demo\n\nCLI toolkit for repository summaries.",
        package_files="",
        default_branch="main",
    )

    assert result.document.sections[0].name == "Usage"
    assert result.document.sections[0].entries[0].url == "about:usage-examples"
    assert "Run `lmstxt <repo-url>`" in result.llms_txt_content
    assert result.trace.section_plan[0]["name"] == "Usage"
    assert result.trace.section_plan[0]["source"] == "deterministic"


def test_repository_analyzer_uses_model_section_plan_when_available(monkeypatch):
    class RepoAnalysis:
        project_purpose = "CLI toolkit for repository summaries."
        key_concepts = ["CLI", "Artifacts"]

    class StructureAnalysis:
        important_directories = ["src", "docs"]
        entry_points = ["src/lms_llmsTxt/cli.py"]
        development_info = "pytest and uv"

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: RepoAnalysis())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: StructureAnalysis())
    monkeypatch.setattr(
        ra,
        "generate_examples",
        lambda **_: analyzer.dspy.Prediction(usage_examples="Run `lmstxt <repo-url>` to generate artifacts."),
    )
    monkeypatch.setattr(
        ra,
        "plan_sections",
        lambda **_: analyzer.dspy.Prediction(
            included_sections=["Docs", "Usage"],
            preferred_section_order=["Docs", "Usage"],
            remember_bullets=["Read Docs first", "Then run the CLI"],
        ),
    )
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [
            ("Docs", [("README", "https://example.com/readme", "docs page")]),
            ("Tutorials", [("Walkthrough", "https://example.com/tutorial", "worked example")]),
        ],
    )

    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="README.md\ndocs/walkthrough.md\nsrc/lms_llmsTxt/cli.py",
        readme_content="# Demo\n\nCLI toolkit for repository summaries.",
        package_files="",
        default_branch="main",
    )


def test_repository_analyzer_ignores_invalid_model_section_filter(monkeypatch):
    class RepoAnalysis:
        project_purpose = "CLI toolkit for repository summaries."
        key_concepts = ["CLI", "Artifacts"]

    class StructureAnalysis:
        important_directories = ["src", "docs"]
        entry_points = ["src/lms_llmsTxt/cli.py"]
        development_info = "pytest and uv"

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: RepoAnalysis())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: StructureAnalysis())
    monkeypatch.setattr(
        ra,
        "generate_examples",
        lambda **_: analyzer.dspy.Prediction(usage_examples="Run `lmstxt <repo-url>` to generate artifacts."),
    )
    monkeypatch.setattr(
        ra,
        "plan_sections",
        lambda **_: analyzer.dspy.Prediction(
            included_sections=["Nonexistent"],
            preferred_section_order=["Tutorials", "Docs"],
        ),
    )
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [
            ("Docs", [("README", "https://example.com/readme", "docs page")]),
            ("Tutorials", [("Walkthrough", "https://example.com/tutorial", "worked example")]),
        ],
    )

    result = ra.forward(
        repo_url="https://github.com/acme/demo",
        file_tree="README.md\ndocs/walkthrough.md\nsrc/lms_llmsTxt/cli.py",
        readme_content="# Demo\n\nCLI toolkit for repository summaries.",
        package_files="",
        default_branch="main",
    )

    assert [section.name for section in result.document.sections[:3]] == ["Tutorials", "Docs", "Usage"]
    assert result.trace.section_plan[0]["source"] == "model"

