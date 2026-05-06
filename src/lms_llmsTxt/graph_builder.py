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

PROVENANCE_ONLY_PHRASES = (
    "this node is grounded in repository paths",
    "this node is based on evidence anchors",
    "use it to understand ownership boundaries",
    "operational risk or validation surface",
    "no key symbols were extracted",
    "related traversal",
    "uploaded artifact note",
    "evidence-backed neighbors",
)


def _contains_provenance_boilerplate(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in PROVENANCE_ONLY_PHRASES)


def validate_semantic_node(node: RepoGraphNode) -> None:
    if _contains_provenance_boilerplate(f"{node.description}\n{node.content}"):
        raise ValueError(f"Node {node.id} used provenance boilerplate instead of semantic synthesis")

    if node.type != "moc":
        body_before_evidence = node.content.lower().split("## evidence", 1)[0]
        paragraphs = [
            part.strip()
            for part in body_before_evidence.split("\n\n")
            if len(part.strip()) > 80
        ]
        if len(paragraphs) < 2:
            raise ValueError(f"Node {node.id} does not contain enough semantic explanation before evidence")
        if node.label.strip().startswith(("/", "./")) or "/" in node.label:
            raise ValueError(f"Node {node.id} has a raw path label instead of a concept label")


def validate_semantic_graph(graph: RepoSkillGraph) -> None:
    moc_count = sum(1 for node in graph.nodes if node.type == "moc")
    if moc_count != 1:
        raise ValueError(f"Repo graph must contain exactly one MOC node; found {moc_count}")

    node_ids = {node.id for node in graph.nodes}
    if len(node_ids) != len(graph.nodes):
        raise ValueError("Repo graph contains duplicate node ids")

    for node in graph.nodes:
        validate_semantic_node(node)
        for target in node.links:
            if target not in node_ids:
                raise ValueError(f"Node {node.id} links to unknown node {target}")


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


_PATHISH_RE = re.compile(r"(?:^|\s)(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+")


