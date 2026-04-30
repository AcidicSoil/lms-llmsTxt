from __future__ import annotations

import json
from pathlib import Path
import re
from collections import Counter, defaultdict
from itertools import combinations

from .graph_models import (
    ForceGraphData,
    ForceGraphLink,
    ForceGraphNode,
    GraphNodeEvidence,
    GraphNodeType,
    RepoGraphNode,
    RepoSkillGraph,
)
from .repo_digest import RepoDigest


MAX_REPO_NODES = 20
MAX_MOC_LINKS = 16
MAX_NODE_LINKS = 5


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "node"


def _unique_slug(value: str, used: set[str]) -> str:
    base = _slug(value)
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _node_type_for_subsystem(subsystem: dict) -> GraphNodeType:
    name = str(subsystem.get("name", "")).lower()
    paths = [str(path).lower() for path in subsystem.get("paths", [])]
    searchable = " ".join([name, *paths])

    if any(token in searchable for token in ("test", "spec", "e2e", "fixture", "mock")):
        return "gotcha"
    if any(token in searchable for token in ("doc", "guide", "example", "workflow", "template")):
        return "pattern"
    if any(token in searchable for token in ("config", "security", "secret", "credential")):
        return "gotcha"
    return "concept"


def _path_tokens(paths: list[str]) -> set[str]:
    tokens: set[str] = set()
    for path in paths:
        parts = [part for part in path.lower().split("/") if part]
        tokens.update(parts[:3])
        stem = parts[-1].rsplit(".", 1)[0] if parts else ""
        if stem:
            tokens.add(stem)
    return tokens


def _subsystem_relation_score(source: dict, target: dict) -> int:
    source_name = str(source.get("name", "")).lower()
    target_name = str(target.get("name", "")).lower()
    source_paths = [str(path) for path in source.get("paths", [])]
    target_paths = [str(path) for path in target.get("paths", [])]
    source_symbols = {str(symbol).lower() for symbol in source.get("key_symbols", [])}
    target_symbols = {str(symbol).lower() for symbol in target.get("key_symbols", [])}

    score = 0
    source_root = source_name.split("/", 1)[0]
    target_root = target_name.split("/", 1)[0]
    if source_root and source_root == target_root:
        score += 8

    shared_tokens = _path_tokens(source_paths) & _path_tokens(target_paths)
    score += min(len(shared_tokens) * 3, 12)

    shared_symbols = source_symbols & target_symbols
    score += min(len(shared_symbols) * 2, 8)

    if "test" in source_name and target_root and target_root in source_name:
        score += 10
    if "test" in target_name and source_root and source_root in target_name:
        score += 10

    if any(token in source_name for token in ("doc", "guide")) and target_root in source_name:
        score += 6
    if any(token in target_name for token in ("doc", "guide")) and source_root in target_name:
        score += 6

    if source_root in {"internal", "src", "app"} and target_root in {"cmd", "cli", "bin"}:
        score += 5
    if target_root in {"internal", "src", "app"} and source_root in {"cmd", "cli", "bin"}:
        score += 5

    return score


def _format_evidence_lines(paths: list[str]) -> str:
    if not paths:
        return "- No concrete file path was available in the digest."
    return "\n".join(f"- `{path}`" for path in paths[:8])


def _content_for_subsystem(
    subsystem: dict,
    *,
    node_type: GraphNodeType,
    related_links: list[str],
) -> str:
    name = str(subsystem["name"])
    summary = str(subsystem["summary"])
    key_symbols = [str(symbol) for symbol in subsystem.get("key_symbols", [])[:12]]
    paths = [str(path) for path in subsystem.get("paths", [])[:8]]

    related_sentence = (
        " ".join(
            f"Follow [[{node_id}]] to compare adjacent responsibilities and integration evidence."
            for node_id in related_links
        )
        if related_links
        else "No high-confidence adjacent subsystem was detected in the digest."
    )

    operational_heading = {
        "concept": "Why this subsystem matters",
        "pattern": "Reusable implementation pattern",
        "gotcha": "Operational risk or validation surface",
        "moc": "Overview",
    }[node_type]

    return (
        f"---\n"
        f"title: {name}\n"
        f"type: {node_type}\n"
        f"description: {summary}\n"
        f"---\n\n"
        f"# {name}\n\n"
        f"{summary}\n\n"
        f"## {operational_heading}\n\n"
        f"This node is grounded in repository paths that indicate a `{node_type}` role in the codebase. "
        f"Use it to understand ownership boundaries before changing related files.\n\n"
        f"## Evidence\n\n"
        f"{_format_evidence_lines(paths)}\n\n"
        f"## Key symbols\n\n"
        f"{', '.join(key_symbols) if key_symbols else 'No key symbols were extracted from the digest.'}\n\n"
        f"## Related traversal\n\n"
        f"{related_sentence}\n"
    )


