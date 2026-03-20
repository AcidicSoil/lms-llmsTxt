<source_code>
src/lms_llmsTxt/__init__.py
```
"""LM Studio-powered llms.txt generation toolkit."""

import importlib.metadata

from .analyzer import RepositoryAnalyzer
from .config import AppConfig
from .fallback import (
    fallback_llms_payload,
    fallback_llms_markdown,
)
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError
from .models import GenerationArtifacts, RepositoryMaterial
from .schema import LLMS_JSON_SCHEMA

try:
    __version__ = importlib.metadata.version("lmstudio-lmstxt-generator")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "AppConfig",
    "GenerationArtifacts",
    "RepositoryAnalyzer",
    "RepositoryMaterial",
    "configure_lmstudio_lm",
    "LMStudioConnectivityError",
    "fallback_llms_payload",
    "fallback_llms_markdown",
    "LLMS_JSON_SCHEMA",
    "__version__",
]
```

src/lms_llmsTxt/analyzer.py
```
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

import requests

from .github import construct_github_file_url, fetch_file_content, owner_repo_from_url
try:
    import dspy
except ImportError:
    from .signatures import dspy

from .signatures import (
    AnalyzeCodeStructure,
    AnalyzeRepositoryFromDigest,
    AnalyzeRepository,
    GenerateLLMsTxt,
    GenerateUsageExamples,
)
from .repo_digest import RepoDigest

logger = logging.getLogger(__name__)

_URL_VALIDATION_TIMEOUT = 5
_URL_SESSION = requests.Session()
_URL_HEADERS = {"User-Agent": "lms-lmstxt"}


def _nicify_title(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    base = re.sub(r"\.(md|rst|txt|py|ipynb|js|ts|html|mdx)$", "", base, flags=re.I)
    base = base.replace("-", " ").replace("_", " ")
    title = base.strip().title() or path
    if re.search(r"(^|/)index(\.mdx?|\.html?)?$", path, flags=re.I):
        parts = path.strip("/").split("/")
        if len(parts) > 1:
            title = parts[-2].replace("-", " ").replace("_", " ").title()
    return title


def _short_note(path: str) -> str:
    lower = path.lower()
    if any(
        hint in lower
        for hint in ["getting-started", "quickstart", "install", "overview", "/readme"]
    ):
        return "install & quickstart"
    if any(hint in lower for hint in ["reference", "/api"]):
        return "API reference"
    if any(hint in lower for hint in ["tutorial", "example", "how-to", "demo"]):
        return "worked example"
    if any(hint in lower for hint in ["concept", "architecture", "faq"]):
        return "core concept"
    if "changelog" in lower or "release" in lower:
        return "version history"
    if "license" in lower:
        return "usage terms"
    if "security" in lower:
        return "security policy"
    return "docs page"


def _score(path: str) -> float:
    score = 0.0
    lower = path.lower()
    if any(
        hint in lower
        for hint in ["quickstart", "getting-started", "install", "overview", "/readme"]
    ):
        score += 5
    if any(hint in lower for hint in ["tutorial", "example", "how-to", "demo"]):
        score += 3
    if re.search(r"(^|/)index(\.mdx?|\.html?)?$", lower):
        score += 2
    score -= lower.count("/") * 0.1
    return score


TAXONOMY: List[Tuple[str, re.Pattern]] = [
    (
        "Docs",
        re.compile(r"(docs|guide|getting[-_ ]?started|quickstart|install|overview)", re.I),
    ),
    ("Tutorials", re.compile(r"(tutorial|example|how[-_ ]?to|cookbook|demos?)", re.I)),
    ("API", re.compile(r"(api|reference|sdk|class|module)", re.I)),
    ("Concepts", re.compile(r"(concept|architecture|design|faq)", re.I)),
    (
        "Optional",
        re.compile(r"(contributing|changelog|release|security|license|benchmark)", re.I),
    ),
]


def _url_alive(url: str) -> bool:
    try:
        response = _URL_SESSION.head(
            url, allow_redirects=True, timeout=_URL_VALIDATION_TIMEOUT, headers=_URL_HEADERS
        )
        status = response.status_code
        if status and status < 400:
            return True
        response = _URL_SESSION.get(
            url,
            stream=True,
            timeout=_URL_VALIDATION_TIMEOUT,
            headers=_URL_HEADERS,
        )
        response.close()
        return response.status_code < 400
    except requests.RequestException:
        return False


def _github_path_exists(
    repo_url: str,
    path: str,
    ref: str | None,
    token: str | None,
) -> bool:
    try:
        owner, repo = owner_repo_from_url(repo_url)
    except Exception:
        return False
    resolved_ref = ref or "main"
    try:
        content = fetch_file_content(owner, repo, path, resolved_ref, token)
    except Exception:
        return False
    return content is not None


def build_dynamic_buckets(
    repo_url: str,
    file_tree: str,
    default_ref: str | None = None,
    validate_urls: bool = True,
    is_private: bool = False,
    github_token: str | None = None,
    link_style: str = "blob",
) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    paths = [p.strip() for p in file_tree.splitlines() if p.strip()]
    pages = []
    for path in paths:
        if not re.search(r"\.(md|mdx|py|ipynb|js|ts|rst|txt|html)$", path, flags=re.I):
            continue
        pages.append(
            {
                "path": path,
                "url": construct_github_file_url(
                    repo_url, path, ref=default_ref, style=link_style
                ),
                "title": (
                    "README"
                    if re.search(r"(^|/)README\.md$", path, flags=re.I)
                    else _nicify_title(path)
                ),
                "note": _short_note(path),
                "score": _score(path),
            }
        )

    buckets: Dict[str, List[dict]] = defaultdict(list)
    for page in pages:
        matched = False
        for name, regex in TAXONOMY:
            if regex.search(page["path"]) or regex.search(page["title"]):
                buckets[name].append(page)
                matched = True
                break
        if not matched:
            top = page["path"].strip("/").split("/")[0] or "Misc"
            buckets[top.replace("-", " ").replace("_", " ").title()].append(page)

    for name, items in list(buckets.items()):
        items.sort(key=lambda item: (-item["score"], item["title"]))
        buckets[name] = items[:10]
        if not buckets[name]:
            buckets.pop(name, None)

    if validate_urls:
        for name, items in list(buckets.items()):
            filtered = []
            for page in items:
                if is_private and github_token:
                    ok = _github_path_exists(
                        repo_url,
                        page["path"],
                        default_ref,
                        github_token,
                    )
                else:
                    ok = _url_alive(page["url"])
                if ok:
                    filtered.append(page)
                else:
                    logger.debug("Dropping %s due to missing resource.", page["url"])
            if filtered:
                buckets[name] = filtered
            else:
                buckets.pop(name, None)

    reserved = {name for name, _ in TAXONOMY}
    for name in list(buckets.keys()):
        if name not in reserved and len(buckets[name]) <= 1:
            buckets["Optional"].extend(buckets.pop(name))

    ordered: List[Tuple[str, List[Tuple[str, str, str]]]] = []
    seen = set()
    for name, _ in TAXONOMY:
        if name in buckets:
            ordered.append(
                (
                    name,
                    [(pg["title"], pg["url"], pg["note"]) for pg in buckets[name]],
                )
            )
            seen.add(name)
    for name in sorted(k for k in buckets.keys() if k not in seen):
        ordered.append((name, [(pg["title"], pg["url"], pg["note"]) for pg in buckets[name]]))
    return ordered


def render_llms_markdown(
    project_name: str,
    project_purpose: str,
    remember_bullets: Iterable[str],
    buckets: List[Tuple[str, List[Tuple[str, str, str]]]],
) -> str:
    bullets = [str(b).strip().rstrip(".") for b in remember_bullets if str(b).strip()]
    bullets = bullets[:6] or [
        "Install + Quickstart first",
        "Core concepts & API surface",
        "Use Tutorials for worked examples",
    ]
    if len(bullets) < 3:
        bullets += ["Review API reference", "See Optional for meta docs"][: 3 - len(bullets)]
    purpose_line = (project_purpose or "").strip().replace("\n", " ")

    def fmt(items: Iterable[Tuple[str, str, str]]) -> str:
        return "\n".join(f"- [{title}]({url}): {note}." for title, url, note in items)

    out = [
        f"# {project_name}",
        "",
        f"> {purpose_line or 'Project overview unavailable.'}",
        "",
        "**Remember:**",
        *[f"- {bullet}" for bullet in bullets],
        "",
    ]
    for name, items in buckets:
        if not items:
            continue
        out.append(f"## {name}")
        out.append(fmt(items) or "- _No curated links yet_.")
        out.append("")
    return "\n".join(out).strip()


def _pred_get(prediction: Any, key: str, default: Any = None) -> Any:
    if prediction is None:
        return default
    if isinstance(prediction, dict):
        return prediction.get(key, default)
    return getattr(prediction, key, default)


def _as_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_list_of_text(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            text = _as_text(item)
            if text:
                out.append(text)
        return out
    text = _as_text(value)
    return [text] if text else []


def _readme_lead_sentence(readme_content: str) -> str:
    if not readme_content:
        return ""
    text = " ".join(line.strip() for line in readme_content.splitlines() if line.strip())
    if not text:
        return ""
    sentence = text.split(".")[0].strip()
    return (sentence + ".") if sentence and not sentence.endswith(".") else sentence


class RepositoryAnalyzer(dspy.Module):
    """DSPy module that synthesizes an llms.txt summary for a GitHub repository."""

    def __init__(self, production_mode: bool = True) -> None:
        super().__init__()
        self.production_mode = production_mode
        predictor = getattr(dspy, "Predict", dspy.ChainOfThought) if production_mode else dspy.ChainOfThought
        self.analyze_repo = predictor(AnalyzeRepository)
        self.analyze_repo_digest = predictor(AnalyzeRepositoryFromDigest)
        self.analyze_structure = predictor(AnalyzeCodeStructure)
        self.generate_examples = predictor(GenerateUsageExamples)
        self.generate_llms_txt = predictor(GenerateLLMsTxt)

    def forward(
        self,
        repo_url: str | None = None,
        file_tree: str = "",
        readme_content: str = "",
        package_files: str = "",
        default_branch: str | None = None,
        is_private: bool = False,
        github_token: str | None = None,
        link_style: str = "blob",
        repo_digest: RepoDigest | None = None,
    ):
        effective_repo_url = repo_url or "https://github.com/unknown/repo"
        if repo_digest is not None:
            digest_summary = (
                f"Architecture: {repo_digest.architecture_summary}\n"
                f"Primary language: {repo_digest.primary_language}\n"
                f"Entry points: {', '.join(repo_digest.entry_points[:10])}\n"
                f"Dependencies: {', '.join(repo_digest.key_dependencies[:20])}\n"
            )
            repo_analysis = self.analyze_repo_digest(
                digest_summary=digest_summary,
                repo_url=effective_repo_url,
            )
            structure_analysis = dspy.Prediction(
                important_directories=[s.get("name", "") for s in repo_digest.subsystems[:8]],
                entry_points=repo_digest.entry_points[:10],
                development_info=repo_digest.architecture_summary,
            )
            file_tree = file_tree or "\n".join(
                path
                for sub in repo_digest.subsystems
                for path in sub.get("paths", [])[:6]
            )
        else:
            repo_analysis = self.analyze_repo(
                repo_url=effective_repo_url,
                file_tree=file_tree,
                readme_content=readme_content,
            )
            structure_analysis = self.analyze_structure(
                file_tree=file_tree, package_files=package_files
            )

        project_purpose = _as_text(_pred_get(repo_analysis, "project_purpose"))
        if not project_purpose:
            project_purpose = _as_text(
                repo_digest.architecture_summary if repo_digest else "",
                default=_readme_lead_sentence(readme_content) or "Project overview unavailable.",
            )
            logger.debug("Analyzer missing project_purpose; using fallback summary.")

        key_concepts = _as_list_of_text(_pred_get(repo_analysis, "key_concepts"))
        if not key_concepts and repo_digest is not None:
            key_concepts = [sub.get("name", "") for sub in repo_digest.subsystems[:6] if sub.get("name")]
            if not key_concepts:
                key_concepts = repo_digest.key_dependencies[:6]
            logger.debug("Analyzer missing key_concepts; using digest-derived concepts.")

        entry_points = _as_list_of_text(_pred_get(structure_analysis, "entry_points"))
        if not entry_points and repo_digest is not None:
            entry_points = repo_digest.entry_points[:10]
            logger.debug("Analyzer missing entry_points; using digest entry points.")

        important_directories = _as_list_of_text(_pred_get(structure_analysis, "important_directories"))
        if not important_directories and repo_digest is not None:
            important_directories = [sub.get("name", "") for sub in repo_digest.subsystems[:8] if sub.get("name")]

        development_info = _as_text(_pred_get(structure_analysis, "development_info"))
        if not development_info and repo_digest is not None:
            development_info = _as_text(repo_digest.architecture_summary, default="Repository architecture summary unavailable.")

        self.generate_examples(
            repo_info=(
                f"Purpose: {project_purpose}\n\n"
                f"Concepts: {', '.join(key_concepts)}\n\n"
                f"Entry points: {', '.join(entry_points)}\n"
            )
        )

        try:
            _, repo = owner_repo_from_url(effective_repo_url)
            project_name = repo.replace("-", " ").replace("_", " ").title()
        except Exception:
            project_name = "Project"

        buckets = build_dynamic_buckets(
            effective_repo_url,
            file_tree,
            default_ref=default_branch,
            validate_urls=True,
            is_private=is_private,
            github_token=github_token,
            link_style=link_style,
        )

        llms_txt_content = render_llms_markdown(
            project_name=project_name,
            project_purpose=project_purpose,
            remember_bullets=key_concepts,
            buckets=buckets,
        )

        return dspy.Prediction(
            llms_txt_content=llms_txt_content,
            analysis=dspy.Prediction(
                project_purpose=project_purpose,
                key_concepts=key_concepts,
            ),
            structure=dspy.Prediction(
                important_directories=important_directories,
                entry_points=entry_points,
                development_info=development_info,
            ),
        )
```

src/lms_llmsTxt/cli.py
```
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
    ui_base_url: str = "http://localhost:3010",
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
        default="http://localhost:3010",
        help="Base URL for the HyperGraph UI used by --ui (default: http://localhost:3010).",
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
```

