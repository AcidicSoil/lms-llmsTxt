from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
from typing import Any

try:
    import dspy
except ImportError:  # pragma: no cover - test fallback
    from .signatures import dspy

from .config import AppConfig
from .graph_builder import validate_semantic_graph
from .graph_models import GraphNodeEvidence, RepoGraphNode, RepoSkillGraph
from .models import RepositoryMaterial
from .repo_digest import RepoDigest
from .signatures import SynthesizeRepoGraphNodes

logger = logging.getLogger(__name__)

MAX_BATCH_NODES = 12
MAX_NODE_EXCERPT_CHARS = 1_200

LOW_VALUE_PHRASES = (
    "explains the role",
    "nearby files depend on that concept",
    "this concept describes the repository responsibility",
    "rather than reading it as a bundle of filenames",
    "random collection of paths",
    "the strongest evidence paths include",
    "care about src",
    "this area groups the behavior",
)


def enrich_repo_graph_with_dspy(
    graph: RepoSkillGraph,
    digest: RepoDigest,
    material: RepositoryMaterial,
    config: AppConfig,
) -> RepoSkillGraph:
    """Use a bounded DSPy pass to replace generic deterministic node prose.

    This is intentionally a single batched call. The graph topology remains
    deterministic; DSPy only rewrites labels, descriptions, and user-facing
    markdown for nodes where the model can produce evidence-grounded content.
    """
    non_moc_nodes = [node for node in graph.nodes if node.type != "moc"][:MAX_BATCH_NODES]
    if not non_moc_nodes:
        return graph

    specs = _node_specs(non_moc_nodes, digest, material, config)
    if not specs:
        return graph

    module = RepoGraphDSPySynthesizer()
    try:
        prediction = module(
            repo_topic=digest.topic,
            repo_summary=digest.architecture_summary,
            node_specs_json=json.dumps(specs, ensure_ascii=False, indent=2),
        )
    except TypeError:
        prediction = module.forward(
            repo_topic=digest.topic,
            repo_summary=digest.architecture_summary,
            node_specs_json=json.dumps(specs, ensure_ascii=False, indent=2),
        )
    except Exception as exc:
        logger.warning("DSPy repo graph node synthesis failed; keeping deterministic graph: %s", exc)
        return graph

    updates = _parse_updates(getattr(prediction, "node_updates_json", ""))
    if not updates:
        logger.info("DSPy repo graph node synthesis returned no usable updates")
        return graph

    updated_nodes: list[RepoGraphNode] = []
    update_by_id = {str(update.get("id", "")): update for update in updates if update.get("id")}
    applied = 0
    for node in graph.nodes:
        update = update_by_id.get(node.id)
        if node.type == "moc" or not update:
            updated_nodes.append(node)
            continue

        candidate = _apply_update(node, update)
        if _is_high_value_node(candidate):
            updated_nodes.append(candidate)
            applied += 1
        else:
            logger.debug("Rejected low-value DSPy graph update for node %s", node.id)
            updated_nodes.append(node)

    if applied == 0:
        return graph

    updated_graph = graph.model_copy(update={"nodes": updated_nodes})
    try:
        validate_semantic_graph(updated_graph)
    except Exception as exc:
        logger.warning("DSPy graph enrichment failed validation; keeping deterministic graph: %s", exc)
        return graph

    logger.info("DSPy repo graph node synthesis enriched %s nodes", applied)
    return updated_graph


