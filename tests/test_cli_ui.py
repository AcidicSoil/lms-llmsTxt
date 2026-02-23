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
    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(reused_existing=True, ready=True),
    )
    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", lambda url: True)

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
    assert "UI status:" in out
    assert "already running" in out
    assert "Browser:" in out
    assert "opened" in out


def test_main_starts_ui_when_not_running(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run_generation(*args, **kwargs):
        return GenerationArtifacts(
            llms_txt_path="/tmp/artifacts/a/b.txt",
            llms_full_path=None,
            graph_json_path="/tmp/artifacts/o/r/graph/repo.graph.json",
        )

    monkeypatch.setattr(cli, "run_generation", fake_run_generation)
    monkeypatch.setattr(cli, "_default_hypergraph_dir", lambda: Path("/tmp/hypergraph"))
    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(
            started_process=True,
            ready=True,
            pid=12345,
            log_path="/tmp/hypergraph-dev.log",
        ),
    )
    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", lambda url: True)

    rc = cli.main(["https://github.com/acme/repo", "--generate-graph", "--ui"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "started background dev server (pid=12345)" in out
    assert "log: /tmp/hypergraph-dev.log" in out
    assert "\n  - ready" in out
    assert "Browser:" in out
    assert "opened" in out


def test_main_ui_no_open_skips_browser(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run_generation(*args, **kwargs):
        return GenerationArtifacts(
            llms_txt_path="/tmp/artifacts/a/b.txt",
            llms_full_path=None,
            graph_json_path="/tmp/artifacts/o/r/graph/repo.graph.json",
        )

    monkeypatch.setattr(cli, "run_generation", fake_run_generation)
    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(reused_existing=True, ready=True),
    )

    called = {"browser": 0}

    def fake_open(url: str) -> bool:
        called["browser"] += 1
        return True

    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", fake_open)

    rc = cli.main(["https://github.com/acme/repo", "--generate-graph", "--ui", "--ui-no-open"])
    out = capsys.readouterr().out

    assert rc == 0
    assert called["browser"] == 0
    assert "Browser:" not in out


def test_ensure_hypergraph_ui_running_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert status.reused_existing is True
    assert status.ready is True
    assert status.started_process is False
