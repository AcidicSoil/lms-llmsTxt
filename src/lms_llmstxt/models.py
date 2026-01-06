from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepositoryMaterial:
    """Aggregate of repository inputs we feed into DSPy."""

    repo_url: str
    file_tree: str
    readme_content: str
    package_files: str
    default_branch: str
    is_private: bool


@dataclass
class GenerationArtifacts:
    """Outputs written to disk once generation completes."""

    llms_txt_path: str
    llms_full_path: str | None = None
    ctx_path: str | None = None
    json_path: str | None = None
    used_fallback: bool = False
