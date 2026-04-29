from __future__ import annotations

import json
from pathlib import Path
import re

from .graph_models import (
    ForceGraphData,
    ForceGraphLink,
    ForceGraphNode,
    GraphNodeEvidence,
    RepoGraphNode,
    RepoSkillGraph,
)
from .repo_digest import RepoDigest


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "node"


def build_repo_graph(digest: RepoDigest) -> RepoSkillGraph:
    nodes: list[RepoGraphNode] = []

    moc_links: list[str] = []
    for subsystem in digest.subsystems[:20]:
        node_id = _slug(subsystem["name"])
        moc_links.append(node_id)
        content = (
            f"---\n"
            f"title: {subsystem['name']}\n"
            f"type: concept\n"
            f"description: {subsystem['summary']}\n"
            f"---\n\n"
            f"{subsystem['summary']}\n\n"
            f"Key symbols: {', '.join(subsystem.get('key_symbols', [])[:12]) or 'n/a'}\n"
        )
        evidence = [
            GraphNodeEvidence(path=path, start_line=1, end_line=1, artifact_ref="repo_digest")
            for path in subsystem.get("paths", [])[:8]
        ]
        nodes.append(
            RepoGraphNode(
                id=node_id,
                label=subsystem["name"],
                type="concept",
                description=subsystem["summary"],
                content=content,
                links=[],
                evidence=evidence,
                artifacts=["repo.graph.json", "repo.force.json"],
                tags=["subsystem", digest.primary_language],
            )
        )

    moc_content = (
        f"# {digest.topic}\n\n"
        f"This map summarizes repository structure and important exploration paths. "
        f"Start with subsystem nodes and follow evidence-backed links to inspect source files.\n\n"
        f"## Domain Clusters\n"
        + "\n".join(
            f"- Explore [[{node_id}]] to inspect related module behavior and evidence anchors."
            for node_id in moc_links[:16]
        )
        + "\n\n## Explorations Needed\n"
        "- Which subsystems should be prioritized for onboarding documentation?\n"
        "- Which dependencies are high-risk and need version guardrails?\n"
        "- Where should integration tests be expanded based on current topology?\n"
    )

    moc = RepoGraphNode(
        id="moc",
        label=f"{digest.topic} Map",
        type="moc",
        description=digest.architecture_summary or "Repository map of content",
        content=moc_content,
        links=moc_links[:16],
        evidence=[GraphNodeEvidence(path="repo_digest", artifact_ref=digest.digest_id)],
        artifacts=["repo.graph.json"],
        tags=["moc", digest.primary_language],
    )

    nodes.insert(0, moc)
    return RepoSkillGraph(topic=digest.topic, nodes=nodes)


def to_force_graph(graph: RepoSkillGraph) -> ForceGraphData:
    nodes = [
        ForceGraphNode(
            id=node.id,
            label=node.label,
            type=node.type,
            val=3.0 if node.type == "moc" else 1.5,
        )
        for node in graph.nodes
    ]
    links: list[ForceGraphLink] = []
    for node in graph.nodes:
        for target in node.links:
            links.append(ForceGraphLink(source=node.id, target=target))
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
