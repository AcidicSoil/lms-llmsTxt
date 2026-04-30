from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RepositoryMaterial:
    """Aggregate of repository inputs we feed into DSPy."""

    repo_url: str
    file_tree: str
    readme_content: str
    package_files: str
    default_branch: str
    is_private: bool


@dataclass(slots=True)
class LLMsLinkEntry:
    """Single curated link entry in the rendered llms.txt document."""

    title: str
    url: str
    note: str


@dataclass(slots=True)
class LLMsSection:
    """A deterministic llms.txt section with curated link entries."""

    name: str
    entries: list[LLMsLinkEntry] = field(default_factory=list)


@dataclass(slots=True)
class LLMsDocument:
    """Structured intermediate representation consumed by the markdown renderer."""

    project_name: str
    project_purpose: str
    remember_bullets: list[str] = field(default_factory=list)
    sections: list[LLMsSection] = field(default_factory=list)


@dataclass(slots=True)
class AnalyzerTrace:
    """Inspectable metadata for staged analyzer execution."""

    selected_evidence: list[dict[str, Any]] = field(default_factory=list)
    dropped_evidence: list[dict[str, Any]] = field(default_factory=list)
    section_plan: list[dict[str, Any]] = field(default_factory=list)
    model_section_planning: dict[str, Any] = field(default_factory=dict)
    deterministic_section_planning: dict[str, Any] = field(default_factory=dict)
    compaction_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GenerationArtifacts:
    """Outputs written to disk once generation completes."""

    llms_txt_path: str
    llms_full_path: str | None = None
    ctx_path: str | None = None
    json_path: str | None = None
    graph_json_path: str | None = None
    force_graph_path: str | None = None
    graph_nodes_dir: str | None = None
    trace_path: str | None = None
    used_fallback: bool = False
    fallback_reason: str | None = None