src/lms_llmsTxt/config.py
```
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    """
    Runtime configuration for the LM Studio llms.txt generator.

    Users can override defaults through environment variables:
      - ``LMSTUDIO_MODEL``: LM Studio model identifier.
      - ``LMSTUDIO_BASE_URL``: API base URL (defaults to http://localhost:1234/v1).
      - ``LMSTUDIO_API_KEY``: Optional API key (LM Studio accepts any string).
      - ``OUTPUT_DIR``: Root folder for generated artifacts.
      - ``ENABLE_CTX``: Set truthy to emit llms-ctx.txt files when llms_txt.create_ctx
        is available.
    """
    lm_model: str = field(
        default_factory=lambda: os.getenv(
            "LMSTUDIO_MODEL", "qwen_qwen3-vl-4b-instruct"
        )
    )
    lm_api_base: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    )
    lm_api_key: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "artifacts"))
    )
    github_token: str | None = field(
        default_factory=lambda: os.getenv("GITHUB_ACCESS_TOKEN")
        or os.getenv("GH_TOKEN")
    )
    link_style: str = field(
        default_factory=lambda: os.getenv("LINK_STYLE", "blob")
    )
    enable_ctx: bool = field(default_factory=lambda: _env_flag("ENABLE_CTX", False))
    lm_streaming: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_STREAMING", True))
    lm_auto_unload: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_AUTO_UNLOAD", True))
    max_context_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "32768"))
    )
    max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
    )
    context_headroom_ratio: float = field(
        default_factory=lambda: float(os.getenv("CONTEXT_HEADROOM_RATIO", "0.15"))
    )
    max_file_tree_lines: int = field(
        default_factory=lambda: int(os.getenv("MAX_FILE_TREE_LINES", "1200"))
    )
    max_readme_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_README_CHARS", "24000"))
    )
    max_package_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_PACKAGE_CHARS", "18000"))
    )
    retry_reduction_steps: tuple[float, ...] = field(
        default_factory=lambda: tuple(
            float(part.strip())
            for part in os.getenv("RETRY_REDUCTION_STEPS", "0.70,0.50").split(",")
            if part.strip()
        )
    )
    enable_repo_graph: bool = field(default_factory=lambda: _env_flag("ENABLE_REPO_GRAPH", False))
    enable_session_memory: bool = field(
        default_factory=lambda: _env_flag("ENABLE_SESSION_MEMORY", False)
    )

    def ensure_output_root(self, owner: str, repo: str) -> Path:
        """Return ``<output_root>/<owner>/<repo>`` and create it if missing."""
        repo_root = self.output_dir / owner / repo
        repo_root.mkdir(parents=True, exist_ok=True)
        return repo_root
```

src/lms_llmsTxt/context_budget.py
```
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class BudgetDecision(str, Enum):
    APPROVED = "approved"
    NEEDS_COMPACTION = "needs_compaction"
    REJECTED = "rejected"


@dataclass(slots=True)
class ContextBudget:
    max_context_tokens: int
    reserved_output_tokens: int
    headroom_ratio: float
    estimated_prompt_tokens: int = 0
    available_tokens: int = 0
    decision: BudgetDecision = BudgetDecision.APPROVED
    component_estimates: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover
    tiktoken = None


def estimate_tokens(text: str) -> int:
    data = text or ""
    if not data:
        return 0
    if tiktoken is None:
        return max(1, len(data) // 4)
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(data))
    except Exception:
        return max(1, len(data) // 4)


def _truncate_chars(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def _trim_file_tree(tree: str, max_lines: int) -> str:
    if max_lines <= 0:
        return ""
    lines = tree.splitlines()
    if len(lines) <= max_lines:
        return tree
    return "\n".join(lines[:max_lines])


def build_context_budget(config: Any, material: Any) -> ContextBudget:
    max_context_tokens = int(getattr(config, "max_context_tokens", 32768))
    reserved_output_tokens = int(getattr(config, "max_output_tokens", 4096))
    headroom_ratio = float(getattr(config, "context_headroom_ratio", 0.15))

    file_tree = _trim_file_tree(
        str(getattr(material, "file_tree", "") or ""),
        int(getattr(config, "max_file_tree_lines", 1200)),
    )
    readme = _truncate_chars(
        str(getattr(material, "readme_content", "") or ""),
        int(getattr(config, "max_readme_chars", 24000)),
    )
    packages = _truncate_chars(
        str(getattr(material, "package_files", "") or ""),
        int(getattr(config, "max_package_chars", 18000)),
    )

    component_estimates = {
        "file_tree": estimate_tokens(file_tree),
        "readme_content": estimate_tokens(readme),
        "package_files": estimate_tokens(packages),
    }

    estimated = sum(component_estimates.values())
    headroom_tokens = int(max_context_tokens * headroom_ratio)
    available = max(0, max_context_tokens - reserved_output_tokens - headroom_tokens)

    budget = ContextBudget(
        max_context_tokens=max_context_tokens,
        reserved_output_tokens=reserved_output_tokens,
        headroom_ratio=headroom_ratio,
        estimated_prompt_tokens=estimated,
        available_tokens=available,
        component_estimates=component_estimates,
    )
    budget.decision = validate_budget(budget)
    return budget


def validate_budget(budget: ContextBudget) -> BudgetDecision:
    if budget.estimated_prompt_tokens <= budget.available_tokens:
        return BudgetDecision.APPROVED
    if budget.available_tokens > 0 and budget.estimated_prompt_tokens <= budget.available_tokens * 2:
        return BudgetDecision.NEEDS_COMPACTION
    return BudgetDecision.REJECTED
```

src/lms_llmsTxt/context_compaction.py
```
from __future__ import annotations

from dataclasses import replace

from .context_budget import ContextBudget
from .models import RepositoryMaterial


def _trim_file_tree(file_tree: str, max_lines: int) -> str:
    lines = file_tree.splitlines()
    if len(lines) <= max_lines:
        return file_tree
    return "\n".join(lines[:max_lines]) + "\n... (trimmed file tree)"


def _trim_text(content: str, max_chars: int, label: str) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + f"\n... (trimmed {label})"


def compact_material(material: RepositoryMaterial, budget: ContextBudget, config) -> RepositoryMaterial:
    # Deterministic compaction ladder.
    compacted = replace(material)
    compacted.file_tree = _trim_file_tree(
        compacted.file_tree,
        max(50, int(getattr(config, "max_file_tree_lines", 1200) * 0.6)),
    )
    compacted.readme_content = _trim_text(
        compacted.readme_content,
        max(1000, int(getattr(config, "max_readme_chars", 24000) * 0.5)),
        "README",
    )
    compacted.package_files = _trim_text(
        compacted.package_files,
        max(1200, int(getattr(config, "max_package_chars", 18000) * 0.5)),
        "package files",
    )

    # Final deterministic blob truncation based on budget estimate proportions.
    if budget.estimated_prompt_tokens > budget.available_tokens and budget.available_tokens > 0:
        factor = max(0.2, min(1.0, budget.available_tokens / max(1, budget.estimated_prompt_tokens)))
        compacted.readme_content = _trim_text(
            compacted.readme_content,
            max(500, int(len(compacted.readme_content) * factor)),
            "README",
        )
        compacted.package_files = _trim_text(
            compacted.package_files,
            max(500, int(len(compacted.package_files) * factor)),
            "package files",
        )
    return compacted
```

src/lms_llmsTxt/fallback.py
```
from __future__ import annotations

import textwrap
from typing import Dict, List, Tuple

from .analyzer import build_dynamic_buckets, render_llms_markdown
from .schema import LLMS_JSON_SCHEMA


def _summary_from_readme(readme: str) -> str:
    if not readme:
        return "Project overview unavailable."
    lines = [line.strip() for line in readme.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return "Project overview unavailable."
    if lines[0].startswith("#"):
        lines = lines[1:]
    excerpt = []
    for line in lines:
        if line.startswith("#"):
            break
        excerpt.append(line)
        if len(" ".join(excerpt)) > 280:
            break
    summary = " ".join(excerpt).strip()
    if not summary:
        return "Project overview unavailable."
    return summary


def _remember_bullets() -> List[str]:
    return [
        "Start with Docs for install & onboarding",
        "Check Tutorials for end-to-end workflows",
        "Review API references before integrating",
    ]


def fallback_llms_payload(
    repo_name: str,
    repo_url: str,
    file_tree: str,
    readme_content: str,
    *,
    default_branch: str | None = None,
    is_private: bool = False,
    github_token: str | None = None,
    link_style: str = "blob",
) -> Dict[str, object]:
    buckets = build_dynamic_buckets(
        repo_url,
        file_tree,
        default_ref=default_branch,
        validate_urls=True,
        is_private=is_private,
        github_token=github_token,
        link_style=link_style,
    )
    summary = _summary_from_readme(readme_content)
    remember = _remember_bullets()
    sections: List[Dict[str, object]] = []
    for title, items in buckets:
        links = [
            {"title": link_title, "url": link_url, "note": note}
            for (link_title, link_url, note) in items
        ]
        sections.append({"title": title, "links": links})
    payload: Dict[str, object] = {
        "schema": LLMS_JSON_SCHEMA,
        "project": {"name": repo_name, "summary": summary},
        "remember": remember,
        "sections": sections,
    }
    return payload


def fallback_markdown_from_payload(repo_name: str, payload: Dict[str, object]) -> str:
    buckets: List[Tuple[str, List[Tuple[str, str, str]]]] = []
    for section in payload["sections"]:
        sec = section  # type: ignore[assignment]
        items = [
            (link["title"], link["url"], link["note"])
            for link in sec["links"]  # type: ignore[index]
        ]
        buckets.append((sec["title"], items))  # type: ignore[arg-type]
    markdown = render_llms_markdown(
        project_name=repo_name,
        project_purpose=payload["project"]["summary"],  # type: ignore[index]
        remember_bullets=payload["remember"],  # type: ignore[index]
        buckets=buckets,
    )
    header = textwrap.dedent(
        """\
        <!-- Generated via fallback path (no LM). -->
        """
    )
    return header + "\n" + markdown


def fallback_llms_markdown(
    repo_name: str,
    repo_url: str,
    file_tree: str,
    readme_content: str,
    *,
    default_branch: str | None = None,
    is_private: bool = False,
    github_token: str | None = None,
    link_style: str = "blob",
) -> str:
    payload = fallback_llms_payload(
        repo_name=repo_name,
        repo_url=repo_url,
        file_tree=file_tree,
        readme_content=readme_content,
        default_branch=default_branch,
        is_private=is_private,
        github_token=github_token,
        link_style=link_style,
    )
    return fallback_markdown_from_payload(repo_name, payload)


__all__ = [
    "fallback_llms_payload",
    "fallback_llms_markdown",
    "fallback_markdown_from_payload",
]
```

src/lms_llmsTxt/full_builder.py
```
from __future__ import annotations

import base64
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin
import posixpath
import requests
from .github import  _normalize_repo_path

@dataclass
class GhRef:
    owner: str
    repo: str
    path: str
    ref: Optional[str] = None


_GH_LINK = re.compile(
    r"https?://(?:raw\.githubusercontent\.com|github\.com)/(?P<owner>[^/]+)/(?P<repo>[^/]+)/"
    r"(?:(?:blob|tree)/)?(?P<ref>[^/]+)/(?P<path>.+)$",
    re.I,
)


def parse_github_link(url: str) -> Optional[GhRef]:
    match = _GH_LINK.match(url)
    if not match:
        return None
    groups = match.groupdict()
    return GhRef(groups["owner"], groups["repo"], groups["path"], groups.get("ref"))


def gh_get_file(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[str, bytes]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref} if ref else {}
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lms-lmstxt",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, params=params, headers=headers, timeout=30)
    if response.status_code == 404:
        raise FileNotFoundError(f"GitHub 404 for {owner}/{repo}/{path}@{ref or 'default'}")
    response.raise_for_status()
    payload = response.json()
    if payload.get("encoding") == "base64":
        body = base64.b64decode(payload["content"])
    else:
        body = payload.get("content", "").encode("utf-8", "ignore")
    mime_hint = payload.get("type", "file")
    return mime_hint, body


def fetch_raw_file(
    owner: str,
    repo: str,
    path: str,
    ref: str,
) -> bytes:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    response = requests.get(
        url,
        headers={"User-Agent": "lms-lmstxt"},
        timeout=30,
    )
    if response.status_code == 404:
        raise FileNotFoundError(f"Raw GitHub 404 for {owner}/{repo}/{path}@{ref}")
    response.raise_for_status()
    return response.content


# curated list item like "- [Title](https://...)"
_PAGE_LINK = re.compile(r"^\s*-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^\s)]+)\)", re.M)

# within-page link patterns
_MD_LINK = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)")
_HTML_LINK = re.compile(r"<a\s+[^>]*href=[\"'](?P<href>[^\"'#]+)[\"'][^>]*>(?P<text>.*?)</a>", re.I | re.S)

# crude HTML-to-text helpers (stdlib only)
_TAG = re.compile(r"<[^>]+>")
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
_WHITESPACE = re.compile(r"[ \t\f\v]+")
_NEWLINES = re.compile(r"\n{3,}")


def iter_llms_links(curated_text: str) -> Iterable[Tuple[str, str]]:
    for match in _PAGE_LINK.finditer(curated_text):
        yield match.group("title").strip(), match.group("url").strip()


def sanitize_path_for_block(title: str, url: str, gh: Optional[GhRef]) -> str:
    if gh:
        path = gh.path
    else:
        # website: create a stable, readable label from the title
        path = title.lower().strip().replace(" ", "-")
    return path.lstrip("/")

def _resolve_repo_url(gh: GhRef, ref: str, href: str, style: str = "blob") -> Optional[str]:
    """
    Resolve a repo-relative link found in Markdown/HTML to a canonical
    GitHub URL (blob or raw).

    - Leaves absolute http(s) links unchanged.
    - Ignores anchors, mailto:, javascript:.
    - Normalizes '.' and '..' segments.
    - For extensionless paths (no '.' in final segment), assumes '.md'.
    """
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:")):
        return None
    if href.startswith(("http://", "https://")):
        return href

    # Build a repo-relative path
    if href.startswith("/"):
        rel = href.lstrip("/")
    else:
        base_dir = gh.path.rsplit("/", 1)[0] if "/" in gh.path else ""
        rel = f"{base_dir}/{href}" if base_dir else href

    rel = _normalize_repo_path(rel)

    # Heuristic: if the last segment has no dot, treat it as a markdown file.
    last = rel.rsplit("/", 1)[-1]
    if "." not in last:
        rel = rel + ".md"

    if style == "raw":
        return f"https://raw.githubusercontent.com/{gh.owner}/{gh.repo}/{ref}/{rel}"
    return f"https://github.com/{gh.owner}/{gh.repo}/blob/{ref}/{rel}"




def _resolve_web_url(base_url: str, href: str) -> Optional[str]:
    """
    Resolve a general website href against base_url.
    Ignore fragments and non-http(s) schemes.
    """
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    resolved = urljoin(base_url, href)
    if resolved.startswith(("http://", "https://")):
        return resolved
    return None


def _extract_links(body_text: str, *, gh: Optional[GhRef], ref: str, base_url: Optional[str], link_style: str = "blob") -> list[tuple[str, str]]:
    """
    Extract outbound links from Markdown/HTML and resolve to absolute URLs.
    For GitHub pages pass gh+ref. For websites pass base_url.
    """
    seen: set[tuple[str, str]] = set()
    found: list[tuple[str, str]] = []

    def _add(text: str, href: str):
        key = (text, href)
        if key not in seen:
            seen.add(key)
            found.append(key)

    # Markdown links
    for m in _MD_LINK.finditer(body_text):
        text = m.group("text").strip()
        href = m.group("href").strip()
        if gh:
            resolved = _resolve_repo_url(gh, ref, href, style=link_style)
        else:
            resolved = _resolve_web_url(base_url or "", href)
        if resolved:
            _add(text, resolved)

    # HTML links
    for m in _HTML_LINK.finditer(body_text):
        text = re.sub(r"\s+", " ", m.group("text")).strip() or "link"
        href = m.group("href").strip()
        if gh:
            resolved = _resolve_repo_url(gh, ref, href, style=link_style)
        else:
            resolved = _resolve_web_url(base_url or "", href)
        if resolved:
            _add(text, resolved)

    return found


def _html_to_text(html: str) -> str:
    """
    Very simple HTML -> text. Removes scripts/styles, strips tags,
    normalizes whitespace. No external dependencies.
    """
    cleaned = _SCRIPT_STYLE.sub("", html)
    cleaned = _TAG.sub("", cleaned)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = _WHITESPACE.sub(" ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = _NEWLINES.sub("\n\n", cleaned)
    return cleaned.strip()


def _fetch_website(url: str, user_agent: str = "lms-lmstxt", timeout: int = 30) -> str:
    resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    resp.raise_for_status()
    # prefer text; if bytes fallback, requests gives .text with encoding guess
    return resp.text


def build_llms_full_from_repo(
    curated_llms_text: str,
    max_bytes_per_file: int = 800_000,
    max_files: int = 100,
    *,
    prefer_raw: bool = False,
    default_ref: Optional[str] = None,
    token: Optional[str] = None,
    link_style: str = "blob",
) -> str:
    """
    Extended: also accepts general website URLs in the curated list.
    GitHub URLs are fetched via API/raw as before. Non-GitHub URLs are fetched as HTML.
    """
    resolved_token = (
        token
        if token is not None
        else os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
    )
    blocks = []
    seen = set()
    count = 0

    for title, url in iter_llms_links(curated_llms_text):
        if count >= max_files:
            break

        gh = parse_github_link(url)

        # dedupe key
        if gh:
            key = (gh.owner, gh.repo, gh.path, gh.ref or "")
        else:
            key = ("web", url)
        if key in seen:
            continue
        seen.add(key)

        if gh:
            # GitHub path fetch
            resolved_ref = gh.ref or default_ref or "main"
            try:
                if prefer_raw:
                    body = fetch_raw_file(gh.owner, gh.repo, gh.path, resolved_ref)
                else:
                    _, body = gh_get_file(
                        gh.owner,
                        gh.repo,
                        gh.path,
                        resolved_ref,
                        resolved_token,
                    )
            except requests.HTTPError as exc:
                message = _format_http_error(gh, resolved_ref, exc, auth_used=not prefer_raw)
                body = message.encode("utf-8")
            except Exception as exc:
                message = _format_generic_error(gh, resolved_ref, exc)
                body = message.encode("utf-8")

            truncated = False
            if len(body) > max_bytes_per_file:
                body = body[:max_bytes_per_file] + b"\n[truncated]\n"
                truncated = True

            block_path = sanitize_path_for_block(title, url, gh)
            text_body = body.decode("utf-8", "replace")

            links = _extract_links(text_body, gh=gh, ref=resolved_ref, base_url=None, link_style=link_style)[:100]
            link_section = ""
            if links:
                bullet_lines = "\n".join(f"- [{t}]({h})" for t, h in links)
                link_section = f"\n## Links discovered\n{bullet_lines}\n"

            blocks.append(f"--- {block_path} ---\n{text_body}\n{link_section}")
            count += 1

        else:
            # General website fetch
            try:
                html = _fetch_website(url)
            except Exception as exc:
                text_body = f"[fetch-error] {url} :: {exc}"
            else:
                text_body = _html_to_text(html)

            # enforce size after text conversion for websites
            encoded = text_body.encode("utf-8", "ignore")
            if len(encoded) > max_bytes_per_file:
                encoded = encoded[:max_bytes_per_file] + b"\n[truncated]\n"
                text_body = encoded.decode("utf-8", "ignore")

            links = _extract_links(
                html if 'html' in locals() else text_body,
                gh=None,
                ref="",
                base_url=url,
                link_style=link_style,
            )[:100]
            link_section = ""
            if links:
                bullet_lines = "\n".join(f"- [{t}]({h})" for t, h in links)
                link_section = f"\n## Links discovered\n{bullet_lines}\n"

            block_path = sanitize_path_for_block(title, url, gh=None)
            blocks.append(f"--- {block_path} ---\n{text_body}\n{link_section}")
            count += 1

    disclaimer = textwrap.dedent(
        """\
        # llms-full (private-aware)
        > Built from GitHub files and website pages. Large files may be truncated.
        """
    )
    return disclaimer + "\n" + "\n".join(blocks)


def _format_http_error(
    gh: GhRef,
    ref: str,
    exc: requests.HTTPError,
    *,
    auth_used: bool,
) -> str:
    response = exc.response
    status = response.status_code if response is not None else "unknown"
    reason = response.reason if response is not None else str(exc)
    hint = ""
    if auth_used and response is not None and response.status_code == 403:
        hint = (
            " Verify that GITHUB_ACCESS_TOKEN or GH_TOKEN has 'repo' scope and is not expired."
        )
    return (
        f"[fetch-error] {gh.owner}/{gh.repo}/{gh.path}@{ref} :: "
        f"HTTP {status} {reason}.{hint}"
    )


def _format_generic_error(gh: GhRef, ref: str, exc: Exception) -> str:
    return (
        f"[fetch-error] {gh.owner}/{gh.repo}/{gh.path}@{ref} :: {exc}"
    )
```

