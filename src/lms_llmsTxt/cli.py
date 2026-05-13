import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlencode
from urllib.request import Request, urlopen

from .config import AppConfig
from .graph_builder import build_repo_graph_from_llms_markdown, emit_graph_files
from .pipeline import run_generation


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_hypergraph_dir() -> Path:
    return _project_root() / "hypergraph"


def _default_ui_log_dir() -> Path:
    return _project_root() / "artifacts" / ".ui-logs"


@dataclass(slots=True)
class UIRuntimeStatus:
    reused_existing: bool = False
    started_process: bool = False
    ready: bool = False
    pid: int | None = None
    log_path: str | None = None
    ui_base_url: str | None = None
    note: str | None = None
    error: str | None = None


@dataclass(slots=True)
class UIStopStatus:
    stopped: bool = False
    stale_metadata_removed: bool = False
    pid: int | None = None
    metadata_path: str | None = None
    error: str | None = None


def build_graph_viewer_url(
    graph_json_path: str | Path,
    *,
    ui_base_url: str = "http://localhost:3000",
    hypergraph_dir: Path | None = None,
) -> str:
    graph_path = Path(graph_json_path).resolve()
    viewer_root = (hypergraph_dir or _default_hypergraph_dir()).resolve()
    graph_path_arg = str(graph_path)

    try:
        graph_path_arg = str(graph_path.relative_to(viewer_root))
    except ValueError:
        # Prefer relative path from the visualizer working directory when possible.
        try:
            graph_path_arg = str(graph_path.relative_to(viewer_root.parent))
            graph_path_arg = str(Path("..") / graph_path_arg)
        except ValueError:
            graph_path_arg = str(graph_path)

    base = ui_base_url.rstrip("/")
    query = urlencode(
        {
            "mode": "load-repo-graph",
            "graphPath": graph_path_arg,
            "autoLoad": "1",
        }
    )
    return f"{base}/?{query}"


def _probe_ui_reachable(ui_base_url: str, timeout_seconds: float = 1.0) -> bool:
    """Return True only when the requested URL appears to serve HyperGraph."""
    base = ui_base_url.rstrip("/") + "/"
    health_url = urljoin(base, "api/health")
    try:
        request = Request(health_url, method="GET")
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            if '"app":"hypergraph"' in body.replace(" ", ""):
                return True
    except (HTTPError, URLError):
        pass
    except Exception:
        pass

    try:
        request = Request(ui_base_url, method="GET")
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return "HyperGraph" in body or "Hyperbrowser" in body
    except (HTTPError, URLError):
        return False
    except Exception:
        return False


def _ui_host_port(ui_base_url: str) -> tuple[str, int]:
    parsed = urlparse(ui_base_url)
    host = parsed.hostname or "localhost"
    if parsed.port:
        return host, parsed.port
    return host, 443 if parsed.scheme == "https" else 80


def _ui_base_url_with_port(ui_base_url: str, port: int) -> str:
    parsed = urlparse(ui_base_url)
    netloc = parsed.hostname or "localhost"
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if parsed.username or parsed.password:
        auth = ""
        if parsed.username:
            auth += parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        netloc = f"{auth}@{netloc}"
    netloc = f"{netloc}:{port}"
    return parsed._replace(netloc=netloc).geturl().rstrip("/")


def _port_available_for_dev_server(port: int) -> bool:
    families = [socket.AF_INET]
    if socket.has_ipv6:
        families.append(socket.AF_INET6)

    for family in families:
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.bind(("::" if family == socket.AF_INET6 else "0.0.0.0", port))
        except OSError:
            return False
        finally:
            sock.close()
    return True


