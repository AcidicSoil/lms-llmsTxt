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

    status = cli.ensure_hypergraph_ui_running("http://localhost:3010")

    assert status.reused_existing is True
    assert status.ready is True
    assert status.started_process is False


def test_spawn_hypergraph_dev_server_sets_port_from_ui_base_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class FakeProcess:
        pid = 4242

    class FakePopen:
        def __new__(cls, args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})
            return FakeProcess()

    monkeypatch.setattr(cli, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(cli.subprocess, "Popen", FakePopen)

    proc, log_path = cli._spawn_hypergraph_dev_server("http://127.0.0.1:3123")

    assert proc.pid == 4242
    assert log_path.parent == tmp_path / "logs"
    assert calls[0]["args"] == ["npm", "run", "ui:dev"]
    env = calls[0]["kwargs"]["env"]
    assert isinstance(env, dict)
    assert env["PORT"] == "3123"


def test_ensure_hypergraph_ui_running_spawns_with_requested_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[str] = []

    class FakeProcess:
        pid = 999

        def poll(self):
            return None

    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), Path("/tmp/hypergraph-dev.log")

    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3124")

    assert spawned == ["http://localhost:3124"]
    assert status.started_process is True
    assert status.ready is True
    assert status.pid == 999


def test_probe_ui_reachable_accepts_hypergraph_health(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *_args):
            return b'{"app":"hypergraph","status":"ok"}'

    seen_urls: list[str] = []

    def fake_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)

    assert cli._probe_ui_reachable("http://localhost:3000") is True
    assert seen_urls == ["http://localhost:3000/api/health"]


def test_probe_ui_reachable_rejects_non_hypergraph_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *_args):
            return self.body

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/api/health"):
            return FakeResponse(b'{"app":"other-service","status":"ok"}')
        return FakeResponse(b"<html><title>Other app</title></html>")

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)

    assert cli._probe_ui_reachable("http://localhost:3000") is False


def test_probe_ui_reachable_falls_back_to_hypergraph_page_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *_args):
            return self.body

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/api/health"):
            raise cli.HTTPError(request.full_url, 404, "missing", {}, None)
        return FakeResponse(b"<html><title>HyperGraph</title></html>")

    monkeypatch.setattr(cli, "urlopen", fake_urlopen)

    assert cli._probe_ui_reachable("http://localhost:3000") is True


def test_ensure_hypergraph_ui_running_does_not_reuse_wrong_service(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[str] = []

    class FakeProcess:
        pid = 31415

        def poll(self):
            return None

    def fake_probe(*args, **kwargs):
        return False

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), Path("/tmp/hypergraph-dev.log")

    monkeypatch.setattr(cli, "_probe_ui_reachable", fake_probe)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert spawned == ["http://localhost:3000"]
    assert status.reused_existing is False
    assert status.started_process is True
    assert status.ready is True