src/lms_llmsTxt/github.py
```
from __future__ import annotations

import base64
import os
import re
from typing import Iterable

import requests
import posixpath
from .models import RepositoryMaterial

def _normalize_repo_path(path: str) -> str:
    """
    Normalize a repo-relative path:
    - strip leading slash
    - collapse '.' and '..' segments
    """
    path = path.lstrip("/")
    # posix-style normalization: 'docs/./x/../y' -> 'docs/y'
    return posixpath.normpath(path)

_GITHUB_URL = re.compile(
    r"""
    ^
    (?:
        git@github\.com:
        (?P<owner_ssh>[^/]+)/(?P<repo_ssh>[^/]+?)(?:\.git)?
        |
        https?://github\.com/
        (?P<owner_http>[^/]+)/(?P<repo_http>[^/]+?)(?:\.git)?
    )
    (?:/.*)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SESSION = requests.Session()


def owner_repo_from_url(repo_url: str) -> tuple[str, str]:
    """Return ``(owner, repo)`` for https or SSH GitHub URLs."""
    m = _GITHUB_URL.match(repo_url.strip())
    if not m:
        raise ValueError(f"Unrecognized GitHub URL: {repo_url!r}")
    owner = m.group("owner_http") or m.group("owner_ssh")
    repo = m.group("repo_http") or m.group("repo_ssh")
    return owner, repo


def _auth_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lms-lmstxt",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_repository_metadata(owner: str, repo: str, token: str | None) -> dict[str, object]:
    resp = _SESSION.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=_auth_headers(token),
        timeout=20,
    )
    if resp.status_code == 404:
        raise FileNotFoundError(f"Repository not found: {owner}/{repo}")
    resp.raise_for_status()
    payload = resp.json()
    return {
        "default_branch": payload.get("default_branch", "main"),
        "is_private": bool(payload.get("private", False)),
        "visibility": payload.get("visibility"),
    }


def get_default_branch(owner: str, repo: str, token: str | None) -> str:
    metadata = get_repository_metadata(owner, repo, token)
    return str(metadata.get("default_branch", "main"))


def fetch_file_tree(
    owner: str, repo: str, ref: str, token: str | None
) -> Iterable[str]:
    resp = _SESSION.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}",
        params={"recursive": 1},
        headers=_auth_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    return [
        item["path"]
        for item in payload.get("tree", [])
        if item.get("type") == "blob" and "path" in item
    ]


def fetch_file_content(
    owner: str, repo: str, path: str, ref: str, token: str | None
) -> str | None:
    resp = _SESSION.get(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        params={"ref": ref},
        headers=_auth_headers(token),
        timeout=20,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    payload = resp.json()
    content = payload.get("content")
    if content and payload.get("encoding") == "base64":
        return base64.b64decode(content).decode("utf-8", "replace")
    if isinstance(content, str):
        return content
    return None


def gather_repository_material(repo_url: str, token: str | None = None) -> RepositoryMaterial:
    owner, repo = owner_repo_from_url(repo_url)
    metadata = get_repository_metadata(owner, repo, token)
    ref = str(metadata.get("default_branch", "main"))

    file_paths = fetch_file_tree(owner, repo, ref, token)
    file_tree = "\n".join(sorted(file_paths))

    readme = fetch_file_content(owner, repo, "README.md", ref, token) or ""

    package_blobs = []
    for candidate in (
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "requirements.txt",
        "package.json",
    ):
        content = fetch_file_content(owner, repo, candidate, ref, token)
        if content:
            package_blobs.append(f"=== {candidate} ===\n{content}")

    package_files = "\n\n".join(package_blobs)

    return RepositoryMaterial(
        repo_url=repo_url,
        file_tree=file_tree,
        readme_content=readme,
        package_files=package_files,
        default_branch=ref,
        is_private=bool(metadata.get("is_private", False)),
    )


def construct_github_file_url(
    repo_url: str, path: str, ref: str | None = None, style: str = "blob"
) -> str:
    """
    Build a canonical GitHub URL for a repo file.

    style="blob": https://github.com/owner/repo/blob/ref/path
    style="raw":  https://raw.githubusercontent.com/owner/repo/ref/path
    """
    owner, repo = owner_repo_from_url(repo_url)
    if not ref:
        token = os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
        try:
            ref = get_default_branch(owner, repo, token)
        except Exception:
            ref = "main"

    norm_path = _normalize_repo_path(path)

    if style == "raw":
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{norm_path}"
    return f"https://github.com/{owner}/{repo}/blob/{ref}/{norm_path}"

```

src/lms_llmsTxt/graph_builder.py
```
from __future__ import annotations

import json
from pathlib import Path
import re

from .graph_models import (
    ForceGraphData,
    ForceGraphLink,
    ForceGraphNode,
    GraphNodeEvidence,
    RepoGraphNode,
    RepoSkillGraph,
)
from .repo_digest import RepoDigest


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "node"


def build_repo_graph(digest: RepoDigest) -> RepoSkillGraph:
    nodes: list[RepoGraphNode] = []

    moc_links: list[str] = []
    for subsystem in digest.subsystems[:20]:
        node_id = _slug(subsystem["name"])
        moc_links.append(node_id)
        content = (
            f"---\n"
            f"title: {subsystem['name']}\n"
            f"type: concept\n"
            f"description: {subsystem['summary']}\n"
            f"---\n\n"
            f"{subsystem['summary']}\n\n"
            f"Key symbols: {', '.join(subsystem.get('key_symbols', [])[:12]) or 'n/a'}\n"
        )
        evidence = [
            GraphNodeEvidence(path=path, start_line=1, end_line=1, artifact_ref="repo_digest")
            for path in subsystem.get("paths", [])[:8]
        ]
        nodes.append(
            RepoGraphNode(
                id=node_id,
                label=subsystem["name"],
                type="concept",
                description=subsystem["summary"],
                content=content,
                links=[],
                evidence=evidence,
                artifacts=["repo.graph.json", "repo.force.json"],
                tags=["subsystem", digest.primary_language],
            )
        )

    moc_content = (
        f"# {digest.topic}\n\n"
        f"This map summarizes repository structure and important exploration paths. "
        f"Start with subsystem nodes and follow evidence-backed links to inspect source files.\n\n"
        f"## Domain Clusters\n"
        + "\n".join(
            f"- Explore [[{node_id}]] to inspect related module behavior and evidence anchors."
            for node_id in moc_links[:16]
        )
        + "\n\n## Explorations Needed\n"
        "- Which subsystems should be prioritized for onboarding documentation?\n"
        "- Which dependencies are high-risk and need version guardrails?\n"
        "- Where should integration tests be expanded based on current topology?\n"
    )

    moc = RepoGraphNode(
        id="moc",
        label=f"{digest.topic} Map",
        type="moc",
        description=digest.architecture_summary or "Repository map of content",
        content=moc_content,
        links=moc_links[:16],
        evidence=[GraphNodeEvidence(path="repo_digest", artifact_ref=digest.digest_id)],
        artifacts=["repo.graph.json"],
        tags=["moc", digest.primary_language],
    )

    nodes.insert(0, moc)
    return RepoSkillGraph(topic=digest.topic, nodes=nodes)


def to_force_graph(graph: RepoSkillGraph) -> ForceGraphData:
    nodes = [
        ForceGraphNode(
            id=node.id,
            label=node.label,
            type=node.type,
            val=3.0 if node.type == "moc" else 1.5,
        )
        for node in graph.nodes
    ]
    links: list[ForceGraphLink] = []
    for node in graph.nodes:
        for target in node.links:
            links.append(ForceGraphLink(source=node.id, target=target))
    return ForceGraphData(nodes=nodes, links=links)


def emit_graph_files(graph: RepoSkillGraph, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    force = to_force_graph(graph)

    graph_json = output_dir / "repo.graph.json"
    force_json = output_dir / "repo.force.json"
    nodes_dir = output_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    graph_json.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    force_json.write_text(force.model_dump_json(indent=2), encoding="utf-8")

    for node in graph.nodes:
        (nodes_dir / f"{node.id}.md").write_text(node.content.rstrip() + "\n", encoding="utf-8")

    return {
        "graph_json": str(graph_json),
        "force_json": str(force_json),
        "nodes_dir": str(nodes_dir),
    }


def load_graph_from_file(path: Path) -> RepoSkillGraph:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RepoSkillGraph.model_validate(payload)
```

src/lms_llmsTxt/graph_models.py
```
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

GraphNodeType = Literal["moc", "concept", "pattern", "gotcha"]


class GraphNodeEvidence(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None
    artifact_ref: str | None = None
    excerpt: str | None = None


class GraphEdge(BaseModel):
    target_id: str
    relation: str = "relates_to"
    prose: str | None = None


class RepoGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    description: str
    content: str
    links: list[str] = Field(default_factory=list)
    evidence: list[GraphNodeEvidence] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RepoSkillGraph(BaseModel):
    topic: str
    nodes: list[RepoGraphNode]
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ForceGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    val: float = 1.0


class ForceGraphLink(BaseModel):
    source: str
    target: str


class ForceGraphData(BaseModel):
    nodes: list[ForceGraphNode]
    links: list[ForceGraphLink]
```

