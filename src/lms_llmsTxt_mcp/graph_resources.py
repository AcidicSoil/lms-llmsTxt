from __future__ import annotations

import re
from pathlib import Path

from .config import settings

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def graph_resource_uri(relative_path: str) -> str:
    return f"lmstxt://graphs/{relative_path}"


def repo_graph_node_uri(repo_id: str, node_id: str) -> str:
    return f"repo://{repo_id}/graph/nodes/{node_id}"


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


def _iter_repo_graph_roots() -> list[tuple[str, str, Path]]:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    results: list[tuple[str, str, Path]] = []
    for graph_file in root.glob("**/graph/repo.graph.json"):
        rel = graph_file.relative_to(root)
        parts = rel.parts
        if len(parts) < 4 or parts[-2] != "graph" or parts[-1] != "repo.graph.json":
            continue
        owner = parts[-4]
        repo = parts[-3]
        repo_root = root / owner / repo / "graph"
        results.append((owner, repo, repo_root))
    return results


def _repo_id_aliases(owner: str, repo: str) -> set[str]:
    return {
        f"{owner}--{repo}",
        f"{owner}/{repo}",
        f"{owner}__{repo}",
    }


def resolve_repo_node_path(repo_id: str, node_id: str) -> Path:
    if not _SAFE_SEGMENT.fullmatch(node_id):
        raise ValueError(f"Invalid node id: {node_id}")
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    for owner, repo, repo_root in _iter_repo_graph_roots():
        if repo_id not in _repo_id_aliases(owner, repo):
            continue
        node_path = repo_root / "nodes" / f"{node_id}.md"
        if node_path.is_file():
            return node_path.relative_to(root)
    raise FileNotFoundError(f"Graph node not found: repo_id={repo_id}, node_id={node_id}")


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


def read_repo_node_chunk(repo_id: str, node_id: str, offset: int, limit: int) -> str:
    path = resolve_repo_node_path(repo_id=repo_id, node_id=node_id)
    return read_graph_artifact_chunk(str(path), offset, limit)
