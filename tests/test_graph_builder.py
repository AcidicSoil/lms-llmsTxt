from pathlib import Path

import pytest

from lms_llmsTxt.graph_builder import (
    build_repo_graph,
    emit_graph_files,
    to_force_graph,
    validate_semantic_graph,
)
from lms_llmsTxt.graph_models import RepoGraphNode, RepoSkillGraph
from lms_llmsTxt.repo_digest import RepoDigest


def test_build_repo_graph_from_llms_markdown_uses_sections_and_links():
    from lms_llmsTxt.graph_builder import build_repo_graph_from_llms_markdown

    graph = build_repo_graph_from_llms_markdown(
        """
# Example Project

## Core Runtime
- [Pipeline](https://github.com/acme/repo/blob/main/src/runtime/pipeline.py): coordinates staged generation.
- [Config](src/runtime/config.py): keeps runtime settings together.

## Tests
- [Runtime tests](tests/runtime/test_pipeline.py): validates pipeline behavior.
        """.strip()
    )

    labels = {node.label for node in graph.nodes}
    evidence_paths = {evidence.path for node in graph.nodes for evidence in node.evidence}

    assert graph.topic == "Example Project"
    assert "Core Runtime" in labels
    assert "Tests" in labels
    assert "src/runtime/pipeline.py" in evidence_paths
    assert "tests/runtime/test_pipeline.py" in evidence_paths


def test_graph_builder_emits_expected_files(tmp_path: Path):
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="Core services and adapters",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py"],
                "summary": "Authentication subsystem",
                "key_symbols": ["login", "logout"],
            }
        ],
        key_dependencies=["requests"],
        entry_points=["src/main.py"],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    assert graph.nodes[0].type == "moc"
    assert len(graph.nodes) >= 2
    paths = emit_graph_files(graph, tmp_path)
    assert (tmp_path / "repo.graph.json").exists()
    assert (tmp_path / "repo.force.json").exists()
    assert (tmp_path / "nodes" / "moc.md").exists()
    assert paths["graph_json"].endswith("repo.graph.json")


def test_repo_graph_adds_evidence_backed_topology_and_node_variety():
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="CLI, auth, docs, and tests",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py", "src/auth/tokens.py"],
                "summary": "Authentication source code",
                "key_symbols": ["login", "TokenStore"],
            },
            {
                "name": "tests/auth",
                "paths": ["tests/auth/test_login.py"],
                "summary": "Authentication regression coverage",
                "key_symbols": ["test_login", "TokenStore"],
            },
            {
                "name": "docs/auth-guide",
                "paths": ["docs/auth-guide.md"],
                "summary": "Authentication guide and usage pattern",
                "key_symbols": ["login"],
            },
            {
                "name": "cmd/example",
                "paths": ["cmd/example/cli.py"],
                "summary": "CLI entry point",
                "key_symbols": ["main"],
            },
        ],
        key_dependencies=["requests"],
        entry_points=["cmd/example/cli.py"],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    node_ids = {node.id for node in graph.nodes}
    non_moc_nodes = [node for node in graph.nodes if node.type != "moc"]

    assert graph.nodes[0].type == "moc"
    assert {node.type for node in non_moc_nodes} >= {"concept", "pattern", "gotcha"}
    assert any(node.links for node in non_moc_nodes)
    assert all(target in node_ids for node in graph.nodes for target in node.links)
    assert all("Related traversal" not in node.content for node in non_moc_nodes)
    assert all("This node is grounded in repository paths" not in node.content for node in non_moc_nodes)
    assert any("Related concepts" in node.content for node in non_moc_nodes)
    assert any("[[" in node.content for node in non_moc_nodes if node.links)


def test_force_graph_uses_deduped_valid_edges_and_degree_sizing():
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="Auth and tests",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py"],
                "summary": "Authentication source code",
                "key_symbols": ["login"],
            },
            {
                "name": "tests/auth",
                "paths": ["tests/auth/test_login.py"],
                "summary": "Authentication tests",
                "key_symbols": ["login"],
            },
        ],
        key_dependencies=[],
        entry_points=[],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    force = to_force_graph(graph)
    edge_keys = {tuple(sorted((link.source, link.target))) for link in force.links}
    node_values = {node.id: node.val for node in force.nodes}

    assert len(force.links) == len(edge_keys)
    assert any(key == ("src-auth", "tests-auth") for key in edge_keys)
    assert node_values["src-auth"] > 1.5
    assert node_values["tests-auth"] > 1.5


def test_semantic_graph_validation_rejects_provenance_boilerplate():
    graph = RepoSkillGraph(
        topic="Example Repo",
        nodes=[
            RepoGraphNode(
                id="moc",
                label="Example Repo Map",
                type="moc",
                description="Repository overview",
                content="# Example Repo\n\nA semantic overview of the repository.",
                links=["bad-node"],
            ),
            RepoGraphNode(
                id="bad-node",
                label="Bad Node",
                type="concept",
                description="This node is grounded in repository paths.",
                content=(
                    "---\n"
                    "title: Bad Node\n"
                    "type: concept\n"
                    "description: Bad node\n"
                    "---\n\n"
                    "# Bad Node\n\n"
                    "This node is grounded in repository paths that indicate a concept role.\n\n"
                    "Another paragraph that would otherwise be long enough to pass structure validation."
                ),
                links=[],
            ),
        ],
    )

    with pytest.raises(ValueError, match="provenance boilerplate"):
        validate_semantic_graph(graph)


def test_repo_digest_uses_selected_evidence_content_for_graph_summaries():
    from lms_llmsTxt.models import RepositoryMaterial
    from lms_llmsTxt.repo_digest import build_repo_digest

    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="docs/knowledge-base.md\ndocs/api-reference.md",
        readme_content="# Example\n\nA docs repo.",
        package_files=(
            "=== selected evidence: docs/knowledge-base.md ===\n"
            "Knowledge base integration connects local models to user-owned corpora. "
            "It explains retrieval, grounding, and answer workflows.\n\n"
            "=== selected evidence: docs/api-reference.md ===\n"
            "The API reference documents concrete methods, arguments, return shapes, "
            "and integration boundaries for SDK users."
        ),
        default_branch="main",
        is_private=False,
    )

    digest = build_repo_digest(material, topic="Docs")
    summaries = {subsystem["name"]: subsystem["summary"] for subsystem in digest.subsystems}

    assert "Knowledge base integration connects local models" in summaries["docs/knowledge-base.md"]
    assert "concrete methods" in summaries["docs/api-reference.md"]

    graph = build_repo_graph(digest)
    non_moc_content = "\n".join(node.content for node in graph.nodes if node.type != "moc")
    assert "Knowledge base integration connects local models" in non_moc_content
    assert "concrete methods" in non_moc_content
    assert "This area groups the behavior" not in non_moc_content