src/lms_llmsTxt/lmstudio.py
```
from __future__ import annotations

import logging
import subprocess
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

from .config import AppConfig

try:
    import dspy
except ImportError:
    from .signatures import dspy

logger = logging.getLogger(__name__)

try:  # Optional dependency recommended for managed unload
    import lmstudio as _LMSTUDIO_SDK  # type: ignore
except Exception:  # pragma: no cover - SDK is optional at runtime
    _LMSTUDIO_SDK = None  # type: ignore[assignment]


class LMStudioConnectivityError(RuntimeError):
    """Raised when LM Studio cannot be reached or does not expose the model."""


_MODEL_ENDPOINTS: tuple[str, ...] = ("/v1/models", "/api/v1/models", "/models")
_LOAD_ENDPOINT_PATTERNS: tuple[str, ...] = (
    "/v1/models/{model}/load",
    "/v1/models/load",
    "/v1/models/{model}",
    "/api/v1/models/{model}/load",
    "/api/v1/models/load",
    "/api/v1/models/{model}",
    "/models/{model}/load",
    "/models/load",
    "/models/{model}",
)
_UNLOAD_ENDPOINT_PATTERNS: tuple[str, ...] = (
    "/v1/models/{model}/unload",
    "/v1/models/unload",
    "/v1/models/{model}",
    "/api/v1/models/{model}/unload",
    "/api/v1/models/unload",
    "/api/v1/models/{model}",
    "/models/{model}/unload",
    "/models/unload",
    "/models/{model}",
)


def _build_lmstudio_url(base: str, endpoint: str) -> str:
    """
    Join ``base`` and ``endpoint`` while avoiding duplicated version prefixes.
    """

    base_trimmed = base.rstrip("/")
    path = endpoint
    for prefix in ("/v1", "/api/v1"):
        if base_trimmed.endswith(prefix) and path.startswith(prefix):
            path = path[len(prefix) :] or ""
            if path and not path.startswith("/"):
                path = "/" + path
            break

    if not path.startswith("/"):
        path = "/" + path if path else ""

    return base_trimmed + path


def _fetch_models(
    base_url: str, headers: dict[str, str]
) -> Tuple[set[str], Optional[str]]:
    """
    Return (models, successful_endpoint) by probing known LM Studio endpoints.

    Recent LM Studio releases mirror OpenAI's `/v1/models` endpoint, while older
    builds exposed `/api/v1/models` or `/models`. We probe the known variants and
    return the first that yields a usable payload.
    """
    last_error: Optional[requests.RequestException] = None
    for endpoint in _MODEL_ENDPOINTS:
        url = _build_lmstudio_url(base_url, endpoint)
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            last_error = exc
            logger.debug("LM Studio GET %s failed: %s", url, exc)
            continue

        models: set[str] = set()
        if isinstance(payload, dict) and "data" in payload:
            for item in payload["data"]:
                if isinstance(item, dict):
                    identifier = item.get("id") or item.get("name")
                    if identifier:
                        models.add(str(identifier))
                elif isinstance(item, str):
                    models.add(item)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    identifier = item.get("id") or item.get("name")
                    if identifier:
                        models.add(str(identifier))
                elif isinstance(item, str):
                    models.add(item)

        logger.debug("LM Studio models from %s: %s", url, models or "<empty>")
        return models, endpoint

    if last_error:
        raise last_error
    return set(), None


def _load_model_http(
    base_url: str,
    headers: dict[str, str],
    model: str,
    endpoint_hint: Optional[str],
) -> bool:
    """
    Attempt to load the requested model via LM Studio's HTTP API.

    Returns True if any request returns a 2xx status code.
    """
    def candidate_paths() -> Iterable[str]:
        if endpoint_hint and endpoint_hint.startswith("/v1"):
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/v1")]
            yield from primary + secondary
        elif endpoint_hint and endpoint_hint.startswith("/api/v1"):
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            yield from primary + secondary
        elif endpoint_hint:
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            yield from primary + secondary
        else:
            yield from _LOAD_ENDPOINT_PATTERNS

    for template in candidate_paths():
        url = _build_lmstudio_url(base_url, template.format(model=model))
        body_candidates = (
            None,
            {"model": model},
            {"id": model},
            {"name": model},
        )
        for body in body_candidates:
            try:
                logger.debug("Attempting LM Studio load via %s body=%s", url, body)
                if body is None:
                    response = requests.post(url, headers=headers, timeout=10)
                else:
                    enriched_headers = dict(headers)
                    enriched_headers["Content-Type"] = "application/json"
                    response = requests.post(
                        url,
                        headers=enriched_headers,
                        json=body,
                        timeout=10,
                    )
                if response.status_code < 400:
                    logger.info(
                        "LM Studio accepted load request via %s (status %s)",
                        url,
                        response.status_code,
                    )
                    return True
                logger.debug(
                    "LM Studio rejected load request via %s (status %s: %s)",
                    url,
                    response.status_code,
                    response.text,
                )
            except requests.RequestException as exc:
                logger.debug("LM Studio load request failed via %s: %s", url, exc)
                continue
    return False


def _load_model_cli(model: str) -> bool:
    """
    Attempt to load the model using the `lms` CLI if available.
    """
    try:
        logger.debug("Attempting CLI load for model '%s'", model)
        result = subprocess.run(
            ["lms", "load", model],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        logger.debug("LM Studio CLI (lms) not found on PATH; skipping CLI load.")
        return False
    except subprocess.SubprocessError as exc:  # pragma: no cover - defensive
        logger.debug("LM Studio CLI load failed: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("LM Studio CLI reported successful load for '%s'.", model)
        return True

    logger.debug(
        "LM Studio CLI returned %s: %s %s",
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return False


def _host_from_api_base(api_base: str | None) -> Optional[str]:
    if not api_base:
        return None
    parsed = urlparse(str(api_base))
    host = parsed.netloc or parsed.path
    host = host.strip("/") if host else ""
    return host or None


def _configure_sdk_client(config: AppConfig) -> None:
    if _LMSTUDIO_SDK is None:
        return
    host = _host_from_api_base(config.lm_api_base)
    if not host:
        return
    try:
        configure = getattr(_LMSTUDIO_SDK, "configure_default_client", None)
        if callable(configure):
            configure(host)
    except Exception as exc:  # pragma: no cover - diagnostic only
        logger.debug("LM Studio SDK configure_default_client failed: %s", exc)


def _unload_model_sdk(config: AppConfig) -> bool:
    """
    Attempt to unload the configured model via the official LM Studio Python SDK.
    """
    if _LMSTUDIO_SDK is None:
        return False

    _configure_sdk_client(config)

    target_key = (config.lm_model or "").strip()
    handles: list = []
    try:
        handles = list(_LMSTUDIO_SDK.list_loaded_models("llm"))  # type: ignore[attr-defined]
    except AttributeError:
        try:
            client = _LMSTUDIO_SDK.get_default_client()  # type: ignore[attr-defined]
            handles = list(client.llm.list_loaded_models())  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - diagnostic path
            logger.debug("LM Studio SDK list_loaded_models unavailable: %s", exc)
            handles = []
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK list_loaded_models failed: %s", exc)
        handles = []

    selected = []
    for handle in handles:
        try:
            identifier = getattr(handle, "identifier", None)
            model_key = getattr(handle, "model_key", None) or getattr(handle, "modelKey", None)
        except Exception:  # pragma: no cover - defensive
            identifier = model_key = None
        if target_key and target_key not in {identifier, model_key}:
            continue
        selected.append(handle)
    if not selected:
        selected = handles

    success = False
    for handle in selected:
        try:
            handle.unload()
            success = True
        except Exception as exc:  # pragma: no cover - diagnostic path
            logger.debug("LM Studio SDK failed to unload handle %r: %s", handle, exc)

    if success:
        logger.info("LM Studio SDK unloaded model '%s'.", target_key or selected[0])
        return True

    try:
        if target_key:
            handle = _LMSTUDIO_SDK.llm(target_key)  # type: ignore[attr-defined]
        else:
            handle = _LMSTUDIO_SDK.llm()  # type: ignore[attr-defined]
    except TypeError:
        handle = _LMSTUDIO_SDK.llm()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK llm(%s) failed: %s", target_key or "<default>", exc)
        return False

    try:
        handle.unload()
        logger.info("LM Studio SDK unloaded model '%s'.", target_key or getattr(handle, "model_key", "<default>"))
        return True
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK handle unload failed: %s", exc)
        return False


def _unload_model_http(
    base_url: str,
    headers: dict[str, str],
    model: str,
    endpoint_hint: Optional[str],
) -> bool:
    """
    Attempt to unload the requested model via LM Studio's HTTP API.

    Returns True if any request returns a 2xx status code.
    """

    def candidate_paths() -> Iterable[str]:
        if endpoint_hint and endpoint_hint.startswith("/v1"):
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/v1")]
            yield from primary + secondary
        elif endpoint_hint and endpoint_hint.startswith("/api/v1"):
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            yield from primary + secondary
        elif endpoint_hint:
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            yield from primary + secondary
        else:
            yield from _UNLOAD_ENDPOINT_PATTERNS

    for template in candidate_paths():
        url = _build_lmstudio_url(base_url, template.format(model=model))
        body_candidates = (
            None,
            {"model": model},
            {"id": model},
            {"name": model},
        )
        for body in body_candidates:
            try:
                logger.debug("Attempting LM Studio unload via POST %s body=%s", url, body)
                if body is None:
                    response = requests.post(url, headers=headers, timeout=10)
                else:
                    enriched_headers = dict(headers)
                    enriched_headers["Content-Type"] = "application/json"
                    response = requests.post(
                        url,
                        headers=enriched_headers,
                        json=body,
                        timeout=10,
                    )
                if response.status_code < 400:
                    logger.info(
                        "LM Studio accepted unload request via POST %s (status %s)",
                        url,
                        response.status_code,
                    )
                    return True
                logger.debug(
                    "LM Studio rejected unload via POST %s (status %s: %s)",
                    url,
                    response.status_code,
                    response.text,
                )
            except requests.RequestException as exc:
                logger.debug("LM Studio unload request failed via %s: %s", url, exc)
                continue
    return False


def _unload_model_cli(model: str) -> bool:
    """
    Attempt to unload the model using the `lms` CLI if available.
    """
    try:
        logger.debug("Attempting CLI unload for model '%s'", model)
        result = subprocess.run(
            ["lms", "unload", model],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        logger.debug("LM Studio CLI (lms) not found on PATH; skipping CLI unload.")
        return False
    except subprocess.SubprocessError as exc:  # pragma: no cover - defensive
        logger.debug("LM Studio CLI unload failed: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("LM Studio CLI reported successful unload for '%s'.", model)
        return True

    logger.debug(
        "LM Studio CLI unload returned %s: %s %s",
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return False


def _ensure_lmstudio_ready(config: AppConfig) -> None:
    """
    Confirm that LM Studio exposes the requested model, attempting to load it if needed.

    Raises
    ------
    LMStudioConnectivityError
        If the LM Studio server cannot be contacted or refuses to expose the model.
    """

    headers = {"Authorization": f"Bearer {config.lm_api_key or ''}"}
    base = config.lm_api_base.rstrip("/")

    try:
        models, endpoint_hint = _fetch_models(base, headers)
    except requests.RequestException as exc:
        raise LMStudioConnectivityError(
            f"Failed to reach LM Studio at {base}: {exc}"
        ) from exc

    if config.lm_model in models:
        logger.debug("LM Studio already has model '%s' loaded.", config.lm_model)
        return

    logger.info(
        "LM Studio does not advertise model '%s'; attempting to load it automatically.",
        config.lm_model,
    )

    loaded = _load_model_http(base, headers, config.lm_model, endpoint_hint)
    if not loaded:
        loaded = _load_model_cli(config.lm_model)

    if not loaded:
        raise LMStudioConnectivityError(
            f"Unable to load model '{config.lm_model}' automatically. "
            "Please load it in the LM Studio UI and retry."
        )

    # Re-query to confirm the model is present.
    try:
        models, _ = _fetch_models(base, headers)
    except requests.RequestException as exc:
        raise LMStudioConnectivityError(
            f"Verified load but subsequent model fetch failed: {exc}"
        ) from exc

    if config.lm_model not in models:
        raise LMStudioConnectivityError(
            f"Model '{config.lm_model}' did not appear in LM Studio after load attempts. "
            "Check the LM Studio logs for more details."
        )

    logger.info("LM Studio model '%s' is ready.", config.lm_model)


def configure_lmstudio_lm(config: AppConfig, *, cache: bool = False) -> dspy.LM:
    """
    Configure DSPy to talk to LM Studio's OpenAI-compatible endpoint.
    """

    _ensure_lmstudio_ready(config)

    lm = dspy.LM(
        f"openai/{config.lm_model}",
        api_base=config.lm_api_base,
        api_key=config.lm_api_key,
        cache=cache,
        streaming=config.lm_streaming,
    )
    dspy.configure(lm=lm)
    return lm


def unload_lmstudio_model(config: AppConfig) -> None:
    """
    Attempt to unload the configured LM Studio model to free resources.
    """

    if _unload_model_sdk(config):
        return

    headers = {"Authorization": f"Bearer {config.lm_api_key or ''}"}
    base = config.lm_api_base.rstrip("/")

    try:
        _, endpoint_hint = _fetch_models(base, headers)
    except requests.RequestException as exc:  # pragma: no cover - informational
        endpoint_hint = None
        logger.debug("Unable to refresh LM Studio endpoint hint before unload: %s", exc)

    if _unload_model_http(base, headers, config.lm_model, endpoint_hint):
        return

    if _unload_model_cli(config.lm_model):
        return

    logger.warning(
        "Failed to unload LM Studio model '%s' via SDK, HTTP, or CLI. The model may remain loaded.",
        config.lm_model,
    )


__all__ = ["configure_lmstudio_lm", "LMStudioConnectivityError", "unload_lmstudio_model"]
```

src/lms_llmsTxt/models.py
```
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepositoryMaterial:
    """Aggregate of repository inputs we feed into DSPy."""

    repo_url: str
    file_tree: str
    readme_content: str
    package_files: str
    default_branch: str
    is_private: bool


@dataclass
class GenerationArtifacts:
    """Outputs written to disk once generation completes."""

    llms_txt_path: str
    llms_full_path: str | None = None
    ctx_path: str | None = None
    json_path: str | None = None
    graph_json_path: str | None = None
    force_graph_path: str | None = None
    graph_nodes_dir: str | None = None
    used_fallback: bool = False
```

