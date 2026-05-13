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
        class Predict:
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


class SynthesizeLLMsSectionNotes(dspy.Signature):
    """Synthesize concise section-level guidance while preserving deterministic rendering."""

    project_name: str = dspy.InputField()
    project_purpose: str = dspy.InputField()
    section_plan: List[str] = dspy.InputField(
        desc="Final section names selected for the llms.txt document"
    )
    candidate_entries: List[str] = dspy.InputField(
        desc="Candidate entries as 'Section | Title | URL | Note' strings"
    )

    section_notes: List[str] = dspy.OutputField(
        desc="Notes as 'Section: concise guidance' for sections that need synthesized context"
    )


class PlanLLMsSections(dspy.Signature):
    """Choose the final semantic section order and remember bullets for llms.txt."""

    project_name: str = dspy.InputField()
    project_purpose: str = dspy.InputField()
    key_concepts: List[str] = dspy.InputField()
    important_directories: List[str] = dspy.InputField()
    entry_points: List[str] = dspy.InputField()
    development_info: str = dspy.InputField()
    available_sections: List[str] = dspy.InputField(
        desc="Available deterministic section names in the current candidate document"
    )

    included_sections: List[str] = dspy.OutputField(
        desc="Subset of available section names to keep in the final document"
    )
    preferred_section_order: List[str] = dspy.OutputField(
        desc="Preferred final section ordering using only available section names"
    )
    remember_bullets: List[str] = dspy.OutputField(
        desc="Short remember bullets for the document header"
    )


class AnalyzeRepositoryFromDigest(dspy.Signature):
    """Generate project summary from a reduced repository digest."""

    digest_summary: str = dspy.InputField(desc="Compact digest of repository structure")
    repo_url: str = dspy.InputField(desc="GitHub repository URL")

    project_purpose: str = dspy.OutputField(desc="Purpose summary in 1-3 sentences")
    key_concepts: List[str] = dspy.OutputField(desc="Key concepts as list")
    architecture_overview: str = dspy.OutputField(desc="Architecture overview paragraph")


class SynthesizeRepoGraphNodes(dspy.Signature):
    """Synthesize one repository graph node into specific, evidence-grounded developer guidance.

    Return JSON only: an array with exactly one object containing id, label,
    description, and content. The input contains a single node spec. Infer that
    node independently from its own paths, excerpts, symbols, and relationship
    context. Explain why linked nodes matter to this node; do not merely list
    neighbor IDs.

    The content value must be markdown with 2-4 concise, node-specific sections.
    Section headings must be unique to this node's domain and must not repeat the
    generic template headings "Related concepts", "Change risk", "Evidence",
    "Inspect first", or "Implementation signals". Use concrete mechanisms, APIs,
    files, components, commands, package boundaries, or workflows from the source
    excerpts. Do not use generic phrases such as "explains the role", "nearby
    files depend", "repository responsibility", or path-inventory prose.
    """

    repo_topic: str = dspy.InputField(desc="Repository or project name")
    repo_summary: str = dspy.InputField(desc="High-level repository summary")
    node_specs_json: str = dspy.InputField(
        desc="JSON array containing exactly one graph node with label, paths, symbols, relationship context, and source excerpts"
    )

    node_updates_json: str = dspy.OutputField(
        desc="JSON array with exactly one object: [{id,label,description,content}] using unique node-specific markdown headings"
    )