def _select_ui_base_url_for_start(ui_base_url: str, *, max_extra_ports: int = 20) -> tuple[str, str | None]:
    _host, requested_port = _ui_host_port(ui_base_url)
    if _port_available_for_dev_server(requested_port):
        return ui_base_url.rstrip("/"), None

    for port in range(requested_port + 1, requested_port + max(1, max_extra_ports) + 1):
        if _port_available_for_dev_server(port):
            selected_url = _ui_base_url_with_port(ui_base_url, port)
            return selected_url, (
                f"Requested UI port {requested_port} was already in use; started HyperGraph on port {port} instead."
            )

    return ui_base_url.rstrip("/"), (
        f"Requested UI port {requested_port} is already in use and no free port was found in "
        f"{requested_port + 1}-{requested_port + max(1, max_extra_ports)}."
    )


def _ui_dev_log_path() -> Path:
    log_dir = _default_ui_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "hypergraph-dev.log"
    if path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = log_dir / f"hypergraph-dev-{stamp}.log"
    return path


def _ui_process_metadata_path() -> Path:
    log_dir = _default_ui_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "hypergraph-dev.json"


def _write_ui_process_metadata(
    *,
    pid: int,
    ui_base_url: str,
    log_path: Path,
) -> Path:
    path = _ui_process_metadata_path()
    _host, port = _ui_host_port(ui_base_url)
    data = {
        "pid": pid,
        "ui_base_url": ui_base_url.rstrip("/"),
        "port": port,
        "log_path": str(log_path),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "started_by": "lmstxt --ui",
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_ui_process_metadata() -> dict[str, object] | None:
    path = _ui_process_metadata_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _remove_ui_process_metadata() -> None:
    _ui_process_metadata_path().unlink(missing_ok=True)


def _tracked_ui_base_url_from_metadata(data: dict[str, object] | None) -> str | None:
    if not data:
        return None
    raw = data.get("ui_base_url")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().rstrip("/")
    port = data.get("port")
    try:
        return f"http://localhost:{int(port)}" if port else None
    except Exception:
        return None


def _tracked_ui_pid_from_metadata(data: dict[str, object] | None) -> int | None:
    if not data:
        return None
    try:
        pid = int(data.get("pid", 0))
    except Exception:
        return None
    return pid if pid > 0 else None


def _reuse_tracked_hypergraph_ui() -> UIRuntimeStatus | None:
    data = _read_ui_process_metadata()
    tracked_url = _tracked_ui_base_url_from_metadata(data)
    tracked_pid = _tracked_ui_pid_from_metadata(data)
    if not tracked_url or not tracked_pid:
        return None

    if not _process_exists(tracked_pid):
        _remove_ui_process_metadata()
        return None

    if not _metadata_matches_lmstxt_ui_process(tracked_pid):
        return None

    if _probe_ui_reachable(tracked_url, timeout_seconds=1.0):
        return UIRuntimeStatus(
            reused_existing=True,
            ready=True,
            pid=tracked_pid,
            ui_base_url=tracked_url,
            note=f"Reused tracked HyperGraph UI process (pid={tracked_pid}).",
        )

    stop_status = stop_tracked_hypergraph_ui(timeout_seconds=5.0)
    if stop_status.stopped or stop_status.stale_metadata_removed:
        return None

    return UIRuntimeStatus(
        pid=tracked_pid,
        ui_base_url=tracked_url,
        error=(
            "Tracked HyperGraph UI process was not reachable and could not be cleaned up: "
            f"{stop_status.error or 'unknown cleanup failure'}"
        ),
    )


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _process_cmdline(pid: int) -> str | None:
    proc_cmdline = Path("/proc") / str(pid) / "cmdline"
    if not proc_cmdline.exists():
        return None
    try:
        return proc_cmdline.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace")
    except Exception:
        return None


def _metadata_matches_lmstxt_ui_process(pid: int) -> bool:
    cmdline = _process_cmdline(pid)
    if cmdline is None:
        # Non-/proc platforms cannot cheaply validate command ownership here.
        # Trust only the metadata file written by this CLI on those platforms.
        return True
    lowered = cmdline.lower()
    return "npm" in lowered and "ui:dev" in lowered


def stop_tracked_hypergraph_ui(timeout_seconds: float = 5.0) -> UIStopStatus:
    metadata_path = _ui_process_metadata_path()
    data = _read_ui_process_metadata()
    status = UIStopStatus(metadata_path=str(metadata_path))
    if not data:
        status.error = f"No tracked HyperGraph UI process metadata found at {metadata_path}."
        return status

    try:
        pid = int(data.get("pid", 0))
    except Exception:
        pid = 0
    status.pid = pid or None
    if not pid or not _process_exists(pid):
        try:
            metadata_path.unlink(missing_ok=True)
            status.stale_metadata_removed = True
        except Exception as exc:
            status.error = f"Tracked UI process is not running, but stale metadata could not be removed: {exc}"
            return status
        status.error = "Tracked HyperGraph UI process is not running; removed stale metadata."
        return status

    if not _metadata_matches_lmstxt_ui_process(pid):
        status.error = (
            f"Refusing to stop pid {pid}; it does not look like the `npm run ui:dev` process "
            "started by lmstxt. Stop it manually if needed."
        )
        return status

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(pid, signal.SIGTERM)
            deadline = time.monotonic() + max(0.1, timeout_seconds)
            while time.monotonic() < deadline:
                if not _process_exists(pid):
                    break
                time.sleep(0.1)
            if _process_exists(pid):
                os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except Exception as exc:
        status.error = f"Failed to stop tracked HyperGraph UI process {pid}: {exc}"
        return status

    try:
        metadata_path.unlink(missing_ok=True)
    except Exception as exc:
        status.error = f"Stopped HyperGraph UI process {pid}, but could not remove metadata: {exc}"
        status.stopped = True
        return status

    status.stopped = True
    return status


def _spawn_hypergraph_dev_server(ui_base_url: str) -> tuple[subprocess.Popen[bytes], Path]:
    repo_root = _project_root()
    _host, port = _ui_host_port(ui_base_url)
    log_path = _ui_dev_log_path()
    log_handle = log_path.open("ab")
    kwargs: dict[str, object] = {
        "cwd": str(repo_root),
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
        "env": {**os.environ, "PORT": str(port)},
    }
    if os.name == "nt":
        flags = 0
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        if flags:
            kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(["npm", "run", "ui:dev"], **kwargs)
    finally:
        # Child inherits the descriptor; parent can close its copy.
        log_handle.close()
    return proc, log_path


def _wait_for_ui_ready(
    ui_base_url: str,
    *,
    timeout_seconds: int,
    poll_interval_seconds: float = 0.5,
) -> bool:
    deadline = time.monotonic() + max(1, timeout_seconds)
    while time.monotonic() < deadline:
        if _probe_ui_reachable(ui_base_url, timeout_seconds=1.0):
            return True
        time.sleep(poll_interval_seconds)
    return False


def ensure_hypergraph_ui_running(
    ui_base_url: str,
    *,
    startup_timeout_seconds: int = 45,
) -> UIRuntimeStatus:
    requested_base_url = ui_base_url.rstrip("/")
    if _probe_ui_reachable(requested_base_url, timeout_seconds=1.0):
        return UIRuntimeStatus(reused_existing=True, ready=True, ui_base_url=requested_base_url)

    tracked_status = _reuse_tracked_hypergraph_ui()
    if tracked_status is not None:
        return tracked_status

    start_base_url, port_note = _select_ui_base_url_for_start(requested_base_url)
    status = UIRuntimeStatus(ui_base_url=start_base_url, note=port_note)
    if port_note and start_base_url == requested_base_url:
        status.error = port_note
        return status

    try:
        proc, log_path = _spawn_hypergraph_dev_server(start_base_url)
        status.started_process = True
        status.pid = proc.pid
        status.log_path = str(log_path)
        _write_ui_process_metadata(pid=proc.pid, ui_base_url=start_base_url, log_path=log_path)
    except FileNotFoundError as exc:
        status.error = (
            f"Failed to start HyperGraph UI ({exc}). Ensure Node.js/npm is installed, "
            "or start the UI manually with `npm run ui:dev`."
        )
        return status
    except Exception as exc:  # pragma: no cover - defensive
        status.error = f"Failed to start HyperGraph UI: {exc}"
        return status

    ready = _wait_for_ui_ready(start_base_url, timeout_seconds=startup_timeout_seconds)
    status.ready = ready
    if ready:
        return status

    exit_code = None
    try:
        exit_code = proc.poll()
    except Exception:
        exit_code = None
    if exit_code is not None:
        status.error = (
            f"HyperGraph UI process exited before becoming ready (exit={exit_code}). "
            f"See log: {status.log_path}"
        )
    else:
        host, port = _ui_host_port(start_base_url)
        status.error = (
            "Timed out waiting for HyperGraph UI to start "
            f"at {host}:{port} after {startup_timeout_seconds}s. "
            f"See log: {status.log_path}"
        )
    return status


def open_graph_viewer_in_browser(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def _emit_graph_from_llms_file(source_path: Path, output_root: Path | None = None) -> dict[str, str]:
    if not source_path.exists():
        raise FileNotFoundError(f"llms artifact not found: {source_path}")
    markdown = source_path.read_text(encoding="utf-8")
    graph = build_repo_graph_from_llms_markdown(markdown, topic=source_path.stem)
    target_dir = (output_root or source_path.parent) / f"{source_path.stem}.graph"
    return emit_graph_files(graph, target_dir)


def _print_graph_from_llms_summary(paths: list[Path], output_dir: Path | None = None) -> str:
    lines = ["Graph artifacts generated from llms markdown:"]
    for source_path in paths:
        graph_paths = _emit_graph_from_llms_file(source_path, output_dir)
        lines.append(f"  - source: {source_path}")
        lines.append(f"    graph: {graph_paths['graph_json']}")
        lines.append(f"    force: {graph_paths['force_json']}")
        lines.append(f"    nodes: {graph_paths['nodes_dir']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lmstxt",
        description="Generate llms.txt artifacts for a GitHub repository using LM Studio.",
    )
    parser.add_argument(
        "repo",
        nargs="?",
        help="GitHub repository URL (https://github.com/<owner>/<repo>). Optional when using --ui alone.",
    )
    parser.add_argument(
        "--model",
        help="LM Studio model identifier (overrides LMSTUDIO_MODEL).",
    )
    parser.add_argument(
        "--api-base",
        help="LM Studio API base URL (overrides LMSTUDIO_BASE_URL).",
    )
    parser.add_argument(
        "--api-key",
        help="LM Studio API key (overrides LMSTUDIO_API_KEY).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where artifacts will be written (default: OUTPUT_DIR or ./artifacts).",
    )
    parser.add_argument(
        "--link-style",
        choices=["blob", "raw"],
        help="Style of GitHub file links to generate (default: blob).",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Append a UTC timestamp comment to generated files.",
    )
    parser.add_argument(
        "--no-ctx",
        action="store_true",
        help="Skip generating llms-ctx.txt even if ENABLE_CTX is set.",
    )
    parser.add_argument(
        "--cache-lm",
        action="store_true",
        help="Enable DSPy's LM cache (useful for repeated experiments).",
    )
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        help="Maximum context tokens budget for prompt construction.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Reserved output token budget.",
    )
    parser.add_argument(
        "--context-headroom",
        type=float,
        help="Headroom ratio reserved from context window (e.g. 0.15).",
    )
    parser.add_argument(
        "-g",
        "--generate-graph",
        action="store_true",
        help="Generate repository graph artifacts (repo.graph.json, repo.force.json, nodes/*.md).",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="Skip llms-full generation and only produce llms.txt (+ optional graph artifacts).",
    )
    parser.add_argument(
        "--lm-unload-timeout-seconds",
        type=int,
        help="Maximum seconds to wait for LM Studio model unload before letting the CLI exit.",
    )
    parser.add_argument(
        "--lm-ttl-seconds",
        "--lm-idle-ttl-seconds",
        dest="lm_ttl_seconds",
        type=int,
        help="Idle TTL in seconds to request when loading/calling LM Studio models (default: 3600).",
    )
    parser.add_argument(
        "--lm-context-length",
        type=int,
        help="Context length to request when loading the LM Studio model (defaults to --max-context-tokens).",
    )
    parser.add_argument(
        "--enable-session-memory",
        action="store_true",
        help="Record append-only generation events for LCM-style session memory.",
    )
    parser.add_argument(
        "--verbose-budget",
        action="store_true",
        help="Log context budget and retry reductions.",
    )
    parser.add_argument(
        "--graph-from",
        action="append",
        type=Path,
        default=[],
        metavar="LLMS_MARKDOWN",
        help="Generate graph artifacts from an existing llms.txt or llms-full.txt file. Repeat for multiple files.",
    )
    parser.add_argument(
        "--ui",
        nargs="?",
        const=True,
        default=False,
        metavar="GRAPH_JSON",
        help="Launch/open HyperGraph. Optionally pass a repo.graph.json path to open it directly.",
    )
    parser.add_argument(
        "--ui-base-url",
        default="http://localhost:3000",
        help="Base URL for the HyperGraph UI used by --ui (default: http://localhost:3000).",
    )
    parser.add_argument(
        "--ui-no-open",
        action="store_true",
        help="Do not auto-open the browser when using --ui (still starts/reuses the UI server).",
    )
    parser.add_argument(
        "--ui-stop",
        action="store_true",
        help="Stop the HyperGraph UI process previously started by lmstxt --ui.",
    )
    parser.add_argument(
        "--ui-start-timeout-seconds",
        type=int,
        default=45,
        help="Seconds to wait for the HyperGraph UI to become reachable when auto-starting (default: 45).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    config = AppConfig()
    if args.model:
        config.lm_model = args.model
    if args.api_base:
        config.lm_api_base = str(args.api_base)
    if args.api_key:
        config.lm_api_key = args.api_key
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.link_style:
        config.link_style = args.link_style
    if args.no_ctx:
        config.enable_ctx = False
    if args.max_context_tokens is not None:
        config.max_context_tokens = args.max_context_tokens
    if args.max_output_tokens is not None:
        config.max_output_tokens = args.max_output_tokens
    if args.context_headroom is not None:
        config.context_headroom_ratio = args.context_headroom
    if args.generate_graph:
        config.enable_repo_graph = True
    if args.lm_unload_timeout_seconds is not None:
        if args.lm_unload_timeout_seconds < 0:
            parser.error("--lm-unload-timeout-seconds must be >= 0.")
        config.lm_unload_timeout_seconds = args.lm_unload_timeout_seconds
    if args.lm_ttl_seconds is not None:
        if args.lm_ttl_seconds < 0:
            parser.error("--lm-ttl-seconds must be >= 0.")
        config.lm_ttl_seconds = args.lm_ttl_seconds
    if args.lm_context_length is not None:
        if args.lm_context_length <= 0:
            parser.error("--lm-context-length must be > 0.")
        config.lm_context_length = args.lm_context_length
    if args.enable_session_memory:
        config.enable_session_memory = True
    if args.ui_start_timeout_seconds is not None and int(args.ui_start_timeout_seconds) <= 0:
        parser.error("--ui-start-timeout-seconds must be > 0.")
    ui_graph_path = Path(args.ui) if isinstance(args.ui, str) else None
    if args.graph_from and args.repo:
        parser.error("--graph-from generates graphs from files and does not take a repository argument.")
    if args.graph_from and ui_graph_path:
        parser.error("Use --graph-from to generate graph artifacts or --ui GRAPH_JSON to open an existing graph, not both at once.")
    if args.ui_stop:
        if args.repo:
            parser.error("--ui-stop does not take a repository argument.")
        stop_status = stop_tracked_hypergraph_ui()
        summary = "HyperGraph UI stop:"
        if stop_status.stopped:
            summary += f"\n  - stopped tracked background process (pid={stop_status.pid})"
        elif stop_status.stale_metadata_removed:
            summary += "\n  - no running tracked process"
            summary += "\n  - removed stale metadata"
        elif stop_status.error:
            summary += f"\n  - {stop_status.error}"
        if stop_status.metadata_path:
            summary += f"\n  - metadata: {stop_status.metadata_path}"
        print(summary)
        return 0 if stop_status.stopped or stop_status.stale_metadata_removed else 1
    if args.graph_from:
        try:
            print(_print_graph_from_llms_summary(args.graph_from, config.output_dir if args.output_dir else None))
        except Exception as exc:
            parser.error(str(exc))
            return 2
        return 0
    if ui_graph_path is not None:
        if args.repo:
            parser.error("--ui GRAPH_JSON does not take a repository argument.")
        if not ui_graph_path.exists():
            parser.error(f"Graph JSON file not found: {ui_graph_path}")
        ui_status = ensure_hypergraph_ui_running(
            args.ui_base_url,
            startup_timeout_seconds=int(args.ui_start_timeout_seconds),
        )
        effective_ui_base_url = (ui_status.ui_base_url or args.ui_base_url).rstrip("/")
        viewer_url = build_graph_viewer_url(ui_graph_path, ui_base_url=effective_ui_base_url)
        summary = "Graph viewer:"
        summary += f"\n  - {viewer_url}"
        if ui_status.reused_existing:
            summary += "\nUI status:\n  - already running"
        elif ui_status.started_process:
            summary += "\nUI status:"
            if ui_status.note:
                summary += f"\n  - {ui_status.note}"
            summary += f"\n  - started background dev server (pid={ui_status.pid})"
            if ui_status.log_path:
                summary += f"\n  - log: {ui_status.log_path}"
            summary += "\n  - ready" if ui_status.ready else "\n  - not ready"
        elif ui_status.error:
            summary += f"\nUI status:\n  - error: {ui_status.error}"
        if not args.ui_no_open:
            if ui_status.ready:
                opened = open_graph_viewer_in_browser(viewer_url)
                summary += "\nBrowser:"
                summary += "\n  - opened" if opened else "\n  - failed to open automatically (open the URL manually)"
            else:
                summary += "\nBrowser:\n  - not opened (UI was not ready)"
        print(summary)
        return 0
    if not args.repo:
        if not args.ui:
            parser.error("repo is required unless --ui is used to launch HyperGraph.")
        ui_status = ensure_hypergraph_ui_running(
            args.ui_base_url,
            startup_timeout_seconds=int(args.ui_start_timeout_seconds),
        )
        effective_ui_base_url = (ui_status.ui_base_url or args.ui_base_url).rstrip("/")
        summary = "HyperGraph UI:"
        summary += f"\n  - {effective_ui_base_url}"
        if ui_status.reused_existing:
            summary += "\nUI status:"
            if ui_status.note:
                summary += f"\n  - {ui_status.note}"
            summary += "\n  - already running"
        elif ui_status.started_process:
            summary += "\nUI status:"
            if ui_status.note:
                summary += f"\n  - {ui_status.note}"
            summary += f"\n  - started background dev server (pid={ui_status.pid})"
            if ui_status.log_path:
                summary += f"\n  - log: {ui_status.log_path}"
            if ui_status.ready:
                summary += "\n  - ready"
            elif ui_status.error:
                summary += f"\n  - error: {ui_status.error}"
        elif ui_status.error:
            summary += "\nUI status:"
            summary += f"\n  - error: {ui_status.error}"

        if not args.ui_no_open:
            if ui_status.ready:
                opened = open_graph_viewer_in_browser(effective_ui_base_url)
                summary += "\nBrowser:"
                summary += "\n  - opened" if opened else "\n  - failed to open automatically (open the URL manually)"
            else:
                summary += "\nBrowser:"
                summary += "\n  - not opened (UI was not ready)"
        print(summary)
        return 0
    if args.ui and not args.generate_graph:
        parser.error("--ui with a repo requires --generate-graph so repo.graph.json is produced. Use `lmstxt --ui` to launch HyperGraph without generating artifacts.")

    try:
        artifacts = run_generation(
            repo_url=args.repo,
            config=config,
            stamp=bool(args.stamp),
            cache_lm=bool(args.cache_lm),
            generate_graph=bool(args.generate_graph),
            graph_only=bool(args.graph_only),
            verbose_budget=bool(args.verbose_budget),
            enable_session_memory=bool(args.enable_session_memory),
        )
    except Exception as exc:
        parser.error(str(exc))
        return 2

    summary = dedent(
        f"""\
        Artifacts written:
          - {artifacts.llms_txt_path}
          - {artifacts.llms_full_path}
        """
    ).rstrip()

    if artifacts.ctx_path:
        summary += f"\n  - {artifacts.ctx_path}"
    if artifacts.json_path:
        summary += f"\n  - {artifacts.json_path}"
    if artifacts.graph_json_path:
        summary += f"\n  - {artifacts.graph_json_path}"
    if artifacts.force_graph_path:
        summary += f"\n  - {artifacts.force_graph_path}"
    if artifacts.graph_nodes_dir:
        summary += f"\n  - {artifacts.graph_nodes_dir}"
    if artifacts.trace_path:
        summary += f"\n  - {artifacts.trace_path}"
    if artifacts.run_log_path:
        summary += f"\n  - {artifacts.run_log_path}"
    if artifacts.run_events_path:
        summary += f"\n  - {artifacts.run_events_path}"
    if artifacts.used_fallback:
        summary += "\n(note) LM call failed; fallback JSON/schema output was used."
        if artifacts.fallback_reason:
            summary += f"\n(reason) {artifacts.fallback_reason}"
    if args.ui:
        if not artifacts.graph_json_path:
            parser.error("--ui was requested, but no repo graph artifact was generated.")
        ui_status = ensure_hypergraph_ui_running(
            args.ui_base_url,
            startup_timeout_seconds=int(args.ui_start_timeout_seconds),
        )
        effective_ui_base_url = (ui_status.ui_base_url or args.ui_base_url).rstrip("/")
        viewer_url = build_graph_viewer_url(artifacts.graph_json_path, ui_base_url=effective_ui_base_url)

        summary += "\nGraph viewer:"
        summary += f"\n  - {viewer_url}"
        if ui_status.reused_existing:
            summary += "\nUI status:"
            if ui_status.note:
                summary += f"\n  - {ui_status.note}"
            summary += "\n  - already running"
        elif ui_status.started_process:
            summary += "\nUI status:"
            if ui_status.note:
                summary += f"\n  - {ui_status.note}"
            summary += f"\n  - started background dev server (pid={ui_status.pid})"
            if ui_status.log_path:
                summary += f"\n  - log: {ui_status.log_path}"
            if ui_status.ready:
                summary += "\n  - ready"
            elif ui_status.error:
                summary += f"\n  - error: {ui_status.error}"
        elif ui_status.error:
            summary += "\nUI status:"
            summary += f"\n  - error: {ui_status.error}"

        if not args.ui_no_open:
            if ui_status.ready:
                opened = open_graph_viewer_in_browser(viewer_url)
                summary += "\nBrowser:"
                summary += "\n  - opened" if opened else "\n  - failed to open automatically (open the URL manually)"
            else:
                summary += "\nBrowser:"
                summary += "\n  - not opened (UI was not ready)"

    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