src/lms_llmsTxt/pipeline.py
```
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .analyzer import RepositoryAnalyzer
from .context_budget import BudgetDecision, build_context_budget
from .config import AppConfig
from .context_compaction import compact_material
from .full_builder import build_llms_full_from_repo
from .fallback import (
    fallback_llms_payload,
    fallback_markdown_from_payload,
)
from .github import gather_repository_material, owner_repo_from_url
from .graph_builder import build_repo_graph, emit_graph_files
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
from .reasoning import sanitize_final_output
from .repo_digest import build_repo_digest
from .retry_policy import ErrorClass, classify_generation_error, next_retry_budget
from .schema import LLMS_JSON_SCHEMA

try:  # Optional import; litellm is a transitive dependency of dspy.
    from litellm.exceptions import BadRequestError as LiteLLMBadRequestError
except Exception:  # pragma: no cover - fall back to generic Exception
    LiteLLMBadRequestError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
except Exception:  # pragma: no cover
    LiteLLMRateLimitError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import AuthenticationError as LiteAuthError
except Exception:  # pragma: no cover
    LiteAuthError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import NotFoundError as LiteNotFoundError
except Exception:  # pragma: no cover
    LiteNotFoundError = tuple()  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _timestamp_comment(prefix: str = "# Generated") -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"{prefix}: {now} UTC"


def _write_text(path: Path, content: str, stamp: bool) -> None:
    text = content.rstrip()
    if stamp:
        text += "\n\n" + _timestamp_comment()
    path.write_text(text + "\n", encoding="utf-8")


def prepare_repository_material(config: AppConfig, repo_url: str) -> RepositoryMaterial:
    return gather_repository_material(repo_url, config.github_token)


def run_generation(
    repo_url: str,
    config: AppConfig,
    *,
    stamp: bool = False,
    cache_lm: bool = False,
    build_full: bool = True,
    build_ctx: bool | None = None,
    generate_graph: bool | None = None,
    graph_only: bool = False,
    verbose_budget: bool = False,
    enable_session_memory: bool | None = None,
) -> GenerationArtifacts:
    owner, repo = owner_repo_from_url(repo_url)
    repo_root = config.ensure_output_root(owner, repo)
    base_name = repo.lower().replace(" ", "-")

    logger.debug("Preparing repository material for %s", repo_url)
    material = prepare_repository_material(config, repo_url)
    try:
        analyzer = RepositoryAnalyzer(production_mode=True)
    except TypeError:
        # Compatibility with tests that monkeypatch RepositoryAnalyzer as a zero-arg callable.
        analyzer = RepositoryAnalyzer()

    fallback_payload = None
    used_fallback = False
    project_name = repo.replace("-", " ").replace("_", " ").title()

    model_loaded = False

    try:
        logger.info("Configuring LM Studio model '%s'", config.lm_model)
        configure_lmstudio_lm(config, cache=cache_lm)
        model_loaded = True

        working_material = material
        budget = build_context_budget(config, working_material)
        if verbose_budget:
            logger.info(
                "Initial budget: estimated=%s available=%s decision=%s",
                budget.estimated_prompt_tokens,
                budget.available_tokens,
                budget.decision,
            )

        if budget.decision != BudgetDecision.APPROVED:
            working_material = compact_material(working_material, budget, config)
            budget = build_context_budget(config, working_material)
            if verbose_budget:
                logger.info(
                    "After compaction: estimated=%s available=%s decision=%s",
                    budget.estimated_prompt_tokens,
                    budget.available_tokens,
                    budget.decision,
                )

        repo_digest = build_repo_digest(working_material, topic=project_name)
        llms_text = ""
        retry_step = 0
        current_budget = budget
        while True:
            try:
                analyzer_kwargs = {
                    "repo_url": working_material.repo_url,
                    "file_tree": working_material.file_tree,
                    "readme_content": working_material.readme_content,
                    "package_files": working_material.package_files,
                    "default_branch": working_material.default_branch,
                    "is_private": working_material.is_private,
                    "github_token": config.github_token,
                    "link_style": config.link_style,
                    "repo_digest": repo_digest,
                }
                try:
                    result = analyzer(**analyzer_kwargs)
                except TypeError as call_exc:
                    # Some test/mocked DSPy module variants expose forward() only.
                    if callable(getattr(analyzer, "forward", None)):
                        logger.debug("Analyzer is not directly callable; invoking forward()")
                        result = analyzer.forward(**analyzer_kwargs)
                    else:
                        raise call_exc
                llms_text = result.llms_txt_content
                break
            except Exception as exc:
                err_class = classify_generation_error(exc)
                if err_class in (ErrorClass.CONTEXT_LENGTH, ErrorClass.PAYLOAD_LIMIT):
                    reduced = next_retry_budget(
                        current_budget,
                        retry_step,
                        reduction_steps=config.retry_reduction_steps,
                    )
                    retry_step += 1
                    if reduced is None:
                        raise
                    current_budget = reduced
                    working_material = compact_material(working_material, current_budget, config)
                    repo_digest = build_repo_digest(working_material, topic=project_name)
                    if verbose_budget:
                        logger.warning(
                            "Retrying generation with reduced budget step=%s estimated=%s available=%s",
                            retry_step,
                            current_budget.estimated_prompt_tokens,
                            current_budget.available_tokens,
                        )
                    continue
                raise
    except (
        LiteLLMBadRequestError,
        LiteLLMRateLimitError,
        LiteAuthError,
        LiteNotFoundError,
        LMStudioConnectivityError,
    ) as exc:
        used_fallback = True
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    except Exception as exc:  # pragma: no cover - defensive fallback
        used_fallback = True
        logger.exception("Unexpected error during DSPy generation: %s", exc)
        logger.warning("Falling back to heuristic llms.txt generation using %s.", LLMS_JSON_SCHEMA["title"])
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    finally:
        if model_loaded and config.lm_auto_unload:
            unload_lmstudio_model(config)

    sanitized = sanitize_final_output(llms_text, strict=True)
    llms_txt_path = repo_root / f"{base_name}-llms.txt"
    logger.info("Writing llms.txt to %s", llms_txt_path)
    _write_text(llms_txt_path, sanitized.text or llms_text, stamp)

    ctx_path: Optional[Path] = None
    should_build_ctx = config.enable_ctx if build_ctx is None else build_ctx
    if should_build_ctx:
        try:
            from llms_txt import create_ctx  # type: ignore
        except ImportError:
            create_ctx = None  # type: ignore
        if create_ctx:
            ctx_text = create_ctx(llms_text, optional=False)
            ctx_path = repo_root / f"{base_name}-llms-ctx.txt"
            logger.debug("Writing llms-ctx to %s", ctx_path)
            _write_text(ctx_path, ctx_text, stamp)

    llms_full_path: Optional[Path] = None
    if build_full and not graph_only:
        llms_full_text = build_llms_full_from_repo(
            sanitized.text or llms_text,
            prefer_raw=not material.is_private,
            default_ref=material.default_branch,
            token=config.github_token,
            link_style=config.link_style,
        )
        llms_full_path = repo_root / f"{base_name}-llms-full.txt"
        logger.debug("Writing llms-full to %s", llms_full_path)
        _write_text(llms_full_path, llms_full_text, stamp)

    json_path: Optional[Path] = None
    if fallback_payload:
        json_path = repo_root / f"{base_name}-llms.json"
        json_path.write_text(json.dumps(fallback_payload, indent=2), encoding="utf-8")
        logger.info("Fallback JSON payload written to %s", json_path)

    graph_json_path: Optional[Path] = None
    force_graph_path: Optional[Path] = None
    graph_nodes_dir: Optional[Path] = None
    should_generate_graph = config.enable_repo_graph if generate_graph is None else bool(generate_graph)
    if should_generate_graph:
        digest = build_repo_digest(material, topic=project_name)
        graph = build_repo_graph(digest)
        graph_paths = emit_graph_files(graph, repo_root / "graph")
        graph_json_path = Path(graph_paths["graph_json"])
        force_graph_path = Path(graph_paths["force_json"])
        graph_nodes_dir = Path(graph_paths["nodes_dir"])

    if enable_session_memory if enable_session_memory is not None else config.enable_session_memory:
        try:
            from lms_llmsTxt_mcp.session_memory import SessionMemoryStore

            memory = SessionMemoryStore(repo_root / "session-memory.jsonl")
            memory.append_event(
                "generation",
                {
                    "repo_url": repo_url,
                    "used_fallback": used_fallback,
                    "llms_txt_path": str(llms_txt_path),
                    "graph_json_path": str(graph_json_path) if graph_json_path else None,
                },
            )
        except Exception:  # pragma: no cover - memory is optional
            logger.exception("Failed to append session memory event")

    return GenerationArtifacts(
        llms_txt_path=str(llms_txt_path),
        llms_full_path=str(llms_full_path) if llms_full_path else None,
        ctx_path=str(ctx_path) if ctx_path else None,
        json_path=str(json_path) if json_path else None,
        graph_json_path=str(graph_json_path) if graph_json_path else None,
        force_graph_path=str(force_graph_path) if force_graph_path else None,
        graph_nodes_dir=str(graph_nodes_dir) if graph_nodes_dir else None,
        used_fallback=used_fallback,
    )
```

src/lms_llmsTxt/reasoning.py
```
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

_REASONING_BLOCK_RE = re.compile(r"<(think|analysis|reasoning)>.*?</\1>", re.IGNORECASE | re.DOTALL)
_REASONING_PREFIX_RE = re.compile(
    r"^(?:Reasoning|Analysis|Chain of thought|Thinking):.*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(slots=True)
class CanonicalResponse:
    final_text: str
    reasoning_text: str | None = None
    provider_hint: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalResponse":
        return cls(
            final_text=str(data.get("final_text", "")),
            reasoning_text=data.get("reasoning_text"),
            provider_hint=data.get("provider_hint"),
            raw_metadata=dict(data.get("raw_metadata") or {}),
        )


@dataclass(slots=True)
class SanitizedOutput:
    text: str
    extracted_reasoning: str | None = None
    was_modified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SanitizedOutput":
        return cls(
            text=str(data.get("text", "")),
            extracted_reasoning=data.get("extracted_reasoning"),
            was_modified=bool(data.get("was_modified", False)),
        )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def canonicalize_response(raw_output: Any, provider_hint: str | None = None) -> CanonicalResponse:
    final_text = ""
    reasoning_text = None

    if isinstance(raw_output, dict):
        final_text = _as_text(
            raw_output.get("final_text")
            or raw_output.get("llms_txt_content")
            or raw_output.get("content")
            or raw_output.get("answer")
        )
        reasoning_text = _as_text(
            raw_output.get("reasoning_text")
            or raw_output.get("reasoning_content")
            or raw_output.get("thinking")
            or raw_output.get("analysis")
        ) or None
    elif isinstance(raw_output, str):
        final_text = raw_output
    else:
        final_text = _as_text(getattr(raw_output, "final_text", None) or getattr(raw_output, "llms_txt_content", None) or getattr(raw_output, "content", None) or getattr(raw_output, "answer", None))
        reasoning_text = _as_text(
            getattr(raw_output, "reasoning_text", None)
            or getattr(raw_output, "reasoning_content", None)
            or getattr(raw_output, "thinking", None)
            or getattr(raw_output, "analysis", None)
        ) or None

    if not final_text and reasoning_text:
        final_text = reasoning_text

    return CanonicalResponse(
        final_text=final_text,
        reasoning_text=reasoning_text,
        provider_hint=provider_hint,
        raw_metadata={"raw_type": type(raw_output).__name__},
    )


def sanitize_final_output(text: str, strict: bool = True) -> SanitizedOutput:
    src = text or ""
    extracted: list[str] = []

    def _extract_block(match: re.Match[str]) -> str:
        extracted.append(match.group(0))
        return ""

    cleaned = _REASONING_BLOCK_RE.sub(_extract_block, src)

    if strict:
        prefix_matches = _REASONING_PREFIX_RE.findall(cleaned)
        if prefix_matches:
            extracted.extend(prefix_matches)
        cleaned = _REASONING_PREFIX_RE.sub("", cleaned)

    # Normalize extra blank lines introduced by stripping wrappers.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    return SanitizedOutput(
        text=cleaned,
        extracted_reasoning="\n\n".join(extracted).strip() or None,
        was_modified=(cleaned != src.strip()),
    )
```

src/lms_llmsTxt/repo_digest.py
```
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Iterable

from .models import RepositoryMaterial


@dataclass(slots=True)
class RepoChunk:
    path: str
    content: str
    start_line: int = 1
    end_line: int = 1


@dataclass(slots=True)
class ChunkCapsule:
    chunk_id: str
    path: str
    chunk_type: str
    summary: str
    key_symbols: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RepoDigest:
    topic: str
    architecture_summary: str
    primary_language: str
    subsystems: list[dict]
    key_dependencies: list[str]
    entry_points: list[str]
    test_coverage_hint: str
    digest_id: str


def _language_from_path(path: str) -> str:
    if path.endswith(".py"):
        return "python"
    if path.endswith(".ts") or path.endswith(".tsx"):
        return "typescript"
    if path.endswith(".js"):
        return "javascript"
    if path.endswith(".rs"):
        return "rust"
    return "unknown"


def _chunk_type(path: str) -> str:
    low = path.lower()
    if "/test" in low or "test_" in low or low.endswith("_test.py"):
        return "test"
    if low.endswith((".md", ".rst", ".txt")):
        return "doc"
    if low.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
        return "config"
    return "code"


def _extract_symbols(content: str) -> list[str]:
    symbols = set(re.findall(r"(?:def|class|function|const|let|var|pub\\s+fn)\\s+([A-Za-z_][A-Za-z0-9_]*)", content))
    return sorted(symbols)[:10]


def _extract_dependencies(content: str) -> list[str]:
    deps = set(re.findall(r"(?:import|from|require|use)\\s+([A-Za-z0-9_./:@-]+)", content))
    return sorted(deps)[:20]


def _summarize(content: str, max_chars: int = 180) -> str:
    flat = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(flat) <= max_chars:
        return flat
    return flat[:max_chars] + "..."


def chunk_repository_material(material: RepositoryMaterial) -> list[RepoChunk]:
    chunks: list[RepoChunk] = []
    for path in sorted(p for p in material.file_tree.splitlines() if p.strip()):
        chunks.append(RepoChunk(path=path, content=path, start_line=1, end_line=1))
    if material.readme_content:
        end_line = max(1, material.readme_content.count("\n") + 1)
        chunks.append(RepoChunk(path="README.md", content=material.readme_content, end_line=end_line))
    if material.package_files:
        end_line = max(1, material.package_files.count("\n") + 1)
        chunks.append(RepoChunk(path="package_files.txt", content=material.package_files, end_line=end_line))
    return chunks


def extract_chunk_capsules(chunks: Iterable[RepoChunk]) -> list[ChunkCapsule]:
    capsules: list[ChunkCapsule] = []
    for chunk in chunks:
        raw_id = f"{chunk.path}:{chunk.start_line}:{chunk.end_line}"
        capsule = ChunkCapsule(
            chunk_id=hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16],
            path=chunk.path,
            chunk_type=_chunk_type(chunk.path),
            summary=_summarize(chunk.content),
            key_symbols=_extract_symbols(chunk.content),
            dependencies=_extract_dependencies(chunk.content),
        )
        capsules.append(capsule)
    return capsules


def reduce_capsules(capsules: list[ChunkCapsule], topic: str = "Repository") -> RepoDigest:
    if not capsules:
        return RepoDigest(
            topic=topic,
            architecture_summary="No repository content available.",
            primary_language="unknown",
            subsystems=[],
            key_dependencies=[],
            entry_points=[],
            test_coverage_hint="no_tests_detected",
            digest_id="empty",
        )

    by_subsystem: dict[str, list[ChunkCapsule]] = {}
    lang_counter: dict[str, int] = {}
    all_deps: set[str] = set()
    entry_points: list[str] = []

    for cap in capsules:
        parts = cap.path.split("/")
        subsystem = "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "root")
        by_subsystem.setdefault(subsystem, []).append(cap)

        lang = _language_from_path(cap.path)
        lang_counter[lang] = lang_counter.get(lang, 0) + 1

        all_deps.update(cap.dependencies)

        lower = cap.path.lower()
        if any(token in lower for token in ("main.py", "__main__.py", "index.ts", "index.js", "cli.py", "/cmd/", "/bin/", "app.py")):
            entry_points.append(cap.path)

    primary_language = max(lang_counter.items(), key=lambda kv: kv[1])[0] if lang_counter else "unknown"

    subsystems: list[dict] = []
    for name, values in sorted(by_subsystem.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        paths = sorted({v.path for v in values})[:20]
        symbols = sorted({s for v in values for s in v.key_symbols})[:20]
        summary = _summarize(" ".join(v.summary for v in values), max_chars=280)
        subsystems.append({"name": name, "paths": paths, "summary": summary, "key_symbols": symbols})

    test_hint = "has_tests" if any(c.chunk_type == "test" for c in capsules) else "no_tests_detected"
    architecture_summary = _summarize(
        " ".join(f"{sub['name']}: {sub['summary']}" for sub in subsystems[:5]),
        max_chars=500,
    )

    digest_key = "|".join(sorted(c.chunk_id for c in capsules))
    digest_id = hashlib.sha256(digest_key.encode("utf-8")).hexdigest()[:16]

    return RepoDigest(
        topic=topic,
        architecture_summary=architecture_summary,
        primary_language=primary_language,
        subsystems=subsystems,
        key_dependencies=sorted(all_deps)[:40],
        entry_points=sorted(set(entry_points))[:20],
        test_coverage_hint=test_hint,
        digest_id=digest_id,
    )


def build_repo_digest(material: RepositoryMaterial, topic: str = "Repository") -> RepoDigest:
    chunks = chunk_repository_material(material)
    capsules = extract_chunk_capsules(chunks)
    return reduce_capsules(capsules, topic=topic)
```

