from pathlib import Path

from lms_llmsTxt.graph_builder import build_repo_graph, emit_graph_files
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
