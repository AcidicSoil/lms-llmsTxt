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


def test_main_generates_graph_from_llms_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "demo-llms.txt"
    source.write_text(
        "# Demo\n\n## Runtime\n- [Pipeline](src/pipeline.py): coordinates generation.\n",
        encoding="utf-8",
    )

    rc = cli.main(["--graph-from", str(source)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Graph artifacts generated from llms markdown:" in out
    assert (tmp_path / "demo-llms.graph" / "repo.graph.json").exists()
    assert (tmp_path / "demo-llms.graph" / "repo.force.json").exists()


def test_main_opens_ui_directly_to_graph_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    graph_path = tmp_path / "repo.graph.json"
    graph_path.write_text('{"topic":"Demo","nodes":[]}', encoding="utf-8")
    opened: list[str] = []

    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(reused_existing=True, ready=True),
    )
    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", lambda url: opened.append(url) or True)
    monkeypatch.setattr(cli, "_default_hypergraph_dir", lambda: tmp_path / "hypergraph")

    rc = cli.main(["--ui", str(graph_path), "--ui-base-url", "http://localhost:3009"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Graph viewer:" in out
    assert "http://localhost:3009/?" in out
    assert opened and "repo.graph.json" in opened[0]


def test_main_rejects_repo_ui_without_generate_graph() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["https://github.com/pallets/flask", "--ui"])
    assert excinfo.value.code == 2


def test_main_requires_repo_unless_launching_ui() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code == 2


def test_main_launches_ui_without_repo(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    called = {"generation": 0, "browser": 0}

    def fake_run_generation(*args, **kwargs):
        called["generation"] += 1
        raise AssertionError("lmstxt --ui must not run generation when no repo is supplied")

    def fake_open(url: str) -> bool:
        called["browser"] += 1
        assert url == "http://localhost:3000"
        return True

    monkeypatch.setattr(cli, "run_generation", fake_run_generation)
    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(reused_existing=True, ready=True),
    )
    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", fake_open)

    rc = cli.main(["--ui"])
    out = capsys.readouterr().out

    assert rc == 0
    assert called == {"generation": 0, "browser": 1}
    assert "HyperGraph UI:" in out
    assert "http://localhost:3000" in out
    assert "already running" in out
    assert "Browser:" in out
    assert "opened" in out


def test_main_launches_ui_without_repo_and_no_open(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    called = {"browser": 0}

    monkeypatch.setattr(
        cli,
        "ensure_hypergraph_ui_running",
        lambda *args, **kwargs: cli.UIRuntimeStatus(
            started_process=True,
            ready=True,
            pid=23456,
            log_path="/tmp/hypergraph-dev.log",
        ),
    )
    monkeypatch.setattr(cli, "open_graph_viewer_in_browser", lambda url: called.__setitem__("browser", called["browser"] + 1))

    rc = cli.main(["--ui", "--ui-no-open", "--ui-base-url", "http://localhost:3002"])
    out = capsys.readouterr().out

    assert rc == 0
    assert called["browser"] == 0
    assert "HyperGraph UI:" in out
    assert "http://localhost:3002" in out
    assert "started background dev server (pid=23456)" in out
    assert "log: /tmp/hypergraph-dev.log" in out
    assert "Browser:" not in out


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
    monkeypatch.setattr(cli, "_select_ui_base_url_for_start", lambda url: (url, None))

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


def test_ensure_hypergraph_ui_running_uses_alternate_port_when_requested_port_is_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[str] = []

    class FakeProcess:
        pid = 1001

        def poll(self):
            return None

    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        cli,
        "_select_ui_base_url_for_start",
        lambda url: (
            "http://localhost:3001",
            "Requested UI port 3000 was already in use; started HyperGraph on port 3001 instead.",
        ),
    )

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), Path("/tmp/hypergraph-dev.log")

    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert spawned == ["http://localhost:3001"]
    assert status.ui_base_url == "http://localhost:3001"
    assert status.note == "Requested UI port 3000 was already in use; started HyperGraph on port 3001 instead."
    assert status.started_process is True
    assert status.ready is True


def test_ensure_hypergraph_ui_running_uses_next_free_port_when_requested_port_is_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[str] = []

    class FakeProcess:
        pid = 1001

        def poll(self):
            return None

    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        cli,
        "_port_available_for_dev_server",
        lambda port: port == 3001,
    )

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), Path("/tmp/hypergraph-dev.log")

    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert spawned == ["http://localhost:3001"]
    assert status.started_process is True
    assert status.ready is True
    assert status.ui_base_url == "http://localhost:3001"
    assert status.note == "Requested UI port 3000 was already in use; started HyperGraph on port 3001 instead."