src/lms_llmsTxt/retry_policy.py
```
from __future__ import annotations

from dataclasses import replace
from enum import Enum

from .context_budget import ContextBudget


class ErrorClass(str, Enum):
    CONTEXT_LENGTH = "context_length"
    PAYLOAD_LIMIT = "payload_limit"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


_CONTEXT_PATTERNS = (
    "context_length_exceeded",
    "maximum context",
    "context window",
    "too many tokens",
    "input too long",
)
_PAYLOAD_PATTERNS = (
    "413",
    "payload too large",
    "request entity too large",
)
_RATE_LIMIT_PATTERNS = (
    "429",
    "rate limit",
    "too many requests",
)


def classify_generation_error(exc: Exception) -> ErrorClass:
    msg = str(exc).lower()
    if any(token in msg for token in _CONTEXT_PATTERNS):
        return ErrorClass.CONTEXT_LENGTH
    if any(token in msg for token in _PAYLOAD_PATTERNS):
        return ErrorClass.PAYLOAD_LIMIT
    if any(token in msg for token in _RATE_LIMIT_PATTERNS):
        return ErrorClass.RATE_LIMIT
    return ErrorClass.UNKNOWN


def next_retry_budget(
    previous_budget: ContextBudget,
    step: int,
    reduction_steps: tuple[float, ...] | list[float] = (0.70, 0.50),
) -> ContextBudget | None:
    if step >= len(reduction_steps):
        return None
    ratio = float(reduction_steps[step])
    if ratio <= 0 or ratio >= 1:
        return None

    next_components = {
        k: max(1, int(v * ratio)) if v > 0 else 0
        for k, v in previous_budget.component_estimates.items()
    }
    return replace(
        previous_budget,
        max_context_tokens=max(1, int(previous_budget.max_context_tokens * ratio)),
        estimated_prompt_tokens=max(1, int(previous_budget.estimated_prompt_tokens * ratio)),
        available_tokens=max(1, int(previous_budget.available_tokens * ratio)),
        component_estimates=next_components,
    )
```

src/lms_llmsTxt/schema.py
```
from __future__ import annotations

LLMS_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "llmsTxtDocument",
    "type": "object",
    "required": ["project", "remember", "sections"],
    "properties": {
        "project": {
            "type": "object",
            "required": ["name", "summary"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "summary": {"type": "string", "minLength": 1},
            },
        },
        "remember": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "sections": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "links"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "url", "note"],
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string", "format": "uri"},
                                "note": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}


__all__ = ["LLMS_JSON_SCHEMA"]
```

src/lms_llmsTxt/signatures.py
```
from __future__ import annotations

from typing import List

try:
    import dspy
except ImportError:
    class MockDSPy:
        class Signature:
            pass
        class Module:
            pass
        class ChainOfThought:
            def __init__(self, signature): pass
            def __call__(self, **kwargs): return MockDSPy.Prediction()
        class Predict:
            def __init__(self, signature): pass
            def __call__(self, **kwargs): return MockDSPy.Prediction()
        class Prediction:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        class LM:
            def __init__(self, *args, **kwargs): pass

        class InputField:
            def __init__(self, *args, **kwargs): pass
        
        class OutputField:
            def __init__(self, *args, **kwargs): pass
            
        @staticmethod
        def configure(**kwargs):
            pass

    dspy = MockDSPy()


class AnalyzeRepository(dspy.Signature):
    """Summarize a repository's purpose and concepts."""

    repo_url: str = dspy.InputField(desc="GitHub repository URL")
    file_tree: str = dspy.InputField(desc="Repository file structure (one path per line)")
    readme_content: str = dspy.InputField(desc="README.md content (raw)")

    project_purpose: str = dspy.OutputField(
        desc="Main purpose and goals of the project (2–4 sentences)"
    )
    key_concepts: List[str] = dspy.OutputField(
        desc="Important concepts and terminology (bullet list items)"
    )
    architecture_overview: str = dspy.OutputField(
        desc="High-level architecture overview (1–2 paragraphs)"
    )


class AnalyzeCodeStructure(dspy.Signature):
    """Identify important directories, entry points, and development insights."""

    file_tree: str = dspy.InputField()
    package_files: str = dspy.InputField(
        desc="Concatenated contents of pyproject/requirements/package.json files."
    )

    important_directories: List[str] = dspy.OutputField(
        desc="Key directories with brief notes (e.g., src/, docs/, examples/)"
    )
    entry_points: List[str] = dspy.OutputField(
        desc="Likely entry points or commands (e.g., cli.py, main.ts, npm scripts)"
    )
    development_info: str = dspy.OutputField(
        desc="Development or build info (dependencies, scripts, tooling)"
    )


class GenerateUsageExamples(dspy.Signature):
    """Produce a short section of common usage examples based on the repo analysis."""

    repo_info: str = dspy.InputField(
        desc="Summary of the project's purpose and key concepts"
    )
    usage_examples: str = dspy.OutputField(
        desc="Markdown examples (code fences) showing typical usage"
    )


class GenerateLLMsTxt(dspy.Signature):
    """Generate a complete llms.txt (markdown index) for the project."""

    project_purpose: str = dspy.InputField()
    key_concepts: List[str] = dspy.InputField()
    architecture_overview: str = dspy.InputField()
    important_directories: List[str] = dspy.InputField()
    entry_points: List[str] = dspy.InputField()
    development_info: str = dspy.InputField()
    usage_examples: str = dspy.InputField(
        desc="Common usage patterns and examples (markdown)"
    )

    llms_txt_content: str = dspy.OutputField(
        desc="Complete llms.txt content following the standard format"
    )


class AnalyzeRepositoryFromDigest(dspy.Signature):
    """Generate project summary from a reduced repository digest."""

    digest_summary: str = dspy.InputField(desc="Compact digest of repository structure")
    repo_url: str = dspy.InputField(desc="GitHub repository URL")

    project_purpose: str = dspy.OutputField(desc="Purpose summary in 1-3 sentences")
    key_concepts: List[str] = dspy.OutputField(desc="Key concepts as list")
    architecture_overview: str = dspy.OutputField(desc="Architecture overview paragraph")
```

src/lms_llmsTxt_mcp/__init__.py
```
# lms_llmsTxt_mcp package
```

src/lms_llmsTxt_mcp/artifacts.py
```
from pathlib import Path
from .config import settings
from .runs import RunStore
from .hashing import read_text_preview

def _status_message(status: str, error_message: str | None) -> str:
    if status in ("pending", "processing"):
        return "Processing..."
    if status == "failed":
        return f"Failed: {error_message or 'Unknown error'}"
    return ""

def resource_uri(run_id: str, artifact_name: str) -> str:
    """Generates a standardized URI for a run artifact."""
    return f"lmstxt://runs/{run_id}/{artifact_name}"

def artifact_resource_uri(relative_path: str) -> str:
    """Generates a standardized URI for a persistent artifact on disk."""
    return f"lmstxt://artifacts/{relative_path}"

def read_resource_text(run_store: RunStore, run_id: str, artifact_name: str) -> str:
    """
    Reads text content from an artifact, truncated if necessary.
    Returns the content string (with truncation footer if applied).
    """
    run = run_store.get_run(run_id)
    if run.status != "completed":
        return _status_message(run.status, run.error_message)
    # Find artifact by name
    artifact = next((a for a in run.artifacts if a.name == artifact_name), None)
    if not artifact:
        raise ValueError(f"Artifact {artifact_name} not found in run {run_id}")
    
    # Read content using hashing utility
    content, truncated = read_text_preview(
        Path(artifact.path), 
        settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS
    )
    
    if truncated:
        content += "\n... (content truncated)"
        
    return content

def read_artifact_chunk(run_store: RunStore, run_id: str, artifact_name: str, offset: int, limit: int) -> str:
    """
    Reads a specific chunk of an artifact file.
    Returns the content string.
    """
    run = run_store.get_run(run_id)
    if run.status != "completed":
        return _status_message(run.status, run.error_message)
    artifact = next((a for a in run.artifacts if a.name == artifact_name), None)
    if not artifact:
        raise ValueError(f"Artifact {artifact_name} not found in run {run_id}")
    
    path = Path(artifact.path)
    if not path.exists():
        raise FileNotFoundError(f"Artifact file not found at {path}")
        
    try:
        # Check size first to avoid unnecessary opens if offset is out of bounds
        file_size = path.stat().st_size
        if offset >= file_size:
            return ""
            
        with open(path, "r", encoding="utf-8") as f:
            f.seek(offset)
            return f.read(limit)
    except UnicodeDecodeError:
        return "<Binary or non-UTF-8 content>"

def scan_artifacts() -> list[Path]:
    """
    Scans the allowed root directory for all .txt artifact files.
    Returns a list of Path objects relative to the allowed root.
    """
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    
    # Return relative paths so the API consumer gets "org/repo/llms.txt"
    # rglob finds all .txt files recursively
    return sorted([
        p.relative_to(root) 
        for p in root.rglob("*.txt") 
        if p.is_file()
    ])
```

src/lms_llmsTxt_mcp/config.py
```
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    LLMSTXT_MCP_ALLOWED_ROOT: Path = Path("./artifacts")
    LLMSTXT_MCP_RESOURCE_MAX_CHARS: int = 100000
    LLMSTXT_MCP_RUN_TTL_SECONDS: int = 60 * 60 * 24
    LLMSTXT_MCP_RUN_CLEANUP_INTERVAL_SECONDS: int = 300
    LLMSTXT_MCP_RUN_MAX: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
```

src/lms_llmsTxt_mcp/errors.py
```
class OutputDirNotAllowedError(Exception):
    """Raised when the output directory is not allowed."""
    pass

class LMStudioUnavailableError(Exception):
    """Raised when LM Studio is not available."""
    pass

class UnknownRunError(Exception):
    """Raised when a requested run ID is not found."""
    pass
```

