from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from .config import AppConfig
from .graph_models import GraphNodeEvidence, RepoGraphNode, RepoSkillGraph
from .models import RepositoryMaterial
from .repo_digest import RepoDigest

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 42_000
MAX_EXCERPT_CHARS = 6_000
MAX_SUBSYSTEMS = 18

PROVENANCE_ONLY_PHRASES = (
    "this node is grounded in repository paths",
    "use it to understand ownership boundaries",
    "operational risk or validation surface",
    "no key symbols were extracted",
    "related traversal",
    "uploaded artifact note",
    "evidence-backed neighbors",
    "sparse uploaded repo graph",
)

SEMANTIC_SYSTEM_PROMPT = """You are a domain knowledge graph architect.

Given repository evidence, infer the durable concepts, patterns, and gotchas a developer must understand. Produce a semantic learning map, not a file inventory, provenance map, audit log, or generic repository traversal guide.

Prefer concept-level labels over raw package/path labels. For example:
- Bad: packages/google-vertex
- Good: Google Vertex Provider Integration
- Better: Provider-Specific Adapter Boundary, if the concept generalizes across providers.

Return JSON only with this shape:
{
  "topic": "project or repo name",
  "nodes": [
    {
      "id": "kebab-case-id",
      "label": "Human Readable Concept Label",
      "type": "moc" | "concept" | "pattern" | "gotcha",
      "description": "Specific one-sentence explanation of what this node teaches",
      "content": "Markdown content with [[wikilinks]] woven into explanatory prose",
      "links": ["other-node-id"],
      "source_subsystems": ["subsystem names or evidence paths"]
    }
  ]
}

Rules:
- Generate 12-18 nodes total when enough evidence exists; fewer is acceptable for tiny repos.
- Exactly one node must be type "moc".
- The MOC should explain the repo's conceptual map and link to important nodes in prose.
- Every non-MOC node must include YAML frontmatter with title, type, and description.
- Every non-MOC node must explain what the concept means, why it exists, at least one concrete mechanism/API/file behavior/architecture boundary from evidence, when a developer should care, and what breaks if misunderstood.
- Evidence/path references are allowed only as compact support near the bottom, never as the main story.
- Do not output: "This node is grounded in repository paths", "Use it to understand ownership boundaries", "Operational risk or validation surface", "No key symbols were extracted", "Related traversal", "Uploaded artifact note", or other provenance/debug boilerplate.
"""


