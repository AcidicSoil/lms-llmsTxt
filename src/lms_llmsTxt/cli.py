import argparse
import logging
import os
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen

from .config import AppConfig
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
    request = Request(ui_base_url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds):
            return True
    except HTTPError:
        # A real HTTP response proves the server is reachable.
        return True
    except URLError:
        return False
    except Exception:
        return False


def _ui_host_port(ui_base_url: str) -> tuple[str, int]:
    parsed = urlparse(ui_base_url)
    host = parsed.hostname or "localhost"
    if parsed.port:
        return host, parsed.port
    return host, 443 if parsed.scheme == "https" else 80


def _ui_dev_log_path() -> Path:
    log_dir = _default_ui_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "hypergraph-dev.log"
    if path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = log_dir / f"hypergraph-dev-{stamp}.log"
    return path


def _spawn_hypergraph_dev_server() -> tuple[subprocess.Popen[bytes], Path]:
    repo_root = _project_root()
    log_path = _ui_dev_log_path()
    log_handle = log_path.open("ab")
    kwargs: dict[str, object] = {
        "cwd": str(repo_root),
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
        "env": dict(os.environ),
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
    if _probe_ui_reachable(ui_base_url, timeout_seconds=1.0):
        return UIRuntimeStatus(reused_existing=True, ready=True)

    status = UIRuntimeStatus()
    try:
        proc, log_path = _spawn_hypergraph_dev_server()
        status.started_process = True
        status.pid = proc.pid
        status.log_path = str(log_path)
    except FileNotFoundError as exc:
        status.error = (
            f"Failed to start HyperGraph UI ({exc}). Ensure Node.js/npm is installed, "
            "or start the UI manually with `npm run ui:dev`."
        )
        return status
    except Exception as exc:  # pragma: no cover - defensive
        status.error = f"Failed to start HyperGraph UI: {exc}"
        return status

    ready = _wait_for_ui_ready(ui_base_url, timeout_seconds=startup_timeout_seconds)
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
        host, port = _ui_host_port(ui_base_url)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lmstxt",
        description="Generate llms.txt artifacts for a GitHub repository using LM Studio.",
    )
    parser.add_argument("repo", help="GitHub repository URL (https://github.com/<owner>/<repo>)")
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
        "--ui",
        action="store_true",
        help="Print a HyperGraph visualizer URL for the generated repo graph artifact.",
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
    if args.enable_session_memory:
        config.enable_session_memory = True
    if args.ui and not args.generate_graph:
        parser.error("--ui requires --generate-graph so repo.graph.json is produced.")
    if args.ui_start_timeout_seconds is not None and int(args.ui_start_timeout_seconds) <= 0:
        parser.error("--ui-start-timeout-seconds must be > 0.")

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
    if artifacts.used_fallback:
        summary += "\n(note) LM call failed; fallback JSON/schema output was used."
    if args.ui:
        if not artifacts.graph_json_path:
            parser.error("--ui was requested, but no repo graph artifact was generated.")
        viewer_url = build_graph_viewer_url(artifacts.graph_json_path, ui_base_url=args.ui_base_url)
        ui_status = ensure_hypergraph_ui_running(
            args.ui_base_url,
            startup_timeout_seconds=int(args.ui_start_timeout_seconds),
        )

        summary += "\nGraph viewer:"
        summary += f"\n  - {viewer_url}"
        if ui_status.reused_existing:
            summary += "\nUI status:"
            summary += "\n  - already running"
        elif ui_status.started_process:
            summary += "\nUI status:"
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