src/lms_llmsTxt_mcp/generator.py
```
import threading
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple

from lms_llmsTxt.pipeline import run_generation
from lms_llmsTxt.full_builder import build_llms_full_from_repo, iter_llms_links
from lms_llmsTxt.github import gather_repository_material, owner_repo_from_url
from lms_llmsTxt import LMStudioConnectivityError, AppConfig
from lms_llmsTxt.models import GenerationArtifacts

from .errors import LMStudioUnavailableError, OutputDirNotAllowedError
from .models import RunRecord, ArtifactRef
from .runs import RunStore
from .hashing import sha256_file
from .security import validate_output_dir

_lock = threading.Lock()
logger = logging.getLogger(__name__)

def _base_name_from_llms_path(path: Path) -> str:
    name = path.name
    suffix = "-llms.txt"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return path.stem


def _find_artifact(run: RunRecord, name: str) -> Optional[ArtifactRef]:
    return next((a for a in run.artifacts if a.name == name), None)


def _upsert_artifact_list(artifacts: list[ArtifactRef], ref: ArtifactRef) -> None:
    for idx, existing in enumerate(artifacts):
        if existing.name == ref.name:
            artifacts[idx] = ref
            return
    artifacts.append(ref)


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _artifact_ref_from_path(name: str, path: Path) -> Optional[ArtifactRef]:
    if not path.exists():
        return None
    return ArtifactRef(
        name=name,
        path=str(path.absolute()),
        size_bytes=path.stat().st_size,
        hash_sha256=sha256_file(path),
    )


def _repo_root_from_url(output_dir: Path, repo_url: str) -> Path:
    owner, repo = owner_repo_from_url(repo_url)
    return output_dir / owner / repo


def _artifact_path_from_url(output_dir: Path, repo_url: str, artifact_name: str) -> Path:
    _, repo = owner_repo_from_url(repo_url)
    base_name = repo.lower().replace(" ", "-")
    repo_root = _repo_root_from_url(output_dir, repo_url)
    suffix_map = {
        "llms.txt": "llms.txt",
        "llms-full.txt": "llms-full.txt",
        "llms-ctx.txt": "llms-ctx.txt",
        "llms.json": "llms.json",
    }
    suffix = suffix_map.get(artifact_name, artifact_name)
    return repo_root / f"{base_name}-{suffix}"


def _resolve_llms_txt_path(
    run_store: RunStore,
    run_id: str,
    repo_url: Optional[str],
    output_dir: Path,
) -> Tuple[Path, RunRecord]:
    run = run_store.get_run(run_id)
    llms_artifact = _find_artifact(run, "llms.txt")
    if llms_artifact:
        return Path(llms_artifact.path), run

    if not repo_url:
        raise ValueError("repo_url is required when llms.txt is not present in the run")

    llms_path = _artifact_path_from_url(output_dir, repo_url, "llms.txt")
    return llms_path, run


def _ensure_llms_txt(
    repo_url: str,
    output_dir: Path,
    *,
    cache_lm: bool = False,
) -> Path:
    llms_path = _artifact_path_from_url(output_dir, repo_url, "llms.txt")
    if llms_path.exists():
        return llms_path

    logger.info("llms.txt missing; generating now for %s", repo_url)
    config = AppConfig(output_dir=output_dir)
    artifacts = run_generation(
        repo_url=repo_url,
        config=config,
        cache_lm=cache_lm,
        build_full=False,
        build_ctx=False,
    )
    generated_path = Path(artifacts.llms_txt_path)
    if not generated_path.exists():
        raise FileNotFoundError(f"llms.txt not found after generation at {generated_path}")
    return generated_path


def safe_generate_llms_txt(
    run_store: RunStore,
    run_id: Optional[str],
    url: str,
    output_dir: str = "./artifacts",
    cache_lm: bool = True,
) -> RunRecord:
    """
    Thread-safe wrapper around run_generation that only writes llms.txt (+ optional llms.json).
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)
    logger.info("Generating llms.txt for %s (run_id=%s)", url, run_id)

    # Security: Validate output directory before use
    try:
        validated_dir = validate_output_dir(Path(output_dir))
    except OutputDirNotAllowedError as e:
        logger.error("Security violation: %s", e)
        run_store.update_run(run_id, status="failed", error_message=str(e))
        raise

    # Construct AppConfig from arguments
    config = AppConfig(output_dir=validated_dir)

    with _lock:
        try:
            # Call run_generation with correct signature
            artifacts: GenerationArtifacts = run_generation(
                repo_url=url,
                config=config,
                cache_lm=cache_lm,
                build_full=False,
                build_ctx=False,
            )

            # Process artifacts into our domain model
            refs: list[ArtifactRef] = []

            # Helper to add artifact
            def add_artifact(path_str: str | None, name: str) -> None:
                if not path_str:
                    return
                p = Path(path_str)
                if p.exists():
                    refs.append(ArtifactRef(
                        name=name,
                        path=str(p.absolute()),
                        size_bytes=p.stat().st_size,
                        hash_sha256=sha256_file(p)
                    ))

            add_artifact(artifacts.llms_txt_path, "llms.txt")
            add_artifact(artifacts.json_path, "llms.json")

            result = run_store.update_run(
                run_id,
                status="completed",
                artifacts=refs,
                error_message=None,
            )
            logger.info("llms.txt generation complete (run_id=%s)", run_id)
            return result

        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e

        except Exception as e:
            logger.error("Unexpected error during generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e


def safe_generate_llms_full(
    run_store: RunStore,
    run_id: Optional[str],
    repo_url: Optional[str],
    output_dir: str = "./artifacts",
) -> RunRecord:
    """
    Build llms-full.txt from an existing llms.txt artifact referenced by run_id,
    or resolve llms.txt by repo_url + output_dir if run_id is omitted.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)

    with _lock:
        try:
            logger.info("Starting llms-full generation (run_id=%s, repo_url=%s)", run_id, repo_url)
            logger.info("Resolving llms.txt via run_id %s", run_id)
            llms_path, run = _resolve_llms_txt_path(
                run_store=run_store,
                run_id=run_id,
                repo_url=repo_url,
                output_dir=Path(output_dir),
            )

            output_root = llms_path.parent.parents[1] if llms_path.exists() else Path(output_dir)
            validated_dir = validate_output_dir(output_root)

            if not llms_path.exists():
                if not repo_url:
                    raise ValueError("repo_url is required to generate llms.txt")
                llms_path = _ensure_llms_txt(repo_url, validated_dir)

            llms_ref = _artifact_ref_from_path("llms.txt", llms_path)
            if not llms_ref:
                raise FileNotFoundError(f"llms.txt not found at {llms_path}")

            llms_text = llms_path.read_text(encoding="utf-8")
            repo_root = llms_path.parent
            config = AppConfig(output_dir=validated_dir)

            if not repo_url:
                raise ValueError("repo_url is required to generate llms-full.txt")
            material = gather_repository_material(repo_url, config.github_token)
            link_count = sum(1 for _ in iter_llms_links(llms_text))
            logger.info("Building llms-full from %s curated links", link_count)
            llms_full_text = build_llms_full_from_repo(
                llms_text,
                prefer_raw=not material.is_private,
                default_ref=material.default_branch,
                token=config.github_token,
                link_style=config.link_style,
            )

            base_name = _base_name_from_llms_path(llms_path)
            llms_full_path = repo_root / f"{base_name}-llms-full.txt"
            _write_text(llms_full_path, llms_full_text)
            logger.info("Wrote llms-full.txt to %s", llms_full_path)

            ref = ArtifactRef(
                name="llms-full.txt",
                path=str(llms_full_path.absolute()),
                size_bytes=llms_full_path.stat().st_size,
                hash_sha256=sha256_file(llms_full_path),
            )

            updated_artifacts = list(run.artifacts)
            _upsert_artifact_list(updated_artifacts, llms_ref)
            _upsert_artifact_list(updated_artifacts, ref)

            updated = run_store.update_run(
                run_id,
                status="completed",
                artifacts=updated_artifacts,
                error_message=None,
            )
            logger.info("llms-full generation complete (run_id=%s)", run_id)
            return updated
        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e
        except Exception as e:
            logger.exception("Unexpected error during llms-full generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e


def safe_generate_llms_ctx(
    run_store: RunStore,
    run_id: Optional[str],
    repo_url: Optional[str] = None,
    output_dir: str = "./artifacts",
) -> RunRecord:
    """
    Build llms-ctx.txt from an existing llms.txt artifact referenced by run_id,
    or resolve llms.txt by repo_url + output_dir if run_id is omitted.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)

    with _lock:
        try:
            logger.info("Starting llms-ctx generation (run_id=%s, repo_url=%s)", run_id, repo_url)
            logger.info("Resolving llms.txt via run_id %s", run_id)
            llms_path, run = _resolve_llms_txt_path(
                run_store=run_store,
                run_id=run_id,
                repo_url=repo_url,
                output_dir=Path(output_dir),
            )
            output_root = llms_path.parent.parents[1] if llms_path.exists() else Path(output_dir)
            validated_dir = validate_output_dir(output_root)

            if not llms_path.exists():
                if not repo_url:
                    raise ValueError("repo_url is required to generate llms.txt")
                llms_path = _ensure_llms_txt(repo_url, validated_dir)

            llms_ref = _artifact_ref_from_path("llms.txt", llms_path)
            if not llms_ref:
                raise FileNotFoundError(f"llms.txt not found at {llms_path}")
            llms_text = llms_path.read_text(encoding="utf-8")

            try:
                from llms_txt import create_ctx  # type: ignore
            except ImportError as exc:
                raise RuntimeError("llms_txt is not installed; cannot generate llms-ctx.txt") from exc

            ctx_text = create_ctx(llms_text, optional=False)
            repo_root = llms_path.parent
            base_name = _base_name_from_llms_path(llms_path)
            ctx_path = repo_root / f"{base_name}-llms-ctx.txt"
            _write_text(ctx_path, ctx_text)
            logger.info("Wrote llms-ctx.txt to %s", ctx_path)

            ref = ArtifactRef(
                name="llms-ctx.txt",
                path=str(ctx_path.absolute()),
                size_bytes=ctx_path.stat().st_size,
                hash_sha256=sha256_file(ctx_path),
            )
            updated_artifacts = list(run.artifacts)
            _upsert_artifact_list(updated_artifacts, llms_ref)
            _upsert_artifact_list(updated_artifacts, ref)
            updated = run_store.update_run(
                run_id,
                status="completed",
                artifacts=updated_artifacts,
                error_message=None,
            )
            logger.info("llms-ctx generation complete (run_id=%s)", run_id)
            return updated
        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e
        except Exception as e:
            logger.exception("Unexpected error during llms-ctx generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e
```

src/lms_llmsTxt_mcp/graph_resources.py
```
from __future__ import annotations

import re
from pathlib import Path

from .config import settings

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def graph_resource_uri(relative_path: str) -> str:
    return f"lmstxt://graphs/{relative_path}"


def repo_graph_node_uri(repo_id: str, node_id: str) -> str:
    return f"repo://{repo_id}/graph/nodes/{node_id}"


def scan_graph_artifacts() -> list[Path]:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    results: list[Path] = []
    for pattern in ("**/repo.graph.json", "**/repo.force.json", "**/nodes/*.md"):
        for path in root.glob(pattern):
            if path.is_file():
                results.append(path.relative_to(root))
    return sorted(results)


def _iter_repo_graph_roots() -> list[tuple[str, str, Path]]:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    if not root.exists():
        return []
    results: list[tuple[str, str, Path]] = []
    for graph_file in root.glob("**/graph/repo.graph.json"):
        rel = graph_file.relative_to(root)
        parts = rel.parts
        if len(parts) < 4 or parts[-2] != "graph" or parts[-1] != "repo.graph.json":
            continue
        owner = parts[-4]
        repo = parts[-3]
        repo_root = root / owner / repo / "graph"
        results.append((owner, repo, repo_root))
    return results


def _repo_id_aliases(owner: str, repo: str) -> set[str]:
    return {
        f"{owner}--{repo}",
        f"{owner}/{repo}",
        f"{owner}__{repo}",
    }


def resolve_repo_node_path(repo_id: str, node_id: str) -> Path:
    if not _SAFE_SEGMENT.fullmatch(node_id):
        raise ValueError(f"Invalid node id: {node_id}")
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    for owner, repo, repo_root in _iter_repo_graph_roots():
        if repo_id not in _repo_id_aliases(owner, repo):
            continue
        node_path = repo_root / "nodes" / f"{node_id}.md"
        if node_path.is_file():
            return node_path.relative_to(root)
    raise FileNotFoundError(f"Graph node not found: repo_id={repo_id}, node_id={node_id}")


def read_graph_artifact_chunk(relative_path: str, offset: int, limit: int) -> str:
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    path = root / relative_path
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Graph artifact not found: {relative_path}")
    if offset < 0:
        offset = 0
    if limit <= 0:
        return ""
    with path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        return handle.read(limit)


def read_repo_node_chunk(repo_id: str, node_id: str, offset: int, limit: int) -> str:
    path = resolve_repo_node_path(repo_id=repo_id, node_id=node_id)
    return read_graph_artifact_chunk(str(path), offset, limit)
```

src/lms_llmsTxt_mcp/hashing.py
```
import hashlib
from pathlib import Path

def sha256_file(path: Path) -> str:
    """Calculates the SHA256 hash of a file efficiently."""
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        # Read in 4KB chunks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def read_text_preview(path: Path, max_chars: int) -> tuple[str, bool]:
    """
    Reads up to max_chars from a text file.
    Returns (content, is_truncated).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(max_chars + 1)
            if len(content) > max_chars:
                return content[:max_chars], True
            return content, False
    except UnicodeDecodeError:
        # Handle cases where the file isn't valid UTF-8
        return "<Binary or non-UTF-8 content>", True
```

src/lms_llmsTxt_mcp/models.py
```
from datetime import datetime, timezone
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

ArtifactName = Literal[
    "llms.txt",
    "llms-full.txt",
    "llms-ctx.txt",
    "llms.json",
    "repo.graph.json",
    "repo.force.json",
]
RunStatus = Literal["pending", "processing", "completed", "failed"]

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ArtifactRef(BaseModel):
    name: ArtifactName
    path: str
    size_bytes: int
    hash_sha256: str

class RunRecord(BaseModel):
    run_id: str
    status: RunStatus
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

class GenerateResult(RunRecord):
    """Legacy name preserved for compatibility with existing tool outputs."""

class ReadArtifactResult(BaseModel):
    content: str
    truncated: bool
    total_chars: int

class ArtifactMetadata(BaseModel):
    filename: str
    size_bytes: int
    last_modified: datetime
    uri: str
```

src/lms_llmsTxt_mcp/runs.py
```
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from threading import Lock, Thread
from .models import RunRecord
from .errors import UnknownRunError

logger = logging.getLogger(__name__)

class RunStore:
    def __init__(
        self,
        max_runs: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        cleanup_interval_seconds: Optional[int] = None,
    ):
        self._runs: Dict[str, RunRecord] = {}
        self._lock = Lock()
        self._max_runs = max_runs if max_runs and max_runs > 0 else None
        self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
        self._cleanup_interval_seconds = (
            cleanup_interval_seconds if cleanup_interval_seconds and cleanup_interval_seconds > 0 else None
        )
        self._cleanup_thread: Optional[Thread] = None

    def put_run(self, run_record: RunRecord) -> None:
        with self._lock:
            self._runs[run_record.run_id] = run_record
            self._prune_locked()

    def update_run(self, run_id: str, **updates: object) -> RunRecord:
        with self._lock:
            if run_id not in self._runs:
                raise UnknownRunError(f"Run ID {run_id} not found")
            existing = self._runs[run_id]
            updates.pop("run_id", None)
            updated = existing.model_copy(
                update={**updates, "updated_at": datetime.now(timezone.utc)}
            )
            self._runs[run_id] = updated
            self._prune_locked()
            return updated

    def get_run(self, run_id: str) -> RunRecord:
        with self._lock:
            if run_id not in self._runs:
                raise UnknownRunError(f"Run ID {run_id} not found")
            return self._runs[run_id]

    def list_runs(self, limit: int = 10) -> List[RunRecord]:
        with self._lock:
            all_runs = list(self._runs.values())
            # Return newest first based on updated timestamp
            all_runs.sort(key=lambda run: run.updated_at, reverse=True)
            return all_runs[:limit]

    def prune_expired(self) -> int:
        now = datetime.now(timezone.utc)
        with self._lock:
            return self._prune_locked(now=now)

    def start_cleanup_worker(self) -> None:
        if not self._ttl_seconds or not self._cleanup_interval_seconds:
            return
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        def _loop() -> None:
            while True:
                time.sleep(self._cleanup_interval_seconds)
                try:
                    removed = self.prune_expired()
                    if removed:
                        logger.info("Pruned %s expired run(s)", removed)
                except Exception:
                    logger.exception("Run cleanup failed")

        self._cleanup_thread = Thread(target=_loop, daemon=True)
        self._cleanup_thread.start()

    def _prune_locked(self, now: Optional[datetime] = None) -> int:
        removed = 0
        if not now:
            now = datetime.now(timezone.utc)

        if self._ttl_seconds:
            cutoff = now - timedelta(seconds=self._ttl_seconds)
            for run_id, run in list(self._runs.items()):
                if run.status in ("completed", "failed") and run.updated_at < cutoff:
                    del self._runs[run_id]
                    removed += 1

        if self._max_runs and len(self._runs) > self._max_runs:
            candidates = sorted(
                ((run_id, run) for run_id, run in self._runs.items() if run.status in ("completed", "failed")),
                key=lambda item: item[1].updated_at,
            )
            for run_id, _run in candidates:
                if len(self._runs) <= self._max_runs:
                    break
                del self._runs[run_id]
                removed += 1

        return removed
```

src/lms_llmsTxt_mcp/security.py
```
from pathlib import Path
from .config import settings
from .errors import OutputDirNotAllowedError

def validate_output_dir(path: Path) -> Path:
    """
    Validates that the path is within the allowed root.
    Returns the resolved absolute path.
    """
    try:
        # Resolve both paths to absolute
        resolved_path = path.resolve()
        # Ensure allowed root exists or at least resolves fully
        allowed_root = settings.LLMSTXT_MCP_ALLOWED_ROOT.resolve()
        
        # Check containment
        if not resolved_path.is_relative_to(allowed_root):
            raise OutputDirNotAllowedError(f"Path {path} is not within allowed root {allowed_root}")
            
        return resolved_path
    except (ValueError, RuntimeError) as e:
        raise OutputDirNotAllowedError(f"Invalid path: {e}")
```