def test_ensure_hypergraph_ui_running_reuses_healthy_tracked_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=2020,
        ui_base_url="http://localhost:3002",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )

    def fake_probe(ui_base_url: str, *args, **kwargs):
        return ui_base_url.rstrip("/") == "http://localhost:3002"

    spawned: list[str] = []
    monkeypatch.setattr(cli, "_probe_ui_reachable", fake_probe)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", lambda ui_base_url: spawned.append(ui_base_url))

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert spawned == []
    assert status.reused_existing is True
    assert status.ready is True
    assert status.pid == 2020
    assert status.ui_base_url == "http://localhost:3002"
    assert "Reused tracked HyperGraph UI" in (status.note or "")


def test_ensure_hypergraph_ui_running_stops_unhealthy_tracked_process_before_spawning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=3030,
        ui_base_url="http://localhost:3002",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )

    class FakeProcess:
        pid = 4040

        def poll(self):
            return None

    stopped: list[float] = []
    spawned: list[str] = []

    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)
    monkeypatch.setattr(cli, "_process_exists", lambda pid: pid == 3030)
    monkeypatch.setattr(cli, "_metadata_matches_lmstxt_ui_process", lambda pid: True)
    monkeypatch.setattr(cli, "stop_tracked_hypergraph_ui", lambda timeout_seconds=5.0: stopped.append(timeout_seconds) or cli.UIStopStatus(stopped=True, pid=3030))
    monkeypatch.setattr(cli, "_port_available_for_dev_server", lambda port: port == 3000)

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), Path("/tmp/hypergraph-dev.log")

    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert stopped == [5.0]
    assert spawned == ["http://localhost:3000"]
    assert status.started_process is True
    assert status.ready is True
    assert status.pid == 4040


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
    monkeypatch.setattr(cli, "_port_available_for_dev_server", lambda port: True)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert spawned == ["http://localhost:3000"]
    assert status.reused_existing is False
    assert status.started_process is True
    assert status.ready is True


def test_ensure_hypergraph_ui_running_writes_process_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeProcess:
        pid = 5151

        def poll(self):
            return None

    def fake_spawn(ui_base_url: str):
        return FakeProcess(), tmp_path / "logs" / "hypergraph-dev.log"

    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3456")

    assert status.started_process is True
    metadata = cli._read_ui_process_metadata()
    assert metadata is not None
    assert metadata["pid"] == 5151
    assert metadata["port"] == 3456
    assert metadata["ui_base_url"] == "http://localhost:3456"
    assert metadata["started_by"] == "lmstxt --ui"


def test_ensure_hypergraph_ui_running_reuses_healthy_tracked_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=5252,
        ui_base_url="http://localhost:3007",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )
    probed: list[str] = []

    def fake_probe(ui_base_url: str, *args, **kwargs):
        probed.append(ui_base_url)
        return ui_base_url == "http://localhost:3007"

    monkeypatch.setattr(cli, "_probe_ui_reachable", fake_probe)
    monkeypatch.setattr(cli, "_process_exists", lambda pid: True)
    monkeypatch.setattr(cli, "_metadata_matches_lmstxt_ui_process", lambda pid: True)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should reuse tracked UI")))

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert status.reused_existing is True
    assert status.ready is True
    assert status.pid == 5252
    assert status.ui_base_url == "http://localhost:3007"
    assert status.note == "Reused tracked HyperGraph UI process (pid=5252)."
    assert probed == ["http://localhost:3000", "http://localhost:3007"]


