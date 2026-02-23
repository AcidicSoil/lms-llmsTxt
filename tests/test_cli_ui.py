from __future__ import annotations

from pathlib import Path

import pytest

from lms_llmsTxt import cli
from lms_llmsTxt.models import GenerationArtifacts


def test_build_graph_viewer_url_prefers_hypergraph_relative_path(tmp_path: Path) -> None:
    repo_root = tmp_path
    hypergraph_dir = repo_root / "hypergraph"
    graph_path = repo_root / "artifacts" / "owner" / "repo" / "graph" / "repo.graph.json"
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text("{}", encoding="utf-8")

    url = cli.build_graph_viewer_url(graph_path, hypergraph_dir=hypergraph_dir)

    assert "mode=load-repo-graph" in url
    assert "autoLoad=1" in url
    assert "..%2Fartifacts%2Fowner%2Frepo%2Fgraph%2Frepo.graph.json" in url


def test_main_rejects_ui_without_generate_graph() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["https://github.com/pallets/flask", "--ui"])
    assert excinfo.value.code == 2


def test_main_prints_viewer_url_when_ui_requested(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    graph_path = "/tmp/artifacts/pallets/flask/graph/repo.graph.json"

    def fake_run_generation(*args, **kwargs):
        return GenerationArtifacts(
            llms_txt_path="/tmp/artifacts/pallets/flask/flask-llms.txt",
            llms_full_path=None,
            graph_json_path=graph_path,
            force_graph_path="/tmp/artifacts/pallets/flask/graph/repo.force.json",
            graph_nodes_dir="/tmp/artifacts/pallets/flask/graph/nodes",
        )

    monkeypatch.setattr(cli, "run_generation", fake_run_generation)
    monkeypatch.setattr(cli, "_default_hypergraph_dir", lambda: Path("/tmp/hypergraph"))

    rc = cli.main(
        [
            "https://github.com/pallets/flask",
            "--generate-graph",
            "--ui",
            "--ui-base-url",
            "http://localhost:3001",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "Graph viewer:" in out
    assert "http://localhost:3001/?" in out
    assert "graphPath=..%2Fartifacts%2Fpallets%2Fflask%2Fgraph%2Frepo.graph.json" in out