src/lms_llmsTxt_mcp/server.py
```
import json
import logging
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .config import settings
from .models import ReadArtifactResult, ArtifactName, RunRecord, ArtifactMetadata
from .runs import RunStore
from .generator import (
    safe_generate_llms_txt,
    safe_generate_llms_full,
    safe_generate_llms_ctx,
)
from .artifacts import (
    read_resource_text, 
    read_artifact_chunk, 
    scan_artifacts, 
    artifact_resource_uri
)
from .security import validate_output_dir
from .hashing import read_text_preview
from .graph_resources import (
    graph_resource_uri,
    read_graph_artifact_chunk,
    read_repo_node_chunk,
    repo_graph_node_uri,
    scan_graph_artifacts,
)
from lms_llmsTxt.github import owner_repo_from_url

# Configure logging to stderr to avoid interfering with JSON-RPC on stdout
logging.basicConfig(
    stream=sys.stderr, 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("lms-llmsTxt")

# Initialize RunStore (singleton for the server instance)
run_store = RunStore(
    max_runs=settings.LLMSTXT_MCP_RUN_MAX,
    ttl_seconds=settings.LLMSTXT_MCP_RUN_TTL_SECONDS,
    cleanup_interval_seconds=settings.LLMSTXT_MCP_RUN_CLEANUP_INTERVAL_SECONDS,
)
run_store.start_cleanup_worker()

def _spawn_background(target, *args, **kwargs) -> None: 
    def _runner() -> None: 
        try:
            target(*args, **kwargs)
        except Exception:
            logger.exception("Background job failed")

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

def _start_run(run_id: str | None) -> str:
    if run_id:
        run_store.get_run(run_id)
        run_store.update_run(run_id, status="processing", error_message=None)
        return run_id
    new_run_id = str(uuid.uuid4())
    run_store.put_run(RunRecord(run_id=new_run_id, status="processing"))
    return new_run_id


def _artifact_path_from_url(output_dir: Path, repo_url: str, artifact_name: str) -> Path:
    owner, repo = owner_repo_from_url(repo_url)
    base_name = repo.lower().replace(" ", "-")
    repo_root = output_dir / owner / repo
    if artifact_name == "repo.graph.json":
        return repo_root / "graph" / "repo.graph.json"
    if artifact_name == "repo.force.json":
        return repo_root / "graph" / "repo.force.json"
    suffix_map = {
        "llms.txt": "llms.txt",
        "llms-full.txt": "llms-full.txt",
        "llms-ctx.txt": "llms-ctx.txt",
        "llms.json": "llms.json",
    }
    suffix = suffix_map.get(artifact_name, artifact_name)
    return repo_root / f"{base_name}-{suffix}"


def _read_file_chunk(path: Path, offset: int, limit: int) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Artifact file not found at {path}")
    try:
        file_size = path.stat().st_size
        if offset >= file_size:
            return ""
        with open(path, "r", encoding="utf-8") as f:
            f.seek(offset)
            return f.read(limit)
    except UnicodeDecodeError:
        return "<Binary or non-UTF-8 content>"

@mcp.tool(
    name="lmstxt_generate_llms_txt",
    annotations={
        "title": "Generate llms.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_txt(
    url: str = Field(..., description="The URL of the repository to process (e.g., https://github.com/owner/repo)"),
    output_dir: str = Field("./artifacts", description="Local directory to store artifacts"),
    cache_lm: bool = Field(True, description="Enable LM caching")
) -> str:
    """
    Generates llms.txt (and llms.json on fallback) for a repository.

    Returns:
        str: JSON-formatted RunRecord containing run_id and status.
    """
    logger.info("Queueing llms.txt generation for %s", url)
    validate_output_dir(Path(output_dir))
    run_id = _start_run(None)
    _spawn_background(
        safe_generate_llms_txt,
        run_store,
        run_id,
        url,
        output_dir,
        cache_lm,
    )
    return run_store.get_run(run_id).model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_generate_llms_full",
    annotations={
        "title": "Generate llms-full.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_full(
    repo_url: str = Field(..., description="Repository URL for resolving default branch and access"),
    run_id: str | None = Field(None, description="Run ID containing llms.txt (optional)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
) -> str:
    """
    Generates llms-full.txt from an existing llms.txt artifact.

    Returns:
        str: JSON-formatted RunRecord with updated artifacts.
    """
    logger.info("Queueing llms-full generation for %s", run_id)
    if not run_id:
        validate_output_dir(Path(output_dir))
    effective_run_id = _start_run(run_id)
    _spawn_background(
        safe_generate_llms_full,
        run_store,
        effective_run_id,
        repo_url,
        output_dir,
    )
    return run_store.get_run(effective_run_id).model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_generate_llms_ctx",
    annotations={
        "title": "Generate llms-ctx.txt",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def generate_llms_ctx(
    run_id: str | None = Field(None, description="Run ID containing llms.txt (optional)"),
    repo_url: str | None = Field(None, description="Repository URL (required when run_id is omitted)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
) -> str:
    """
    Generates llms-ctx.txt from an existing llms.txt artifact.

    Returns:
        str: JSON-formatted RunRecord with updated artifacts.
    """
    logger.info("Queueing llms-ctx generation for %s", run_id)
    if not run_id:
        if not repo_url:
            raise ValueError("repo_url is required when run_id is omitted")
        validate_output_dir(Path(output_dir))
    effective_run_id = _start_run(run_id)
    _spawn_background(
        safe_generate_llms_ctx,
        run_store,
        effective_run_id,
        repo_url,
        output_dir,
    )
    return run_store.get_run(effective_run_id).model_dump_json(indent=2)

@mcp.tool(
    name="lmstxt_list_runs",
    annotations={
        "title": "List Generation History",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def list_runs(
    limit: int = Field(10, description="Maximum number of runs to return", ge=1, le=50)
) -> str:
    """
    Returns a list of recent generation runs, ordered by newest first.

    Returns:
        str: JSON list of RunRecord objects.
    """
    runs = run_store.list_runs(limit=limit)
    return json.dumps([r.model_dump(mode="json") for r in runs], indent=2)

@mcp.tool(
    name="lmstxt_list_all_artifacts",
    annotations={
        "title": "List All Persistent Artifacts",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def list_all_artifacts() -> str:
    """
    Returns a list of all .txt artifact files found in the persistent artifacts directory.
    This includes files from previous server sessions.
    """
    paths = scan_artifacts()
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    results = []
    for p in paths:
        full_path = root / p
        stats = full_path.stat()
        results.append(ArtifactMetadata(
            filename=str(p),
            size_bytes=stats.st_size,
            last_modified=datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc),
            uri=artifact_resource_uri(str(p))
        ))
    return json.dumps([r.model_dump(mode="json") for r in results], indent=2)


@mcp.tool(
    name="lmstxt_list_graph_artifacts",
    annotations={
        "title": "List Graph Artifacts",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
def list_graph_artifacts() -> str:
    paths = scan_graph_artifacts()
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    results = []
    for p in paths:
        full_path = root / p
        stats = full_path.stat()
        results.append(
            ArtifactMetadata(
                filename=str(p),
                size_bytes=stats.st_size,
                last_modified=datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc),
                uri=(
                    repo_graph_node_uri(
                        str(p.parts[0]) + "--" + str(p.parts[1]),
                        p.stem,
                    )
                    if len(p.parts) >= 5 and p.parts[-2] == "nodes"
                    else graph_resource_uri(str(p))
                ),
            )
        )
    return json.dumps([r.model_dump(mode="json") for r in results], indent=2)

@mcp.tool(
    name="lmstxt_read_artifact",
    annotations={
        "title": "Read Artifact Content",
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
def read_artifact(
    run_id: str | None = Field(None, description="The UUID of the run (optional)"),
    repo_url: str | None = Field(None, description="Repository URL (required when run_id is omitted)"),
    output_dir: str = Field("./artifacts", description="Output directory root (used when run_id is omitted)"),
    artifact_name: ArtifactName = Field(..., description="Name of the artifact (e.g., 'llms.txt', 'llms-full.txt')"),
    offset: int = Field(0, description="Byte offset to start reading from", ge=0),
    limit: int = Field(10000, description="Maximum number of characters to read", ge=1, le=100000)
) -> str:
    """
    Reads content from a specific artifact file with pagination support.
    
    Use this for large files (like llms-full.txt) to read in manageable chunks.

    Args:
        run_id (str): Run identifier.
        artifact_name (str): One of: llms.txt, llms-full.txt, llms-ctx.txt, llms.json.
        offset (int): Starting position.
        limit (int): Max characters to return.

    Returns:
        str: JSON-formatted ReadArtifactResult.
        
        Schema:
        {
            "content": "file text content...",
            "truncated": bool,
            "total_chars": int
        }
    """
    effective_limit = min(limit, settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS)
    if run_id:
        logger.info("Reading artifact via run_id %s", run_id)
        content = read_artifact_chunk(run_store, run_id, artifact_name, offset, effective_limit)
    else:
        if not repo_url:
            raise ValueError("repo_url is required when run_id is omitted")
        logger.info("Reading artifact via repo_url + output_dir")
        validated_dir = validate_output_dir(Path(output_dir))
        artifact_path = _artifact_path_from_url(validated_dir, repo_url, artifact_name)
        content = _read_file_chunk(artifact_path, offset, effective_limit)
    
    res = ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content)
    )
    return res.model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_read_graph_artifact",
    annotations={
        "title": "Read Graph Artifact",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
def read_graph_artifact(
    filename: str = Field(..., description="Relative graph artifact path under artifacts root"),
    offset: int = Field(0, description="Byte offset", ge=0),
    limit: int = Field(10000, description="Maximum characters", ge=1, le=100000),
) -> str:
    effective_limit = min(limit, settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS)
    content = read_graph_artifact_chunk(filename, offset, effective_limit)
    result = ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content),
    )
    return result.model_dump_json(indent=2)


@mcp.tool(
    name="lmstxt_read_repo_graph_node",
    annotations={
        "title": "Read Repo Graph Node",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
def read_repo_graph_node(
    repo_id: str = Field(..., description="Repository id (for example owner--repo)"),
    node_id: str = Field(..., description="Graph node id without extension"),
    offset: int = Field(0, description="Byte offset", ge=0),
    limit: int = Field(10000, description="Maximum characters", ge=1, le=100000),
) -> str:
    effective_limit = min(limit, settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS)
    content = read_repo_node_chunk(repo_id=repo_id, node_id=node_id, offset=offset, limit=effective_limit)
    result = ReadArtifactResult(
        content=content,
        truncated=(len(content) == effective_limit),
        total_chars=len(content),
    )
    return result.model_dump_json(indent=2)


@mcp.resource("lmstxt://runs/{run_id}/{artifact_name}")
def get_run_artifact(run_id: str, artifact_name: str) -> str:
    """
    Access a generated artifact as a static resource.
    
    Note: Large files will be truncated according to the server's 
    LLMSTXT_MCP_RESOURCE_MAX_CHARS configuration.
    """
    try:
        return read_resource_text(run_store, run_id, artifact_name)
    except Exception as e:
        logger.error(f"Resource access failed: {e}")
        raise ValueError(f"Failed to read resource: {e}")

@mcp.resource("lmstxt://artifacts/{filename}")
def get_persistent_artifact(filename: str) -> str:
    """
    Access a persistent artifact on disk as a resource.
    
    Note: Large files will be truncated according to the server's 
    LLMSTXT_MCP_RESOURCE_MAX_CHARS configuration.
    """
    root = settings.LLMSTXT_MCP_ALLOWED_ROOT
    path = root / filename
    
    # Security: ensure path is within root
    validate_output_dir(path.parent)
    
    if not path.exists():
        raise FileNotFoundError(f"Artifact {filename} not found")
        
    content, truncated = read_text_preview(
        path, 
        settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS
    )
    
    if truncated:
        content += "\n... (content truncated)"
        
    return content


@mcp.resource("lmstxt://graphs/{filename}")
def get_graph_artifact(filename: str) -> str:
    content = read_graph_artifact_chunk(
        filename,
        0,
        settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS,
    )
    if len(content) >= settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS:
        content += "\n... (content truncated)"
    return content


@mcp.resource("repo://{repo_id}/graph/nodes/{node_id}")
def get_repo_graph_node(repo_id: str, node_id: str) -> str:
    content = read_repo_node_chunk(
        repo_id=repo_id,
        node_id=node_id,
        offset=0,
        limit=settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS,
    )
    if len(content) >= settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS:
        content += "\n... (content truncated)"
    return content

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
```

src/lms_llmsTxt_mcp/session_memory.py
```
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from lms_llmsTxt.context_budget import ContextBudget, estimate_tokens


class SessionMemoryStore:
    """Append-only JSONL memory store with budget-aware pruning."""

    def __init__(self, path: Path, max_events: int = 2000) -> None:
        self.path = path
        self.max_events = max_events
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append_event(self, event_type: str, payload: dict[str, Any]) -> str:
        event_id = str(uuid4())
        row = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.prune_if_needed()
        return event_id

    def list_events(self, limit: int = 200) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        selected = lines[-max(1, limit) :]
        return [json.loads(line) for line in selected if line.strip()]

    def prune_if_needed(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_events:
            return
        kept = lines[-self.max_events :]
        self.path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _is_summary_event(event: dict[str, Any]) -> bool:
    event_type = str(event.get("type", "")).lower()
    payload = event.get("payload", {}) or {}
    payload_kind = str(payload.get("kind", "")).lower() if isinstance(payload, dict) else ""
    return event_type in {"summary", "digest_summary", "repo_digest"} or payload_kind == "summary"


def _format_event(event: dict[str, Any]) -> str:
    timestamp = event.get("timestamp")
    type_label = event.get("type", "event")
    payload = json.dumps(event.get("payload", {}), ensure_ascii=False)
    if timestamp:
        return f"[{timestamp}] [{type_label}] {payload}"
    return f"[{type_label}] {payload}"


def _truncate_to_token_budget(text: str, token_budget: int) -> str:
    if token_budget <= 0:
        return ""
    if estimate_tokens(text) <= token_budget:
        return text
    low = 0
    high = len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid]
        if estimate_tokens(candidate) <= token_budget:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best


def build_active_context(
    events: list[dict[str, Any]],
    max_chars: int = 12000,
    *,
    budget: ContextBudget | None = None,
) -> str:
    indexed = [(idx, event, _format_event(event)) for idx, event in enumerate(events)]

    if budget is None:
        chunks: list[str] = []
        for _, _, chunk in reversed(indexed):
            if len(chunk) > max_chars and not chunks:
                chunks.append(chunk[:max_chars])
                break
            if sum(len(x) for x in chunks) + len(chunk) > max_chars:
                break
            chunks.append(chunk)
        return "\n".join(reversed(chunks))

    max_tokens = max(1, int(budget.available_tokens))
    selected: list[tuple[int, str]] = []
    used_tokens = 0

    def _try_add_candidates(candidates: list[tuple[int, dict[str, Any], str]]) -> None:
        nonlocal used_tokens
        for idx, _, chunk in reversed(candidates):
            remaining = max_tokens - used_tokens
            if remaining <= 0:
                return
            token_len = estimate_tokens(chunk)
            if token_len <= remaining:
                selected.append((idx, chunk))
                used_tokens += token_len
                continue
            if not selected:
                truncated = _truncate_to_token_budget(chunk, remaining)
                if truncated:
                    selected.append((idx, truncated))
                    used_tokens += estimate_tokens(truncated)
            return

    summary_events = [row for row in indexed if _is_summary_event(row[1])]
    raw_events = [row for row in indexed if not _is_summary_event(row[1])]
    _try_add_candidates(summary_events)
    _try_add_candidates(raw_events)

    selected.sort(key=lambda row: row[0])
    return "\n".join(chunk for _, chunk in selected)
```

</source_code>