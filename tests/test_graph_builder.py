from pathlib import Path

from lms_llmsTxt.graph_builder import build_repo_graph, emit_graph_files, to_force_graph
from lms_llmsTxt.repo_digest import RepoDigest


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
    assert any("Related traversal" in node.content for node in non_moc_nodes)
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
