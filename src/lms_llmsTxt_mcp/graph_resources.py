from __future__ import annotations

from pathlib import Path

from .config import settings


def graph_resource_uri(relative_path: str) -> str:
    return f"lmstxt://graphs/{relative_path}"


def scan_graph_artifacts() -> list[Path]:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    results: list[Path] = []
    for pattern in ("**/repo.graph.json", "**/repo.force.json", "**/nodes/*.md"):
        for path in root.glob(pattern):
            if path.is_file():
                results.append(path.relative_to(root))
    return sorted(results)


def read_graph_artifact_chunk(relative_path: str, offset: int, limit: int) -> str:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    path = root / relative_path
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Graph artifact not found: {relative_path}")
    if offset < 0:
        offset = 0
    if limit <= 0:
        return ""
    with path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        return handle.read(limit)
