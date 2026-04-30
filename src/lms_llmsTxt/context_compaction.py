from __future__ import annotations

from dataclasses import replace

from .context_budget import ContextBudget
from .models import RepositoryMaterial


def _trim_file_tree(file_tree: str, max_lines: int) -> str:
    lines = file_tree.splitlines()
    if len(lines) <= max_lines:
        return file_tree
    return "\n".join(lines[:max_lines]) + "\n... (trimmed file tree)"


def _trim_text(content: str, max_chars: int, label: str) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + f"\n... (trimmed {label})"


def compact_material(material: RepositoryMaterial, budget: ContextBudget, config) -> RepositoryMaterial:
    # Deterministic compaction ladder.
    compacted = replace(material)
    compacted.file_tree = _trim_file_tree(
        compacted.file_tree,
        max(50, int(getattr(config, "max_file_tree_lines", 1200) * 0.6)),
    )
    compacted.readme_content = _trim_text(
        compacted.readme_content,
        max(1000, int(getattr(config, "max_readme_chars", 24000) * 0.5)),
        "README",
    )
    compacted.package_files = _trim_text(
        compacted.package_files,
        max(1200, int(getattr(config, "max_package_chars", 18000) * 0.5)),
        "package files",
    )

    # Final deterministic blob truncation based on budget estimate proportions.
    if budget.estimated_prompt_tokens > budget.available_tokens and budget.available_tokens > 0:
        factor = max(0.2, min(1.0, budget.available_tokens / max(1, budget.estimated_prompt_tokens)))
        compacted.readme_content = _trim_text(
            compacted.readme_content,
            max(500, int(len(compacted.readme_content) * factor)),
            "README",
        )
        compacted.package_files = _trim_text(
            compacted.package_files,
            max(500, int(len(compacted.package_files) * factor)),
            "package files",
        )
    return compacted
