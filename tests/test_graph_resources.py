from pathlib import Path

from lms_llmsTxt_mcp import graph_resources


def test_scan_and_read_graph_artifacts(tmp_path: Path, monkeypatch):
    root = tmp_path / "artifacts"
    graph_dir = root / "owner" / "repo" / "graph"
    nodes_dir = graph_dir / "nodes"
    nodes_dir.mkdir(parents=True)
    (graph_dir / "repo.graph.json").write_text("{}", encoding="utf-8")
    (graph_dir / "repo.force.json").write_text("{}", encoding="utf-8")
    (nodes_dir / "moc.md").write_text("# moc", encoding="utf-8")

    monkeypatch.setattr(graph_resources.settings, "LLMSTXT_MCP_ALLOWED_ROOT", root)
    found = graph_resources.scan_graph_artifacts()
    assert any(str(path).endswith("repo.graph.json") for path in found)

    content = graph_resources.read_graph_artifact_chunk("owner/repo/graph/nodes/moc.md", 0, 20)
    assert "moc" in content
