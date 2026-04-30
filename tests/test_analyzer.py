from __future__ import annotations

from lms_llmsTxt import analyzer
from lms_llmsTxt.repo_digest import RepoDigest



def _stub_section_synthesis(monkeypatch, ra, notes=None):
    monkeypatch.setattr(
        ra,
        "synthesize_section_notes",
        lambda **_: analyzer.dspy.Prediction(section_notes=notes or []),
    )

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
    _stub_section_synthesis(monkeypatch, ra)
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
    _stub_section_synthesis(monkeypatch, ra)
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
    _stub_section_synthesis(monkeypatch, ra)
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
    _stub_section_synthesis(monkeypatch, ra)
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

    assert [section.name for section in result.document.sections[:3]] == ["Docs", "Usage"]
    assert result.document.remember_bullets == ["Read Docs first", "Then run the CLI"]
    assert result.trace.section_plan[0]["source"] == "model"
    assert result.trace.section_plan[0]["name"] == "Docs"
    assert result.trace.deterministic_section_planning["available_sections"] == ["Usage", "Docs", "Tutorials"]
    assert result.trace.model_section_planning["included_sections"] == ["Docs", "Usage"]
    assert result.trace.model_section_planning["used_model_filter"] is True
    assert result.trace.model_section_planning["used_model_order"] is True
    assert result.trace.model_section_planning["remember_source"] == "model"
    assert result.trace.model_section_planning["final_sections"] == ["Docs", "Usage"]
    assert result.document.sections[1].entries[0].url == "about:usage-examples"
    assert "Read Docs first" in result.llms_txt_content
    assert "Run `lmstxt <repo-url>`" in result.llms_txt_content


def test_repository_analyzer_synthesizes_section_content_while_rendering_deterministically(monkeypatch):
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
        ),
    )
    _stub_section_synthesis(
        monkeypatch,
        ra,
        notes=["Docs: Start with the README before exploring source files."],
    )
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

    assert result.document.sections[0].name == "Docs"
    assert result.document.sections[0].entries[0].title == "Docs Overview"
    assert result.document.sections[0].entries[0].url == "about:section-synthesis"
    assert "Start with the README before exploring source files" in result.llms_txt_content
    assert result.trace.model_section_planning["section_content_synthesis"]["used"] is True
    assert result.trace.section_plan[0]["source"] == "model"


def test_repository_analyzer_ignores_invalid_model_section_filter(monkeypatch):
    class RepoAnalysis:
        project_purpose = "CLI toolkit for repository summaries."
        key_concepts = ["CLI", "Artifacts"]

    class StructureAnalysis:
        important_directories = ["src", "docs"]
        entry_points = ["src/lms_llmsTxt/cli.py"]
        development_info = "pytest and uv"

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    _stub_section_synthesis(monkeypatch, ra)
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
    assert result.trace.model_section_planning["included_sections"] == ["Nonexistent"]
    assert result.trace.model_section_planning["used_model_filter"] is False
    assert result.trace.model_section_planning["used_model_order"] is True
    assert result.trace.model_section_planning["filtered_sections"] == ["Usage", "Docs", "Tutorials"]
    assert result.trace.model_section_planning["final_sections"] == ["Tutorials", "Docs", "Usage"]
    assert result.trace.deterministic_section_planning["usage_section_added"] is True




def test_repository_analyzer_falls_back_when_digest_analysis_parse_fails(monkeypatch):
    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(analyzer, "AdapterParseError", RuntimeError)
    monkeypatch.setattr(
        ra,
        "analyze_repo_digest",
        lambda **_: (_ for _ in ()).throw(RuntimeError("parse failed")),
    )
    monkeypatch.setattr(ra, "generate_examples", lambda **_: analyzer.dspy.Prediction())
    monkeypatch.setattr(ra, "plan_sections", lambda **_: analyzer.dspy.Prediction())
    _stub_section_synthesis(monkeypatch, ra)
    monkeypatch.setattr(
        analyzer,
        "build_dynamic_buckets",
        lambda *args, **kwargs: [("Docs", [("README", "https://example.com/readme", "docs page")])],
    )

    digest = RepoDigest(
        topic="PinchTab",
        architecture_summary="React dashboard with filtering and activity tracking.",
        primary_language="typescript",
        subsystems=[{"name": "Dashboard", "paths": ["src/Dashboard.tsx"]}],
        key_dependencies=["react", "axios"],
        entry_points=["src/main.tsx"],
        test_coverage_hint="unknown",
        digest_id="digest-parse-fallback",
    )

    result = ra.forward(
        repo_url="https://github.com/pinchtab/pinchtab",
        file_tree="src/Dashboard.tsx\nREADME.md",
        readme_content="# PinchTab\n\nDashboard app.",
        package_files="package.json",
        default_branch="main",
        repo_digest=digest,
    )

    assert "React dashboard with filtering and activity tracking" in result.llms_txt_content
    assert result.analysis.project_purpose == "React dashboard with filtering and activity tracking."
    assert result.analysis.key_concepts == ["Dashboard"]
    assert result.document.sections[0].name == "Docs"


def test_repository_analyzer_keeps_deterministic_document_when_optional_model_steps_parse_fail(monkeypatch):
    class RepoAnalysis:
        project_purpose = "CLI toolkit for repository summaries."
        key_concepts = ["CLI", "Artifacts"]

    class StructureAnalysis:
        important_directories = ["src"]
        entry_points = ["src/lms_llmsTxt/cli.py"]
        development_info = "pytest and uv"

    ra = analyzer.RepositoryAnalyzer(production_mode=True)
    monkeypatch.setattr(analyzer, "AdapterParseError", RuntimeError)
    monkeypatch.setattr(ra, "analyze_repo", lambda **_: RepoAnalysis())
    monkeypatch.setattr(ra, "analyze_structure", lambda **_: StructureAnalysis())
    monkeypatch.setattr(
        ra,
        "generate_examples",
        lambda **_: (_ for _ in ()).throw(RuntimeError("usage parse failed")),
    )
    monkeypatch.setattr(
        ra,
        "plan_sections",
        lambda **_: (_ for _ in ()).throw(RuntimeError("plan parse failed")),
    )
    monkeypatch.setattr(
        ra,
        "synthesize_section_notes",
        lambda **_: (_ for _ in ()).throw(RuntimeError("notes parse failed")),
    )
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

    assert result.document.project_name == "Demo"
    assert [section.name for section in result.document.sections] == ["Docs"]
    assert "README" in result.llms_txt_content
    assert result.trace.section_plan[0]["source"] == "deterministic"
    assert result.trace.model_section_planning["section_content_synthesis"]["used"] is False
    assert result.trace.model_section_planning["section_content_synthesis"]["fallback_reason"] == "adapter-parse-error"