SEMANTIC_GRAPH_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["topic", "nodes"],
    "properties": {
        "topic": {"type": "string"},
        "nodes": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "label",
                    "type",
                    "description",
                    "content",
                    "links",
                    "source_subsystems",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string", "enum": ["moc", "concept", "pattern", "gotcha"]},
                    "description": {"type": "string"},
                    "content": {"type": "string"},
                    "links": {"type": "array", "items": {"type": "string"}},
                    "source_subsystems": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


class SemanticGraphSynthesisError(RuntimeError):
    """Raised when model-authored repo graph synthesis fails validation."""


def build_semantic_repo_graph(
    digest: RepoDigest,
    material: RepositoryMaterial,
    config: AppConfig,
) -> RepoSkillGraph:
    """Generate an LLM-authored, evidence-backed repo skill graph."""
    if not config.lm_model:
        raise SemanticGraphSynthesisError("LMSTUDIO_MODEL is not configured")

    url = _chat_completion_url(config)
    headers = {
        "Authorization": f"Bearer {config.lm_api_key or 'lm-studio'}",
        "Content-Type": "application/json",
    }

    last_error: SemanticGraphSynthesisError | None = None
    for response_format in _response_format_attempts():
        payload = _chat_completion_payload(
            digest,
            material,
            config,
            response_format=response_format,
        )
        try:
            raw_content = _post_chat_completion(
                url,
                headers,
                payload,
                response_format=response_format,
            )
            graph = _parse_graph(raw_content, digest)
            validate_semantic_graph(graph)
            return graph
        except SemanticGraphSynthesisError as exc:
            last_error = exc
            if response_format == "none" or not _is_response_format_rejection(exc):
                raise
            logger.warning(
                "Semantic repo graph request using response_format=%s failed; retrying without response_format: %s",
                response_format,
                exc,
            )

    raise last_error or SemanticGraphSynthesisError("semantic graph synthesis failed")


def validate_semantic_graph(graph: RepoSkillGraph) -> None:
    if not graph.nodes:
        raise SemanticGraphSynthesisError("semantic graph has no nodes")

    moc_count = sum(1 for node in graph.nodes if node.type == "moc")
    if moc_count != 1:
        raise SemanticGraphSynthesisError(f"semantic graph must have exactly one MOC; found {moc_count}")

    node_ids = {node.id for node in graph.nodes}
    if len(node_ids) != len(graph.nodes):
        raise SemanticGraphSynthesisError("semantic graph contains duplicate node ids")

    for node in graph.nodes:
        text = f"{node.description}\n{node.content}".lower()
        for phrase in PROVENANCE_ONLY_PHRASES:
            if phrase in text:
                raise SemanticGraphSynthesisError(
                    f"Node {node.id} used provenance boilerplate instead of semantic synthesis: {phrase}"
                )

        invalid_links = [target for target in node.links if target not in node_ids]
        if invalid_links:
            raise SemanticGraphSynthesisError(f"Node {node.id} links to missing nodes: {invalid_links}")

        if node.type != "moc":
            if not node.content.lstrip().startswith("---"):
                raise SemanticGraphSynthesisError(f"Node {node.id} is missing YAML frontmatter")
            explanatory_body = _strip_frontmatter_and_evidence(node.content)
            paragraphs = [p for p in re.split(r"\n\s*\n", explanatory_body) if len(p.strip()) > 120]
            if len(paragraphs) < 2:
                raise SemanticGraphSynthesisError(f"Node {node.id} lacks substantial explanatory paragraphs")
            if _path_line_ratio(node.content) > 0.45:
                raise SemanticGraphSynthesisError(f"Node {node.id} is mostly paths instead of explanation")
            if _looks_like_raw_path(node.label):
                raise SemanticGraphSynthesisError(f"Node {node.id} uses a raw path label instead of a concept label")
            evidence_index = node.content.lower().find("## evidence")
            first_heading_index = node.content.find("# ")
            if evidence_index != -1 and first_heading_index != -1 and evidence_index < first_heading_index:
                raise SemanticGraphSynthesisError(f"Node {node.id} puts evidence before explanatory content")


def _chat_completion_payload(
    digest: RepoDigest,
    material: RepositoryMaterial,
    config: AppConfig,
    *,
    response_format: str = "json_schema",
) -> dict[str, Any]:
    source_bundle = _build_source_bundle(digest, material)
    user_prompt = (
        f"Repo topic: {digest.topic}\n\n"
        f"Architecture summary:\n{digest.architecture_summary}\n\n"
        f"Primary language: {digest.primary_language}\n"
        f"Entry points: {', '.join(digest.entry_points) or 'unknown'}\n"
        f"Key dependencies: {', '.join(digest.key_dependencies[:24]) or 'unknown'}\n\n"
        f"Subsystem candidates as JSON:\n{json.dumps(digest.subsystems[:MAX_SUBSYSTEMS], indent=2)}\n\n"
        f"Source excerpts:\n{source_bundle}\n\n"
        "Create concept-level graph nodes from the evidence. Keep provenance secondary and compact."
    )
    payload: dict[str, Any] = {
        "model": config.lm_model,
        "messages": [
            {"role": "system", "content": SEMANTIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.35,
        "max_tokens": min(config.max_output_tokens, 8192),
    }
    if response_format == "json_schema":
        payload["response_format"] = _semantic_graph_response_format()
    elif response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
    return payload


def _chat_completion_url(config: AppConfig) -> str:
    url = config.lm_api_base.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    return url


def _response_format_attempts() -> tuple[str, ...]:
    # LM Studio's OpenAI-compatible server rejects legacy json_object mode for
    # several local models. Prefer JSON Schema, then retry without a structured
    # response_format if the server rejects structured output for the loaded model.
    return ("json_schema", "none")


def _post_chat_completion(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    response_format: str,
) -> str:
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise SemanticGraphSynthesisError(f"LM Studio request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = _response_error_detail(response)
        raise SemanticGraphSynthesisError(
            f"LM Studio chat completion failed with status {response.status_code} "
            f"using response_format={response_format}: {detail}"
        )

    try:
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SemanticGraphSynthesisError(
            f"LM Studio returned an unexpected chat completion payload: "
            f"{_truncate(response.text, 1000)}"
        ) from exc

    if not raw_content:
        raise SemanticGraphSynthesisError("LM Studio returned an empty semantic graph response")
    return str(raw_content)


def _response_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return _truncate(response.text, 1200) or response.reason
    return _truncate(json.dumps(payload, ensure_ascii=False), 1200)


def _is_response_format_rejection(error: SemanticGraphSynthesisError) -> bool:
    message = str(error).lower()
    return (
        "response_format" in message
        or "json_schema" in message
        or "schema" in message
        or "status 400" in message
    )


def _truncate(value: str, max_chars: int) -> str:
    return value if len(value) <= max_chars else value[:max_chars] + "...[truncated]"


def _semantic_graph_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "repo_skill_graph",
            "strict": True,
            "schema": SEMANTIC_GRAPH_JSON_SCHEMA,
        },
    }

def _build_source_bundle(digest: RepoDigest, material: RepositoryMaterial) -> str:
    blocks: list[str] = []
    if material.readme_content:
        blocks.append(_excerpt_block("README.md", material.readme_content))
    if material.package_files:
        for path, content in _split_package_blocks(material.package_files):
            blocks.append(_excerpt_block(path, content))

    if not blocks:
        blocks.extend(
            _excerpt_block(str(subsystem.get("name", "subsystem")), str(subsystem.get("summary", "")))
            for subsystem in digest.subsystems[:MAX_SUBSYSTEMS]
        )

    bundle = "\n\n---\n\n".join(blocks)
    return bundle[:MAX_SOURCE_CHARS]


def _split_package_blocks(package_files: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^=== selected evidence: (?P<path>.+?) ===\n", package_files, flags=re.MULTILINE))
    if not matches:
        return [("package_files.txt", package_files)]

    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(package_files)
        blocks.append((match.group("path").strip(), package_files[start:end].strip()))
    prefix = package_files[: matches[0].start()].strip()
    if prefix:
        blocks.insert(0, ("package_files.txt", prefix))
    return blocks


def _excerpt_block(path: str, content: str) -> str:
    excerpt = content.strip()[:MAX_EXCERPT_CHARS]
    return f"### {path}\n\n{excerpt}"


def _parse_graph(raw_content: str, digest: RepoDigest) -> RepoSkillGraph:
    raw = raw_content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    parsed = json.loads(raw)

    used_ids: set[str] = set()
    nodes: list[RepoGraphNode] = []
    source_lookup = _evidence_lookup(digest)
    for raw_node in parsed.get("nodes", []):
        node_id = _unique_slug(str(raw_node.get("id") or raw_node.get("label") or "node"), used_ids)
        label = str(raw_node.get("label") or _title_from_slug(node_id)).strip()
        node_type = raw_node.get("type") if raw_node.get("type") in {"moc", "concept", "pattern", "gotcha"} else "concept"
        description = str(raw_node.get("description") or f"Explains {label} in {digest.topic}.").strip()
        content = str(raw_node.get("content") or "").strip()
        if node_type != "moc" and not content.startswith("---"):
            content = _with_frontmatter(label, node_type, description, content)
        source_keys = [str(item) for item in raw_node.get("source_subsystems", []) if str(item).strip()]
        evidence = _evidence_for_sources(source_keys, source_lookup)
        links = [_slug(str(target)) for target in raw_node.get("links", [])]
        nodes.append(
            RepoGraphNode(
                id=node_id,
                label=label,
                type=node_type,
                description=description,
                content=content,
                links=links,
                evidence=evidence,
                artifacts=["repo.graph.json"],
                tags=["semantic", digest.primary_language, node_type],
            )
        )

    node_ids = {node.id for node in nodes}
    for node in nodes:
        node.links = [target for target in dict.fromkeys(node.links) if target in node_ids and target != node.id]

    return RepoSkillGraph(topic=str(parsed.get("topic") or digest.topic), nodes=nodes)


def _evidence_lookup(digest: RepoDigest) -> dict[str, list[GraphNodeEvidence]]:
    lookup: dict[str, list[GraphNodeEvidence]] = {}
    for subsystem in digest.subsystems:
        name = str(subsystem.get("name", ""))
        evidence = [
            GraphNodeEvidence(path=str(path), start_line=1, end_line=1, artifact_ref="repo_digest")
            for path in subsystem.get("paths", [])[:8]
        ]
        lookup[name] = evidence
        for item in evidence:
            lookup.setdefault(item.path, []).append(item)
    return lookup


def _evidence_for_sources(source_keys: list[str], source_lookup: dict[str, list[GraphNodeEvidence]]) -> list[GraphNodeEvidence]:
    seen: set[str] = set()
    evidence: list[GraphNodeEvidence] = []
    for key in source_keys:
        for ev in source_lookup.get(key, []):
            fingerprint = f"{ev.path}:{ev.start_line}:{ev.end_line}:{ev.artifact_ref}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            evidence.append(ev)
            if len(evidence) >= 8:
                return evidence
    return evidence


def _strip_frontmatter_and_evidence(content: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
    return re.split(r"\n## Evidence\b", text, maxsplit=1, flags=re.IGNORECASE)[0]


def _path_line_ratio(content: str) -> float:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return 1.0
    path_lines = [line for line in lines if re.search(r"`?([A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+`?", line)]
    return len(path_lines) / len(lines)


def _looks_like_raw_path(label: str) -> bool:
    return "/" in label or bool(re.match(r"^(src|app|lib|packages|tests|docs|examples|content)[/-]", label.lower()))


def _with_frontmatter(label: str, node_type: str, description: str, content: str) -> str:
    return "\n".join([
        "---",
        f"title: {label}",
        f"type: {node_type}",
        f"description: {description}",
        "---",
        "",
        content,
    ])


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


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)