def test_ensure_hypergraph_ui_running_stops_unreachable_tracked_process_before_starting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=5353,
        ui_base_url="http://localhost:3007",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )
    spawned: list[str] = []
    stopped: list[bool] = []

    class FakeProcess:
        pid = 5454

        def poll(self):
            return None

    monkeypatch.setattr(cli, "_probe_ui_reachable", lambda *args, **kwargs: False)
    monkeypatch.setattr(cli, "_process_exists", lambda pid: True)
    monkeypatch.setattr(cli, "_metadata_matches_lmstxt_ui_process", lambda pid: True)
    monkeypatch.setattr(cli, "_port_available_for_dev_server", lambda port: True)

    def fake_stop(timeout_seconds: float = 5.0):
        stopped.append(True)
        cli._remove_ui_process_metadata()
        return cli.UIStopStatus(stopped=True, pid=5353)

    def fake_spawn(ui_base_url: str):
        spawned.append(ui_base_url)
        return FakeProcess(), tmp_path / "logs" / "hypergraph-dev-new.log"

    monkeypatch.setattr(cli, "stop_tracked_hypergraph_ui", fake_stop)
    monkeypatch.setattr(cli, "_spawn_hypergraph_dev_server", fake_spawn)
    monkeypatch.setattr(cli, "_wait_for_ui_ready", lambda *args, **kwargs: True)

    status = cli.ensure_hypergraph_ui_running("http://localhost:3000")

    assert stopped == [True]
    assert spawned == ["http://localhost:3000"]
    assert status.started_process is True
    assert status.ready is True
    assert status.pid == 5454


def test_stop_tracked_hypergraph_ui_stops_recorded_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=6161,
        ui_base_url="http://localhost:3000",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )
    exists = iter([True, False])
    killed: list[tuple[int, int]] = []

    monkeypatch.setattr(cli, "_process_exists", lambda pid: next(exists, False))
    monkeypatch.setattr(cli, "_metadata_matches_lmstxt_ui_process", lambda pid: True)
    monkeypatch.setattr(cli.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    status = cli.stop_tracked_hypergraph_ui(timeout_seconds=0.1)

    assert status.stopped is True
    assert status.pid == 6161
    assert killed == [(6161, cli.signal.SIGTERM)]
    assert cli._read_ui_process_metadata() is None


def test_stop_tracked_hypergraph_ui_removes_stale_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=7171,
        ui_base_url="http://localhost:3000",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )
    monkeypatch.setattr(cli, "_process_exists", lambda pid: False)

    status = cli.stop_tracked_hypergraph_ui()

    assert status.stopped is False
    assert status.stale_metadata_removed is True
    assert "not running" in (status.error or "")
    assert cli._read_ui_process_metadata() is None


def test_stop_tracked_hypergraph_ui_refuses_unmatched_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_default_ui_log_dir", lambda: tmp_path / "logs")
    cli._write_ui_process_metadata(
        pid=8181,
        ui_base_url="http://localhost:3000",
        log_path=tmp_path / "logs" / "hypergraph-dev.log",
    )
    monkeypatch.setattr(cli, "_process_exists", lambda pid: True)
    monkeypatch.setattr(cli, "_metadata_matches_lmstxt_ui_process", lambda pid: False)

    status = cli.stop_tracked_hypergraph_ui()

    assert status.stopped is False
    assert "Refusing to stop" in (status.error or "")
    assert cli._read_ui_process_metadata() is not None


def test_main_ui_stop_uses_tracked_process(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        cli,
        "stop_tracked_hypergraph_ui",
        lambda: cli.UIStopStatus(stopped=True, pid=9292, metadata_path="/tmp/hypergraph-dev.json"),
    )

    rc = cli.main(["--ui-stop"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "HyperGraph UI stop:" in out
    assert "stopped tracked background process (pid=9292)" in out
    assert "metadata: /tmp/hypergraph-dev.json" in out


def test_main_ui_stop_rejects_repo_argument() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["https://github.com/acme/repo", "--ui-stop"])
    assert excinfo.value.code == 2