def _related_edges(subsystems: list[dict], node_ids: list[str]) -> dict[str, list[str]]:
    scored: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for left_index, right_index in combinations(range(len(subsystems)), 2):
        left = subsystems[left_index]
        right = subsystems[right_index]
        score = _subsystem_relation_score(left, right)
        if score <= 0:
            continue
        left_id = node_ids[left_index]
        right_id = node_ids[right_index]
        scored[left_id].append((score, right_id))
        scored[right_id].append((score, left_id))

    related: dict[str, list[str]] = {}
    for node_id, candidates in scored.items():
        candidates.sort(key=lambda item: (-item[0], item[1]))
        related[node_id] = [candidate for _, candidate in candidates[:MAX_NODE_LINKS]]
    return related


def _build_moc_content(digest: RepoDigest, nodes: list[RepoGraphNode]) -> str:
    type_counts = Counter(node.type for node in nodes if node.type != "moc")
    cluster_lines = []
    for node in nodes[:MAX_MOC_LINKS]:
        cluster_lines.append(
            f"- Start with [[{node.id}]] when investigating {node.label}; its evidence anchors explain why it belongs in the repository map."
        )

    type_summary = ", ".join(f"{count} {node_type}" for node_type, count in sorted(type_counts.items()))
    return (
        f"# {digest.topic}\n\n"
        f"This map summarizes repository structure, evidence-backed subsystem relationships, and practical traversal paths. "
        f"It contains {type_summary or 'no classified subsystem nodes'} so agents can distinguish architecture, reusable patterns, and validation risks instead of reading a flat file list.\n\n"
        f"## Domain Clusters\n"
        + "\n".join(cluster_lines)
        + "\n\n## Explorations Needed\n"
        "- Which subsystem boundaries should become explicit ownership documentation?\n"
        "- Which pattern and gotcha nodes should become targeted regression tests?\n"
        "- Where should dependency and entry-point evidence be expanded in the next graph pass?\n"
    )


def build_repo_graph(digest: RepoDigest) -> RepoSkillGraph:
    selected_subsystems = digest.subsystems[:MAX_REPO_NODES]
    used_ids: set[str] = {"moc"}
    subsystem_node_ids = [_unique_slug(str(subsystem["name"]), used_ids) for subsystem in selected_subsystems]
    related = _related_edges(selected_subsystems, subsystem_node_ids)

    nodes: list[RepoGraphNode] = []
    for subsystem, node_id in zip(selected_subsystems, subsystem_node_ids):
        node_type = _node_type_for_subsystem(subsystem)
        links = related.get(node_id, [])
        content = _content_for_subsystem(subsystem, node_type=node_type, related_links=links)
        evidence = [
            GraphNodeEvidence(path=path, start_line=1, end_line=1, artifact_ref="repo_digest")
            for path in subsystem.get("paths", [])[:8]
        ]
        nodes.append(
            RepoGraphNode(
                id=node_id,
                label=subsystem["name"],
                type=node_type,
                description=subsystem["summary"],
                content=content,
                links=links,
                evidence=evidence,
                artifacts=["repo.graph.json", "repo.force.json"],
                tags=["subsystem", digest.primary_language, node_type],
            )
        )

    moc_links = [node.id for node in nodes[:MAX_MOC_LINKS]]
    moc = RepoGraphNode(
        id="moc",
        label=f"{digest.topic} Map",
        type="moc",
        description=digest.architecture_summary or "Repository map of content",
        content=_build_moc_content(digest, nodes),
        links=moc_links,
        evidence=[GraphNodeEvidence(path="repo_digest", artifact_ref=digest.digest_id)],
        artifacts=["repo.graph.json"],
        tags=["moc", digest.primary_language],
    )

    return RepoSkillGraph(topic=digest.topic, nodes=[moc, *nodes])


def to_force_graph(graph: RepoSkillGraph) -> ForceGraphData:
    degree: Counter[str] = Counter()
    links: list[ForceGraphLink] = []
    node_ids = {node.id for node in graph.nodes}
    seen_links: set[tuple[str, str]] = set()

    for node in graph.nodes:
        for target in node.links:
            if target not in node_ids or target == node.id:
                continue
            key = tuple(sorted((node.id, target)))
            if key in seen_links:
                continue
            seen_links.add(key)
            degree[node.id] += 1
            degree[target] += 1
            links.append(ForceGraphLink(source=node.id, target=target))

    nodes = [
        ForceGraphNode(
            id=node.id,
            label=node.label,
            type=node.type,
            val=(3.0 if node.type == "moc" else 1.5) + min(degree[node.id] * 0.2, 1.2),
        )
        for node in graph.nodes
    ]
    return ForceGraphData(nodes=nodes, links=links)


def emit_graph_files(graph: RepoSkillGraph, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    force = to_force_graph(graph)

    graph_json = output_dir / "repo.graph.json"
    force_json = output_dir / "repo.force.json"
    nodes_dir = output_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    graph_json.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    force_json.write_text(force.model_dump_json(indent=2), encoding="utf-8")

    for node in graph.nodes:
        (nodes_dir / f"{node.id}.md").write_text(node.content.rstrip() + "\n", encoding="utf-8")

    return {
        "graph_json": str(graph_json),
        "force_json": str(force_json),
        "nodes_dir": str(nodes_dir),
    }


def load_graph_from_file(path: Path) -> RepoSkillGraph:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RepoSkillGraph.model_validate(payload)
