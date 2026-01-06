from __future__ import annotations

from typing import List

try:
    import dspy
except ImportError:
    class MockDSPy:
        class Signature:
            pass
        class Module:
            pass
        class ChainOfThought:
            def __init__(self, signature): pass
            def __call__(self, **kwargs): return MockDSPy.Prediction()
        class Prediction:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        class LM:
            def __init__(self, *args, **kwargs): pass

        class InputField:
            def __init__(self, *args, **kwargs): pass
        
        class OutputField:
            def __init__(self, *args, **kwargs): pass
            
        @staticmethod
        def configure(**kwargs):
            pass

    dspy = MockDSPy()


class AnalyzeRepository(dspy.Signature):
    """Summarize a repository's purpose and concepts."""

    repo_url: str = dspy.InputField(desc="GitHub repository URL")
    file_tree: str = dspy.InputField(desc="Repository file structure (one path per line)")
    readme_content: str = dspy.InputField(desc="README.md content (raw)")

    project_purpose: str = dspy.OutputField(
        desc="Main purpose and goals of the project (2–4 sentences)"
    )
    key_concepts: List[str] = dspy.OutputField(
        desc="Important concepts and terminology (bullet list items)"
    )
    architecture_overview: str = dspy.OutputField(
        desc="High-level architecture overview (1–2 paragraphs)"
    )


class AnalyzeCodeStructure(dspy.Signature):
    """Identify important directories, entry points, and development insights."""

    file_tree: str = dspy.InputField()
    package_files: str = dspy.InputField(
        desc="Concatenated contents of pyproject/requirements/package.json files."
    )

    important_directories: List[str] = dspy.OutputField(
        desc="Key directories with brief notes (e.g., src/, docs/, examples/)"
    )
    entry_points: List[str] = dspy.OutputField(
        desc="Likely entry points or commands (e.g., cli.py, main.ts, npm scripts)"
    )
    development_info: str = dspy.OutputField(
        desc="Development or build info (dependencies, scripts, tooling)"
    )


class GenerateUsageExamples(dspy.Signature):
    """Produce a short section of common usage examples based on the repo analysis."""

    repo_info: str = dspy.InputField(
        desc="Summary of the project's purpose and key concepts"
    )
    usage_examples: str = dspy.OutputField(
        desc="Markdown examples (code fences) showing typical usage"
    )


class GenerateLLMsTxt(dspy.Signature):
    """Generate a complete llms.txt (markdown index) for the project."""

    project_purpose: str = dspy.InputField()
    key_concepts: List[str] = dspy.InputField()
    architecture_overview: str = dspy.InputField()
    important_directories: List[str] = dspy.InputField()
    entry_points: List[str] = dspy.InputField()
    development_info: str = dspy.InputField()
    usage_examples: str = dspy.InputField(
        desc="Common usage patterns and examples (markdown)"
    )

    llms_txt_content: str = dspy.OutputField(
        desc="Complete llms.txt content following the standard format"
    )