class RepoGraphDSPySynthesizer(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.synthesize = dspy.Predict(SynthesizeRepoGraphNodes)

    def forward(self, repo_topic: str, repo_summary: str, node_specs_json: str) -> Any:
        return self.synthesize(
            repo_topic=repo_topic,
            repo_summary=repo_summary,
            node_specs_json=node_specs_json,
        )


def _node_specs(
    nodes: list[RepoGraphNode],
    digest: RepoDigest,
    material: RepositoryMaterial,
    config: AppConfig,
) -> list[dict[str, Any]]:
    excerpts = _evidence_excerpt_map(material)
    subsystem_by_name = {str(item.get("name", "")): item for item in digest.subsystems}
    specs: list[dict[str, Any]] = []
    for node in nodes:
        evidence_paths = [ev.path for ev in node.evidence]
        subsystem = _matching_subsystem(node, evidence_paths, subsystem_by_name)
        candidate_paths = evidence_paths or [str(path) for path in subsystem.get("paths", [])[:6]]
        node_excerpts = [
            {"path": path, "excerpt": excerpts[path][:MAX_NODE_EXCERPT_CHARS]}
            for path in candidate_paths
            if path in excerpts and excerpts[path].strip()
        ][:3]
        specs.append(
            {
                "id": node.id,
                "current_label": node.label,
                "type": node.type,
                "current_description": node.description,
                "summary": str(subsystem.get("summary", node.description)),
                "paths": candidate_paths[:6],
                "key_symbols": [str(symbol) for symbol in subsystem.get("key_symbols", [])[:8]],
                "neighbor_ids": node.links[:4],
                "source_excerpts": node_excerpts,
            }
        )
    return specs


def _matching_subsystem(
    node: RepoGraphNode,
    evidence_paths: list[str],
    subsystem_by_name: dict[str, dict],
) -> dict[str, Any]:
    for subsystem in subsystem_by_name.values():
        paths = {str(path) for path in subsystem.get("paths", [])}
        if paths & set(evidence_paths):
            return subsystem
    normalized_label = node.label.lower().replace(" ", "-")
    for name, subsystem in subsystem_by_name.items():
        if normalized_label in name.lower().replace("_", "-"):
            return subsystem
    return {"summary": node.description, "paths": evidence_paths, "key_symbols": []}


def _evidence_excerpt_map(material: RepositoryMaterial) -> dict[str, str]:
    excerpts: dict[str, str] = {}
    package_files = material.package_files or ""
    matches = list(
        re.finditer(
            r"^=== selected evidence: (?P<path>.+?) ===\n(?P<content>.*?)(?=^=== selected evidence: |\Z)",
            package_files,
            flags=re.MULTILINE | re.DOTALL,
        )
    )
    for match in matches:
        path = match.group("path").strip()
        content = match.group("content").strip()
        if path and content:
            excerpts[path] = content
    if material.readme_content:
        excerpts.setdefault("README.md", material.readme_content)
    return excerpts


def _parse_updates(raw: Any) -> list[dict[str, Any]]:
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(parsed, dict):
        parsed = parsed.get("nodes") or parsed.get("updates") or []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _apply_update(node: RepoGraphNode, update: dict[str, Any]) -> RepoGraphNode:
    label = _clean_text(update.get("label")) or node.label
    description = _clean_text(update.get("description")) or node.description
    content = str(update.get("content") or "").strip() or node.content
    if node.type != "moc" and not content.lstrip().startswith("---"):
        content = _with_frontmatter(label, node.type, description, content)
    return node.model_copy(update={"label": label, "description": description, "content": content})


def _with_frontmatter(label: str, node_type: str, description: str, content: str) -> str:
    return "\n".join([
        "---",
        f"title: {label}",
        f"type: {node_type}",
        f"description: {description}",
        "---",
        "",
        content.strip(),
    ]).strip()


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text


def _is_high_value_node(node: RepoGraphNode) -> bool:
    text = f"{node.description}\n{node.content}".lower()
    if any(phrase in text for phrase in LOW_VALUE_PHRASES):
        return False
    body = re.sub(r"^---\n.*?\n---\n", "", node.content, flags=re.DOTALL).strip()
    body = re.split(r"\n## Evidence\b", body, maxsplit=1, flags=re.IGNORECASE)[0]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if len(part.strip()) >= 120]
    if len(paragraphs) < 2:
        return False
    unique_words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", body)}
    return len(unique_words) >= 35


__all__ = ["RepoGraphDSPySynthesizer", "enrich_repo_graph_with_dspy"]
