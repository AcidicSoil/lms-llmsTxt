
## Where `dspy.RLM` fits best in this repo

Your generator currently sends potentially huge **`file_tree`** (and sometimes large README / package blobs) straight into `dspy.ChainOfThought(...)`. That’s exactly the scenario `dspy.RLM` targets: *programmatic exploration of oversized context in a sandboxed Python REPL* instead of stuffing it into the prompt. ([dspy.ai](https://dspy.ai/api/modules/RLM/))
So the highest-leverage integration is:

1) **Keep Chain-of-Thought for small repos** (fast path)
2) **Auto-switch to `dspy.RLM` when inputs exceed a size threshold** (large-repo path)
3) **Fall back to Chain-of-Thought if RLM can’t run** (e.g., Deno not installed / sandbox issue) ([dspy.ai](https://dspy.ai/api/modules/RLM/))
This touches only the generator side (no MCP API changes needed) because both `cli.py` and `lms_llmsTxt_mcp/generator.py` ultimately go through `run_generation(...)` in `pipeline.py`.

---

## Exact files toion)

### ✅ Core (recommended)
| File | What you change |
|---|---|
| `src/lms_llmsTxt/config.py` | Add config knobs: `ENABLE_RLM`, size threshold, RLM iteration limits |
| `src/lms_llmsTxt/analyzer.py` | Instantiate both CoT + RLM; auto-switch based on input size; safe fallback |
| `src/lms_llmsTxt/pipeline.py` | Pass `AppConfig` into `RepositoryAnalyzer(...)` |
| `src/lms_llmsTxt/cli.py` | Add `--rlm` + a couple optional tuning flags |

These locations are in your provided codebase.

---

## Implementation

### tree
```text
src/
  lms_llmsTxt/
    analyzer.py
    cli.py
    config.py
    pipeline.py
```

---

```python
# path: src/lms_llmsTxt/config.py
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


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


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

    RLM (Recursive Language Model) toggles:
      - ``ENABLE_RLM``: Use dspy.RLM for large inputs.
      - ``RLM_MIN_CHARS``: Minimum combined input size (file_tree+README+package files)
        to trigger RLM. Below this threshold, we use ChainOfThought.
      - ``RLM_MAX_ITERATIONS`` / ``RLM_MAX_LLM_CALLS`` / ``RLM_MAX_OUTPUT_CHARS``:
        Safety bounds for the REPL loop and sub-LM calls.
      - ``RLM_VERBOSE``: Enable RLM verbose mode.
    """

    lm_model: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_MODEL", "qwen_qwen3-vl-4b-instruct")
    )
    lm_api_base: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    )
    lm_api_key: str = field(default_factory=lambda: os.getenv("LMSTUDIO_API_KEY", "lm-studio"))
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "artifacts")))
    github_token: str | None = field(
        default_factory=lambda: os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
    )
    link_style: str = field(default_factory=lambda: os.getenv("LINK_STYLE", "blob"))
    enable_ctx: bool = field(default_factory=lambda: _env_flag("ENABLE_CTX", False))
    lm_streaming: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_STREAMING", True))
    lm_auto_unload: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_AUTO_UNLOAD", True))

    # RLM toggles
    enable_rlm: bool = field(default_factory=lambda: _env_flag("ENABLE_RLM", False))
    rlm_min_chars: int = field(default_factory=lambda: _env_int("RLM_MIN_CHARS", 120_000))
    rlm_max_iterations: int = field(default_factory=lambda: _env_int("RLM_MAX_ITERATIONS", 12))
    rlm_max_llm_calls: int = field(default_factory=lambda: _env_int("RLM_MAX_LLM_CALLS", 40))
    rlm_max_output_chars: int = field(default_factory=lambda: _env_int("RLM_MAX_OUTPUT_CHARS", 10_000))
    rlm_verbose: bool = field(default_factory=lambda: _env_flag("RLM_VERBOSE", False))

    def ensure_output_root(self, owner: str, repo: str) -> Path:
        """Return ``<output_root>/<owner>/<repo>`` and create it if missing."""
        repo_root = self.output_dir / owner / repo
        repo_root.mkdir(parents=True, exist_ok=True)
        return repo_root
```

---

```python
# path: src/lms_llmsTxt/analyzer.py
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

import requests

from .config import AppConfig
from .github import construct_github_file_url, fetch_file_content, owner_repo_from_url

try:
    import dspy
except ImportError:
    from .signatures import dspy

from .signatures import (
    AnalyzeCodeStructure,
    AnalyzeRepository,
    GenerateLLMsTxt,
    GenerateUsageExamples,
)

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
    if any(hint in lower for hint in ["getting-started", "quickstart", "install", "overview", "/readme"]):
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
    if any(hint in lower for hint in ["quickstart", "getting-started", "install", "overview", "/readme"]):
        score += 5
    if any(hint in lower for hint in ["tutorial", "example", "how-to", "demo"]):
        score += 3
    if re.search(r"(^|/)index(\.mdx?|\.html?)?$", lower):
        score += 2
    score -= lower.count("/") * 0.1
    return score


TAXONOMY: List[Tuple[str, re.Pattern]] = [
    ("Docs", re.compile(r"(docs|guide|getting[-_ ]?started|quickstart|install|overview)", re.I)),
    ("Tutorials", re.compile(r"(tutorial|example|how[-_ ]?to|cookbook|demos?)", re.I)),
    ("API", re.compile(r"(api|reference|sdk|class|module)", re.I)),
    ("Concepts", re.compile(r"(concept|architecture|design|faq)", re.I)),
    ("Optional", re.compile(r"(contributing|changelog|release|security|license|benchmark)", re.I)),
]


def _url_alive(url: str) -> bool:
    try:
        response = _URL_SESSION.head(url, allow_redirects=True, timeout=_URL_VALIDATION_TIMEOUT, headers=_URL_HEADERS)
        status = response.status_code
        if status and status < 400:
            return True
        response = _URL_SESSION.get(url, stream=True, timeout=_URL_VALIDATION_TIMEOUT, headers=_URL_HEADERS)
        response.close()
        return response.status_code < 400
    except requests.RequestException:
        return False


def _github_path_exists(repo_url: str, path: str, ref: str | None, token: str | None) -> bool:
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
                "url": construct_github_file_url(repo_url, path, ref=default_ref, style=link_style),
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
                    ok = _github_path_exists(repo_url, page["path"], default_ref, github_token)
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
            ordered.append((name, [(pg["title"], pg["url"], pg["note"]) for pg in buckets[name]]))
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


class RepositoryAnalyzer(dspy.Module):
    """
    DSPy module that synthesizes an llms.txt summary for a GitHub repository.

    Enhancement: optionally uses dspy.RLM for large inputs (huge file trees / READMEs),
    falling back to ChainOfThought if RLM is unavailable or fails.
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or AppConfig()

        # Always keep a CoT path (fast, minimal dependencies).
        self._analyze_repo_cot = dspy.ChainOfThought(AnalyzeRepository)
        self._analyze_structure_cot = dspy.ChainOfThought(AnalyzeCodeStructure)

        # Optional RLM path (handles very large contexts).
        self._analyze_repo_rlm = None
        self._analyze_structure_rlm = None
        rlm_ctor = getattr(dspy, "RLM", None)

        if callable(rlm_ctor) and self.config.enable_rlm:
            try:
                self._analyze_repo_rlm = rlm_ctor(
                    AnalyzeRepository,
                    max_iterations=self.config.rlm_max_iterations,
                    max_llm_calls=self.config.rlm_max_llm_calls,
                    max_output_chars=self.config.rlm_max_output_chars,
                    verbose=self.config.rlm_verbose,
                )
                self._analyze_structure_rlm = rlm_ctor(
                    AnalyzeCodeStructure,
                    max_iterations=self.config.rlm_max_iterations,
                    max_llm_calls=self.config.rlm_max_llm_calls,
                    max_output_chars=self.config.rlm_max_output_chars,
                    verbose=self.config.rlm_verbose,
                )
                logger.info("RLM enabled for repository analysis (threshold=%s chars).", self.config.rlm_min_chars)
            except Exception as exc:
                # If RLM can't initialize (e.g., missing Deno), we silently keep CoT.
                self._analyze_repo_rlm = None
                self._analyze_structure_rlm = None
                logger.warning("Failed to initialize dspy.RLM; using ChainOfThought only (%s).", exc)

        self.generate_examples = dspy.ChainOfThought(GenerateUsageExamples)
        self.generate_llms_txt = dspy.ChainOfThought(GenerateLLMsTxt)

    def _should_use_rlm(self, file_tree: str, readme_content: str, package_files: str) -> bool:
        if not self.config.enable_rlm:
            return False
        if self._analyze_repo_rlm is None or self._analyze_structure_rlm is None:
            return False
        total = len(file_tree or "") + len(readme_content or "") + len(package_files or "")
        return total >= self.config.rlm_min_chars

    def forward(
        self,
        repo_url: str,
        file_tree: str,
        readme_content: str,
        package_files: str,
        default_branch: str | None = None,
        is_private: bool = False,
        github_token: str | None = None,
        link_style: str = "blob",
    ):
        use_rlm = self._should_use_rlm(file_tree, readme_content, package_files)
        analyze_repo = self._analyze_repo_rlm if use_rlm else self._analyze_repo_cot
        analyze_structure = self._analyze_structure_rlm if use_rlm else self._analyze_structure_cot

        try:
            repo_analysis = analyze_repo(repo_url=repo_url, file_tree=file_tree, readme_content=readme_content)
        except Exception as exc:
            logger.warning("Repo analysis failed (%s); falling back to ChainOfThought.", exc)
            repo_analysis = self._analyze_repo_cot(repo_url=repo_url, file_tree=file_tree, readme_content=readme_content)

        try:
            structure_analysis = analyze_structure(file_tree=file_tree, package_files=package_files)
        except Exception as exc:
            logger.warning("Structure analysis failed (%s); falling back to ChainOfThought.", exc)
            structure_analysis = self._analyze_structure_cot(file_tree=file_tree, package_files=package_files)

        # (Existing behavior preserved)
        self.generate_examples(
            repo_info=(
                f"Purpose: {repo_analysis.project_purpose}\n\n"
                f"Concepts: {', '.join(repo_analysis.key_concepts or [])}\n\n"
                f"Entry points: {', '.join(structure_analysis.entry_points or [])}\n"
            )
        )

        try:
            _, repo = owner_repo_from_url(repo_url)
            project_name = repo.replace("-", " ").replace("_", " ").title()
        except Exception:
            project_name = "Project"

        buckets = build_dynamic_buckets(
            repo_url,
            file_tree,
            default_ref=default_branch,
            validate_urls=True,
            is_private=is_private,
            github_token=github_token,
            link_style=link_style,
        )

        llms_txt_content = render_llms_markdown(
            project_name=project_name,
            project_purpose=repo_analysis.project_purpose or "",
            remember_bullets=repo_analysis.key_concepts or [],
            buckets=buckets,
        )

        return dspy.Prediction(
            llms_txt_content=llms_txt_content,
            analysis=repo_analysis,
            structure=structure_analysis,
        )
```

---

```python
# path: src/lms_llmsTxt/pipeline.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .analyzer import RepositoryAnalyzer
from .config import AppConfig
from .full_builder import build_llms_full_from_repo
from .fallback import (
    fallback_llms_payload,
    fallback_markdown_from_payload,
)
from .github import gather_repository_material, owner_repo_from_url
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
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
) -> GenerationArtifacts:
    owner, repo = owner_repo_from_url(repo_url)
    repo_root = config.ensure_output_root(owner, repo)
    base_name = repo.lower().replace(" ", "-")

    logger.debug("Preparing repository material for %s", repo_url)
    material = prepare_repository_material(config, repo_url)

    # Pass config in so analyzer can choose RLM/CoT.
    analyzer = RepositoryAnalyzer(config=config)

    fallback_payload = None
    used_fallback = False
    project_name = repo.replace("-", " ").replace("_", " ").title()

    model_loaded = False

    try:
        logger.info("Configuring LM Studio model '%s'", config.lm_model)
        configure_lmstudio_lm(config, cache=cache_lm)
        model_loaded = True

        result = analyzer(
            repo_url=material.repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            package_files=material.package_files,
            default_branch=material.default_branch,
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
        )
        llms_text = result.llms_txt_content
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
        logger.warning(
            "Falling back to heuristic llms.txt generation using %s.",
            LLMS_JSON_SCHEMA["title"],
        )
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

    llms_txt_path = repo_root / f"{base_name}-llms.txt"
    logger.info("Writing llms.txt to %s", llms_txt_path)
    _write_text(llms_txt_path, llms_text, stamp)

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
    if build_full:
        llms_full_text = build_llms_full_from_repo(
            llms_text,
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

    return GenerationArtifacts(
        llms_txt_path=str(llms_txt_path),
        llms_full_path=str(llms_full_path) if llms_full_path else None,
        ctx_path=str(ctx_path) if ctx_path else None,
        json_path=str(json_path) if json_path else None,
        used_fallback=used_fallback,
    )
```

---

```python
# path: src/lms_llmsTxt/cli.py
import argparse
import logging
import sys
from pathlib import Path
from textwrap import dedent

from .config import AppConfig
from .pipeline import run_generation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lmstxt",
        description="Generate llms.txt artifacts for a GitHub repository using LM Studio.",
    )
    parser.add_argument("repo", help="GitHub repository URL (https://github.com/<owner>/<repo>)")
    parser.add_argument("--model", help="LM Studio model identifier (overrides LMSTUDIO_MODEL).")
    parser.add_argument("--api-base", help="LM Studio API base URL (overrides LMSTUDIO_BASE_URL).")
    parser.add_argument("--api-key", help="LM Studio API key (overrides LMSTUDIO_API_KEY).")
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
    parser.add_argument("--stamp", action="store_true", help="Append a UTC timestamp comment to generated files.")
    parser.add_argument("--no-ctx", action="store_true", help="Skip generating llms-ctx.txt even if ENABLE_CTX is set.")
    parser.add_argument("--cache-lm", action="store_true", help="Enable DSPy's LM cache (useful for repeated experiments).")

    # RLM toggles
    parser.add_argument(
        "--rlm",
        action="store_true",
        help="Enable dspy.RLM for very large inputs (requires Deno; see DSPy RLM docs).",
    )
    parser.add_argument(
        "--rlm-min-chars",
        type=int,
        help="Minimum combined input chars (file_tree+README+package blobs) to trigger RLM.",
    )
    parser.add_argument("--rlm-max-iterations", type=int, help="Max RLM REPL iterations.")
    parser.add_argument("--rlm-max-llm-calls", type=int, help="Max RLM sub-LM calls (llm_query).")
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

    if args.rlm:
        config.enable_rlm = True
    if args.rlm_min_chars is not None:
        config.rlm_min_chars = int(args.rlm_min_chars)
    if args.rlm_max_iterations is not None:
        config.rlm_max_iterations = int(args.rlm_max_iterations)
    if args.rlm_max_llm_calls is not None:
        config.rlm_max_llm_calls = int(args.rlm_max_llm_calls)

    try:
        artifacts = run_generation(
            repo_url=args.repo,
            config=config,
            stamp=bool(args.stamp),
            cache_lm=bool(args.cache_lm),
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
    if artifacts.used_fallback:
        summary += "\n(note) LM call failed; fallback JSON/schema output was used."

    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## How to run it

### 1) Install the RLM sandbox dependency (Deno)
```bash
curl -fsSL https://deno.land/install.sh | sh
```

- Downloads and installs **Deno** (required by DSPy’s default RLM interpreter).
- You’ll typically need to restart your shell (or source your profile) so `deno` is on `PATH`. ([dspy.ai](https://dspy.ai/api/modules/RLM/))
### 2) Enable RLM for large repos
```bash
ENABLE_RLM=1 RLM_MIN_CHARS=120000 lmstxt https://github.com/<owner>/<repo>
```

- Turns on the RLM path.
- Sets the threshold where your analyzer switches from CoT → RLM.
- Runs the generator normally (same outputs), but large `file_tree` inputs won’t be shoved directly into the prompt. ([dspy.ai](https://dspy.ai/api/modules/RLM/))
---

## Optional next step (higher impact, more invasive)

If you want RLM to do *more than just “handle huge file trees”*, the next best place is a **second-pass “deep extraction”** over `llms-full.txt` (which can be enormous). RLM is explicitly built for long-document analysis via REPL + bounded sub-LM calls. ([dspy.ai](https://dspy.ai/api/modules/RLM/))
That would add these touches:

- `src/lms_llmsTxt/pipeline.py`: after `llms_full_text` is built, run an `RLM("document -> usage_examples, architecture_overview, entry_points")` pass and inject results into `llms.txt` (or write a new artifact like `*-llms-insights.json`).
- Potentially `src/lms_llmsTxt/models.py`: add a new artifact path.

I didn’t include this in the core patch above because it changes outputs/format behavior, whereas the core patch is a safe, drop-in “same outputs, more robust on large repos.”