def _looks_like_path_inventory(text: str) -> bool:
    if not text.strip():
        return True
    path_hits = len(_PATHISH_RE.findall(text))
    word_hits = len(re.findall(r"[A-Za-z]{3,}", text))
    return path_hits >= 2 and path_hits >= max(1, word_hits // 6)


def _clean_label_part(part: str) -> str:
    part = part.strip("_-. ")
    part = re.sub(r"^\d+[_-]*", "", part)
    if not part:
        return ""
    lower = part.lower()
    acronyms = {
        "api": "API",
        "sdk": "SDK",
        "cli": "CLI",
        "ui": "UI",
        "llm": "LLM",
        "mcp": "MCP",
        "rest": "REST",
        "json": "JSON",
        "ts": "TypeScript",
        "js": "JavaScript",
    }
    if lower in acronyms:
        return acronyms[lower]
    return " ".join(piece.capitalize() for piece in re.split(r"[-_\s]+", part) if piece)


def _humanize_subsystem_label(name: str) -> str:
    parts = [_clean_label_part(part) for part in re.split(r"[/]+", name) if part]
    parts = [part for part in parts if part]
    if not parts:
        return "Repository Capability"
    # Keep the most meaningful two levels while dropping numeric documentation scaffolding.
    if len(parts) > 2:
        parts = parts[-2:]
    return " ".join(parts)


def _humanize_subsystem_name(name: str) -> str:
    return _humanize_subsystem_label(name)


def _theme_from_paths(paths: list[str]) -> str:
    joined = " ".join(paths).lower()
    if "api-reference" in joined or "api_reference" in joined:
        return "api_reference"
    if any(token in joined for token in ("quickstart", "getting-started", "tutorial")):
        return "quickstart"
    if any(token in joined for token in ("plugin", "provider", "adapter")):
        return "extension"
    if any(token in joined for token in ("preset", "config", "configuration")):
        return "configuration"
    if any(token in joined for token in ("cli", "command", "daemon")):
        return "cli"
    if any(token in joined for token in ("model", "llm", "prediction")):
        return "model_runtime"
    if any(token in joined for token in ("doc", ".md", ".mdx")):
        return "documentation"
    return "implementation"


def _semantic_description(subsystem: dict, *, node_type: GraphNodeType) -> str:
    name = str(subsystem["name"])
    raw_summary = str(subsystem.get("summary") or "").strip()
    paths = [str(path) for path in subsystem.get("paths", [])]
    label = _humanize_subsystem_label(name)
    theme = _theme_from_paths(paths)

    if raw_summary and not _contains_provenance_boilerplate(raw_summary) and not _looks_like_path_inventory(raw_summary):
        return raw_summary

    if theme == "api_reference":
        return f"Explains how the {label} surface exposes concrete calls, parameters, and return shapes that developers rely on."
    if theme == "quickstart":
        return f"Explains how {label} introduces the first successful workflow and sets expectations for later integration work."
    if theme == "extension":
        return f"Explains how {label} extends the product through provider, plugin, or adapter boundaries."
    if theme == "configuration":
        return f"Explains how {label} shapes runtime behavior through presets, configuration, or setup decisions."
    if theme == "cli":
        return f"Explains how {label} turns repository capabilities into command-line workflows and operational entry points."
    if theme == "model_runtime":
        return f"Explains how {label} manages model-facing runtime behavior such as loading, prediction, or API calls."
    if node_type == "gotcha":
        return f"Explains the failure mode around {label} and what a developer should verify before changing it."
    if node_type == "pattern":
        return f"Explains the reusable workflow represented by {label} and where it fits in the repository."
    return f"Explains the role {label} plays in the repository and how nearby files depend on that concept."


def _related_concept_sentence(related_links: list[str]) -> str:
    if not related_links:
        return "This node has no high-confidence neighbor in the current graph, so treat it as a focused local concept rather than a broad architecture claim."
    if len(related_links) == 1:
        return f"It connects most directly to [[{related_links[0]}]], because the two areas share source paths, naming, symbols, or integration boundaries."
    linked = ", ".join(f"[[{node_id}]]" for node_id in related_links[:3])
    return f"It connects most directly to {linked}, because those neighboring areas share source paths, naming, symbols, or integration boundaries."


def _developer_action(theme: str, label: str) -> str:
    if theme == "api_reference":
        return f"Care about {label} when changing call signatures, request/response schemas, examples, or generated client surfaces, because small inconsistencies here become user-facing integration bugs."
    if theme == "quickstart":
        return f"Care about {label} when changing setup, authentication, installation, or first-run flows, because this material defines the reader's first successful path through the product."
    if theme == "extension":
        return f"Care about {label} when adding providers, plugins, adapters, or customization hooks, because extension points need stable boundaries between user code and internal behavior."
    if theme == "configuration":
        return f"Care about {label} when defaults, presets, environment variables, or runtime options change, because configuration drift creates hard-to-debug behavior differences."
    if theme == "cli":
        return f"Care about {label} when commands, daemon behavior, local services, or developer automation changes, because it is often the operational face of the system."
    if theme == "model_runtime":
        return f"Care about {label} when model loading, prediction, token limits, or local runtime behavior changes, because those details determine whether the system responds reliably under resource constraints."
    return f"Care about {label} when changing the nearby files, because this area marks a responsibility boundary in the repository rather than a random collection of paths."


def _failure_mode(theme: str, label: str) -> str:
    if theme == "api_reference":
        return f"If {label} is treated as a passive file list, documentation can drift away from the actual API contract and users will copy examples that no longer match runtime behavior."
    if theme == "quickstart":
        return f"If {label} is not kept coherent, readers may fail before they reach the deeper docs even when the underlying product still works."
    if theme == "extension":
        return f"If {label} is misunderstood, plugin or provider code can leak implementation assumptions across the public extension boundary."
    if theme == "configuration":
        return f"If {label} is changed without tracking defaults and override precedence, users can observe behavior that appears nondeterministic across environments."
    if theme == "cli":
        return f"If {label} is changed without respecting process and command boundaries, local workflows can hang, race, or report success before the system is actually ready."
    if theme == "model_runtime":
        return f"If {label} is misunderstood, the system can make the wrong tradeoff between latency, memory, model lifecycle, and correctness."
    return f"If {label} is treated only as provenance, the graph remains accurate but not useful: it tells users where files are without explaining the decision they need to make."


def _content_for_subsystem(
    subsystem: dict,
    *,
    node_type: GraphNodeType,
    related_links: list[str],
) -> str:
    name = str(subsystem["name"])
    paths = [str(path) for path in subsystem.get("paths", [])[:8]]
    key_symbols = [str(symbol) for symbol in subsystem.get("key_symbols", [])[:12]]
    concept_name = _humanize_subsystem_name(name)
    description = _semantic_description(subsystem, node_type=node_type)
    theme = _theme_from_paths(paths)

    focus_label = {
        "concept": "Concept description",
        "pattern": "Pattern description",
        "gotcha": "Failure mode to watch",
        "moc": "Overview",
    }[node_type]

    symbols_sentence = (
        f"Concrete implementation signals include {', '.join(f'`{symbol}`' for symbol in key_symbols[:6])}."
        if key_symbols
        else "The current digest does not expose named public symbols for this area, so the strongest signals are the path names and neighboring docs."
    )
    evidence_sentence = (
        f"The strongest evidence paths include {', '.join(f'`{path}`' for path in paths[:4])}."
        if paths
        else "The current digest did not expose concrete paths for this area."
    )
    related_sentence = _related_concept_sentence(related_links)
    developer_action = _developer_action(theme, concept_name)
    failure_mode = _failure_mode(theme, concept_name)

    return (
        f"---\n"
        f"title: {concept_name}\n"
        f"type: {node_type}\n"
        f"description: {description}\n"
        f"---\n\n"
        f"{description}\n\n"
        f"**{focus_label.upper()}: {description.upper()}**\n\n"
        f"This concept describes the repository responsibility behind `{name}`. "
        f"Rather than reading it as a bundle of filenames, treat it as the place where the project explains, exposes, or protects the {concept_name.lower()} workflow. "
        f"{evidence_sentence}\n\n"
        f"{developer_action} {symbols_sentence}\n\n"
        f"## Related concepts\n\n"
        f"{related_sentence}\n\n"
        f"{failure_mode}\n\n"
        f"## Evidence\n\n"
        f"{_format_evidence_lines(paths)}\n"
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
            f"- Start with [[{node.id}]] when investigating {node.label}; it summarizes the responsibility and neighboring concepts for that part of the project."
        )

    type_summary = ", ".join(f"{count} {node_type}" for node_type, count in sorted(type_counts.items()))
    return (
        f"# {digest.topic}\n\n"
        f"This map summarizes the repository as a set of developer-facing concepts rather than a flat file list. "
        f"It contains {type_summary or 'no classified subsystem nodes'} so agents can distinguish architecture, reusable approaches, and failure modes before making changes.\n\n"
        f"## Domain Clusters\n"
        + "\n".join(cluster_lines)
        + "\n\n## Explorations Needed\n"
        "- Which subsystem boundaries should become explicit ownership documentation?\n"
        "- Which pattern and gotcha nodes should become targeted regression tests?\n"
        "- Which concepts need richer source excerpts in the next graph pass?\n"
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
                label=_humanize_subsystem_label(str(subsystem["name"])),
                type=node_type,
                description=_semantic_description(subsystem, node_type=node_type),
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

    graph = RepoSkillGraph(topic=digest.topic, nodes=[moc, *nodes])
    validate_semantic_graph(graph)
    return graph


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
