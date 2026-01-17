The failure in your screenshot is consistent with “private repo looks like 404” behavior from the GitHub REST API: if the request is not properly authenticated, GitHub intentionally returns `404 Not Found` for private resources. ([GitHub Docs][1]) That matches `lmstxt: error: Repository not found: AcidicSoil/oraclepack` even when the repo exists.

In the current code, the CLI only accepts a GitHub repo URL and the GitHub fetch path treats 404 as “not found” without a strong “missing auth” hint.

What to do immediately (to confirm it’s auth, not a regression)

1. If you have GitHub CLI logged in, export a token and retry:

```sh
export GH_TOKEN="$(gh auth token)"
lmstxt https://github.com/AcidicSoil/oraclepack
```

`gh auth token` is the documented way to print the token gh is using. ([GitHub CLI][2])

1. If that works, it’s not “private repo generation is broken”; it’s “token not set / not used / insufficient scope”. GitHub documents PAT-based auth for REST, and notes that missing auth commonly surfaces as 404/403. ([GitHub Docs][3])

What to add to lms-llmsTxt (requested capabilities)
A) Local generation without a GitHub URL (codefetch-style)
Codefetch supports analyzing the current directory and also supports private repos with a token. ([GitHub][4]) The simplest parity is:

* Change the positional argument from “repo URL only” to “source” (GitHub URL OR local path).
* If `source` is a directory (or file path), generate `llms.txt`, `llms-full.txt`, etc. from the local filesystem.
* For local mode, emit links as relative paths (no network required).

B) Private repo robustness (only “fix” if it’s truly failing with a valid token)

* Add `--github-token` CLI flag (so the user doesn’t have to rely on env vars).
* Improve the 404 error message to explicitly mention “private repos return 404 when unauthenticated”.

Below is a concrete patch plan (full file contents for changed/new files).

tree

```
src/lms_llmsTxt/
  analyzer.py        (updated)
  cli.py             (updated)
  fallback.py        (updated)
  full_builder.py    (updated)
  github.py          (updated)
  local_repo.py      (new)
  pipeline.py        (updated)
```

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
        description="Generate llms.txt artifacts for a GitHub repository OR local directory using LM Studio.",
    )
    parser.add_argument(
        "source",
        help="GitHub repository URL (https://github.com/<owner>/<repo>) OR local path (./my-repo)",
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
        "--github-token",
        help="GitHub token for private repositories (overrides GITHUB_ACCESS_TOKEN/GH_TOKEN).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where artifacts will be written (default: OUTPUT_DIR or ./artifacts).",
    )
    parser.add_argument(
        "--link-style",
        choices=["blob", "raw", "local"],
        help="Link style for generated links (default: blob; local mode uses local unless overridden).",
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
    if args.github_token:
        config.github_token = args.github_token
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.link_style:
        config.link_style = args.link_style
    if args.no_ctx:
        config.enable_ctx = False

    try:
        artifacts = run_generation(
            repo_url=args.source,  # NOTE: pipeline now accepts GitHub URL OR local path
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

```python
# path: src/lms_llmsTxt/local_repo.py
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from .models import RepositoryMaterial


_DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def _is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def _git_ls_files(root: Path) -> list[str]:
    """
    Uses git to enumerate files while respecting .gitignore.
    Includes tracked + untracked (but not ignored) files:
      git ls-files -co --exclude-standard
    """
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return files


def _walk_files(root: Path) -> Iterable[str]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _DEFAULT_EXCLUDES for part in rel.parts):
            continue
        yield rel.as_posix()


def _read_text_if_exists(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def gather_local_repository_material(repo_path: str | Path) -> RepositoryMaterial:
    root = Path(repo_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Local path does not exist: {root}")
    if root.is_file():
        root = root.parent

    if _is_git_repo(root):
        paths = _git_ls_files(root)
    else:
        paths = list(_walk_files(root))

    file_tree = "\n".join(sorted(set(paths)))

    readme = ""
    for candidate in ("README.md", "readme.md", "README.MD", "Readme.md"):
        content = _read_text_if_exists(root / candidate)
        if content:
            readme = content
            break

    package_blobs = []
    for candidate in (
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
        "requirements.txt",
        "package.json",
    ):
        content = _read_text_if_exists(root / candidate)
        if content:
            package_blobs.append(f"=== {candidate} ===\n{content}")

    package_files = "\n\n".join(package_blobs)

    return RepositoryMaterial(
        repo_url=str(root),          # local absolute path (string)
        file_tree=file_tree,
        readme_content=readme,
        package_files=package_files,
        default_branch="local",
        is_private=False,
    )
```

```python
# path: src/lms_llmsTxt/github.py
from __future__ import annotations

import base64
import os
import re
from typing import Iterable

import requests
import posixpath
from .models import RepositoryMaterial


def _normalize_repo_path(path: str) -> str:
    path = path.lstrip("/")
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
    """
    Return (owner, repo) for https/SSH GitHub URLs.

    Also accepts shorthand:
      - github.com/<owner>/<repo>
    """
    raw = repo_url.strip()
    if raw.startswith("github.com/"):
        raw = "https://" + raw
    if raw.startswith("www.github.com/"):
        raw = "https://" + raw[len("www.") :]

    m = _GITHUB_URL.match(raw)
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
        # IMPORTANT: GitHub returns 404 for private repos when unauthenticated/unauthorized.
        hint = ""
        if not token:
            hint = (
                " (If this is a private repo, set GH_TOKEN/GITHUB_ACCESS_TOKEN or pass --github-token.)"
            )
        raise FileNotFoundError(f"Repository not found or access denied: {owner}/{repo}{hint}")
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


def fetch_file_tree(owner: str, repo: str, ref: str, token: str | None) -> Iterable[str]:
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


def fetch_file_content(owner: str, repo: str, path: str, ref: str, token: str | None) -> str | None:
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
    for candidate in ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "package.json"):
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


def construct_github_file_url(repo_url: str, path: str, ref: str | None = None, style: str = "blob") -> str:
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

```python
# path: src/lms_llmsTxt/analyzer.py
from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

from .github import construct_github_file_url, fetch_file_content, owner_repo_from_url

try:
    import dspy
except ImportError:
    from .signatures import dspy

from .signatures import AnalyzeCodeStructure, AnalyzeRepository, GenerateLLMsTxt, GenerateUsageExamples

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


def _local_path_exists(local_root: Path, path: str) -> bool:
    try:
        p = (local_root / path).resolve()
        # best-effort containment (avoid escaping)
        if local_root.resolve() not in p.parents and p != local_root.resolve():
            return False
        return p.exists() and p.is_file()
    except Exception:
        return False


def build_dynamic_buckets(
    repo_url: str,
    file_tree: str,
    default_ref: str | None = None,
    validate_urls: bool = True,
    is_private: bool = False,
    github_token: str | None = None,
    link_style: str = "blob",
    local_root: Path | None = None,
) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    paths = [p.strip() for p in file_tree.splitlines() if p.strip()]
    pages = []
    for path in paths:
        if not re.search(r"\.(md|mdx|py|ipynb|js|ts|rst|txt|html)$", path, flags=re.I):
            continue

        if local_root is not None or link_style == "local":
            url = path
        else:
            url = construct_github_file_url(repo_url, path, ref=default_ref, style=link_style)

        pages.append(
            {
                "path": path,
                "url": url,
                "title": ("README" if re.search(r"(^|/)README\.md$", path, flags=re.I) else _nicify_title(path)),
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
                if local_root is not None or link_style == "local":
                    ok = _local_path_exists(local_root or Path(repo_url), page["path"])
                elif is_private and github_token:
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
    bullets = bullets[:6] or ["Install + Quickstart first", "Core concepts & API surface", "Use Tutorials for worked examples"]
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
    def __init__(self) -> None:
        super().__init__()
        self.analyze_repo = dspy.ChainOfThought(AnalyzeRepository)
        self.analyze_structure = dspy.ChainOfThought(AnalyzeCodeStructure)
        self.generate_examples = dspy.ChainOfThought(GenerateUsageExamples)
        self.generate_llms_txt = dspy.ChainOfThought(GenerateLLMsTxt)

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
        local_root: Path | None = None,
    ):
        repo_analysis = self.analyze_repo(repo_url=repo_url, file_tree=file_tree, readme_content=readme_content)
        structure_analysis = self.analyze_structure(file_tree=file_tree, package_files=package_files)

        self.generate_examples(
            repo_info=(
                f"Purpose: {repo_analysis.project_purpose}\n\n"
                f"Concepts: {', '.join(repo_analysis.key_concepts or [])}\n\n"
                f"Entry points: {', '.join(structure_analysis.entry_points or [])}\n"
            )
        )

        project_name = "Project"
        try:
            _, repo = owner_repo_from_url(repo_url)
            project_name = repo.replace("-", " ").replace("_", " ").title()
        except Exception:
            # local path fallback
            try:
                project_name = Path(str(repo_url)).name.replace("-", " ").replace("_", " ").title() or "Project"
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
            local_root=local_root,
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

```python
# path: src/lms_llmsTxt/fallback.py
from __future__ import annotations

import textwrap
from pathlib import Path
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
    return summary or "Project overview unavailable."


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
    local_root: Path | None = None,
) -> Dict[str, object]:
    buckets = build_dynamic_buckets(
        repo_url,
        file_tree,
        default_ref=default_branch,
        validate_urls=True,
        is_private=is_private,
        github_token=github_token,
        link_style=link_style,
        local_root=local_root,
    )
    summary = _summary_from_readme(readme_content)
    remember = _remember_bullets()
    sections: List[Dict[str, object]] = []
    for title, items in buckets:
        links = [{"title": link_title, "url": link_url, "note": note} for (link_title, link_url, note) in items]
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
        items = [(link["title"], link["url"], link["note"]) for link in sec["links"]]  # type: ignore[index]
        buckets.append((sec["title"], items))  # type: ignore[arg-type]
    markdown = render_llms_markdown(
        project_name=repo_name,
        project_purpose=payload["project"]["summary"],  # type: ignore[index]
        remember_bullets=payload["remember"],  # type: ignore[index]
        buckets=buckets,
    )
    header = textwrap.dedent("""\
        <!-- Generated via fallback path (no LM). -->
        """)
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
    local_root: Path | None = None,
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
        local_root=local_root,
    )
    return fallback_markdown_from_payload(repo_name, payload)


__all__ = [
    "fallback_llms_payload",
    "fallback_llms_markdown",
    "fallback_markdown_from_payload",
]
```

```python
# path: src/lms_llmsTxt/full_builder.py
from __future__ import annotations

import base64
import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin, urlparse

import posixpath
import requests

from .github import _normalize_repo_path


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


def gh_get_file(owner: str, repo: str, path: str, ref: Optional[str] = None, token: Optional[str] = None) -> Tuple[str, bytes]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref} if ref else {}
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lms-lmstxt"}
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


def fetch_raw_file(owner: str, repo: str, path: str, ref: str) -> bytes:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    response = requests.get(url, headers={"User-Agent": "lms-lmstxt"}, timeout=30)
    if response.status_code == 404:
        raise FileNotFoundError(f"Raw GitHub 404 for {owner}/{repo}/{path}@{ref}")
    response.raise_for_status()
    return response.content


_PAGE_LINK = re.compile(r"^\s*-\s*\[(?P<title>.+?)\]\((?P<url>[^\s)]+)\)", re.M)
_MD_LINK = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)")
_HTML_LINK = re.compile(r"<a\s+[^>]*href=[\"'](?P<href>[^\"'#]+)[\"'][^>]*>(?P<text>.*?)</a>", re.I | re.S)

_TAG = re.compile(r"<[^>]+>")
_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
_WHITESPACE = re.compile(r"[ \t\f\v]+")
_NEWLINES = re.compile(r"\n{3,}")


def iter_llms_links(curated_text: str) -> Iterable[Tuple[str, str]]:
    for match in _PAGE_LINK.finditer(curated_text):
        yield match.group("title").strip(), match.group("url").strip()


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _localize_block_path(url: str) -> str:
    u = url.strip()
    if u.startswith("file://"):
        u = urlparse(u).path
    return u.lstrip("/").lstrip("./")


def sanitize_path_for_block(title: str, url: str, gh: Optional[GhRef]) -> str:
    if gh:
        return gh.path
    if _is_http_url(url):
        return title.lower().strip().replace(" ", "-")
    # local (relative) path
    return _localize_block_path(url) or title.lower().strip().replace(" ", "-")


def _resolve_repo_url(gh: GhRef, ref: str, href: str, style: str = "blob") -> Optional[str]:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:")):
        return None
    if href.startswith(("http://", "https://")):
        return href

    if href.startswith("/"):
        rel = href.lstrip("/")
    else:
        base_dir = gh.path.rsplit("/", 1)[0] if "/" in gh.path else ""
        rel = f"{base_dir}/{href}" if base_dir else href

    rel = _normalize_repo_path(rel)

    last = rel.rsplit("/", 1)[-1]
    if "." not in last:
        rel = rel + ".md"

    if style == "raw":
        return f"https://raw.githubusercontent.com/{gh.owner}/{gh.repo}/{ref}/{rel}"
    return f"https://github.com/{gh.owner}/{gh.repo}/blob/{ref}/{rel}"


def _resolve_web_url(base_url: str, href: str) -> Optional[str]:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    resolved = urljoin(base_url, href)
    if resolved.startswith(("http://", "https://")):
        return resolved
    return None


def _resolve_local_url(local_root: Path, base_file: Path, href: str) -> Optional[str]:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    if _is_http_url(href):
        return href
    if href.startswith("file://"):
        return _localize_block_path(href)

    # normalize local relative paths against current file dir
    if href.startswith("/"):
        candidate = (local_root / href.lstrip("/")).resolve()
    else:
        candidate = (base_file.parent / href).resolve()

    try:
        root = local_root.resolve()
        if candidate != root and root not in candidate.parents:
            return None
        rel = candidate.relative_to(root).as_posix()
        # heuristic for extensionless “docs/foo” -> “docs/foo.md”
        last = rel.rsplit("/", 1)[-1]
        if "." not in last:
            rel = rel + ".md"
        return rel
    except Exception:
        return None


def _extract_links(
    body_text: str,
    *,
    gh: Optional[GhRef],
    ref: str,
    base_url: Optional[str],
    link_style: str = "blob",
    local_root: Optional[Path] = None,
    local_base_file: Optional[Path] = None,
) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    found: list[tuple[str, str]] = []

    def _add(text: str, href: str):
        key = (text, href)
        if key not in seen:
            seen.add(key)
            found.append(key)

    for m in _MD_LINK.finditer(body_text):
        text = m.group("text").strip()
        href = m.group("href").strip()
        if gh:
            resolved = _resolve_repo_url(gh, ref, href, style=link_style)
        elif local_root is not None and local_base_file is not None:
            resolved = _resolve_local_url(local_root, local_base_file, href)
        else:
            resolved = _resolve_web_url(base_url or "", href)
        if resolved:
            _add(text, resolved)

    for m in _HTML_LINK.finditer(body_text):
        text = re.sub(r"\s+", " ", m.group("text")).strip() or "link"
        href = m.group("href").strip()
        if gh:
            resolved = _resolve_repo_url(gh, ref, href, style=link_style)
        elif local_root is not None and local_base_file is not None:
            resolved = _resolve_local_url(local_root, local_base_file, href)
        else:
            resolved = _resolve_web_url(base_url or "", href)
        if resolved:
            _add(text, resolved)

    return found


def _html_to_text(html: str) -> str:
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
    local_root: Optional[Path] = None,
) -> str:
    resolved_token = token if token is not None else os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
    blocks = []
    seen = set()
    count = 0

    for title, url in iter_llms_links(curated_llms_text):
        if count >= max_files:
            break

        gh = parse_github_link(url)

        # dedupe
        if gh:
            key = (gh.owner, gh.repo, gh.path, gh.ref or "")
        else:
            key = ("local" if (local_root is not None and not _is_http_url(url)) else "web", url)
        if key in seen:
            continue
        seen.add(key)

        if gh:
            resolved_ref = gh.ref or default_ref or "main"
            try:
                if prefer_raw:
                    body = fetch_raw_file(gh.owner, gh.repo, gh.path, resolved_ref)
                else:
                    _, body = gh_get_file(gh.owner, gh.repo, gh.path, resolved_ref, resolved_token)
            except requests.HTTPError as exc:
                body = f"[fetch-error] {gh.owner}/{gh.repo}/{gh.path}@{resolved_ref} :: {exc}".encode("utf-8")
            except Exception as exc:
                body = f"[fetch-error] {gh.owner}/{gh.repo}/{gh.path}@{resolved_ref} :: {exc}".encode("utf-8")

            if len(body) > max_bytes_per_file:
                body = body[:max_bytes_per_file] + b"\n[truncated]\n"

            block_path = sanitize_path_for_block(title, url, gh)
            text_body = body.decode("utf-8", "replace")

            links = _extract_links(text_body, gh=gh, ref=resolved_ref, base_url=None, link_style=link_style)[:100]
            link_section = ""
            if links:
                bullet_lines = "\n".join(f"- [{t}]({h})" for t, h in links)
                link_section = f"\n## Links discovered\n{bullet_lines}\n"

            blocks.append(f"--- {block_path} ---\n{text_body}\n{link_section}")
            count += 1
            continue

        # local file mode (relative links like docs/foo.md)
        if local_root is not None and not _is_http_url(url):
            rel = _localize_block_path(url)
            path = (local_root / rel).resolve()
            try:
                root = local_root.resolve()
                if path != root and root not in path.parents:
                    raise FileNotFoundError(f"Path escapes local root: {rel}")
                text_body = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                text_body = f"[fetch-error] {rel} :: {exc}"

            encoded = text_body.encode("utf-8", "ignore")
            if len(encoded) > max_bytes_per_file:
                encoded = encoded[:max_bytes_per_file] + b"\n[truncated]\n"
                text_body = encoded.decode("utf-8", "ignore")

            links = _extract_links(
                text_body,
                gh=None,
                ref="",
                base_url=None,
                link_style=link_style,
                local_root=local_root,
                local_base_file=path if "path" in locals() else (local_root / rel),
            )[:100]
            link_section = ""
            if links:
                bullet_lines = "\n".join(f"- [{t}]({h})" for t, h in links)
                link_section = f"\n## Links discovered\n{bullet_lines}\n"

            block_path = sanitize_path_for_block(title, url, gh=None)
            blocks.append(f"--- {block_path} ---\n{text_body}\n{link_section}")
            count += 1
            continue

        # website fetch
        try:
            html = _fetch_website(url)
        except Exception as exc:
            text_body = f"[fetch-error] {url} :: {exc}"
        else:
            text_body = _html_to_text(html)

        encoded = text_body.encode("utf-8", "ignore")
        if len(encoded) > max_bytes_per_file:
            encoded = encoded[:max_bytes_per_file] + b"\n[truncated]\n"
            text_body = encoded.decode("utf-8", "ignore")

        links = _extract_links(
            html if "html" in locals() else text_body,
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
        > Built from GitHub files, local files, and website pages. Large files may be truncated.
        """
    )
    return disclaimer + "\n" + "\n".join(blocks)
```

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
from .fallback import fallback_llms_payload, fallback_markdown_from_payload
from .github import gather_repository_material, owner_repo_from_url
from .local_repo import gather_local_repository_material
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
from .schema import LLMS_JSON_SCHEMA

try:
    from litellm.exceptions import BadRequestError as LiteLLMBadRequestError
except Exception:
    LiteLLMBadRequestError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
except Exception:
    LiteLLMRateLimitError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import AuthenticationError as LiteAuthError
except Exception:
    LiteAuthError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import NotFoundError as LiteNotFoundError
except Exception:
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


def _is_github_source(source: str) -> bool:
    s = source.strip()
    return (
        s.startswith(("http://", "https://", "git@github.com:", "ssh://git@github.com/"))
        or s.startswith("github.com/")
        or s.startswith("www.github.com/")
    )


def prepare_repository_material(config: AppConfig, source: str) -> tuple[RepositoryMaterial, Optional[Path], str, str]:
    """
    Returns (material, local_root, owner, repo)
    """
    if _is_github_source(source):
        owner, repo = owner_repo_from_url(source)
        material = gather_repository_material(source, config.github_token)
        return material, None, owner, repo

    # local path mode
    local_root = Path(source).expanduser().resolve()
    material = gather_local_repository_material(local_root)
    owner = "local"
    repo = local_root.name
    return material, local_root, owner, repo


def run_generation(
    repo_url: str,
    config: AppConfig,
    *,
    stamp: bool = False,
    cache_lm: bool = False,
    build_full: bool = True,
    build_ctx: bool | None = None,
) -> GenerationArtifacts:
    # NOTE: repo_url is now “source”: GitHub URL OR local path
    material, local_root, owner, repo = prepare_repository_material(config, repo_url)

    # local mode: default to local links unless user explicitly asked for blob/raw
    if local_root is not None and config.link_style in (None, "", "blob", "raw"):
        # If you want GitHub-style links while running locally, pass --link-style blob and a GitHub URL instead.
        config.link_style = "local"

    repo_root = config.ensure_output_root(owner, repo)
    base_name = repo.lower().replace(" ", "-")

    logger.debug("Preparing repository material for %s", repo_url)
    analyzer = RepositoryAnalyzer()

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
            local_root=local_root,
        )
        llms_text = result.llms_txt_content
    except (LiteLLMBadRequestError, LiteLLMRateLimitError, LiteAuthError, LiteNotFoundError, LMStudioConnectivityError):
        used_fallback = True
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=material.repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
            local_root=local_root,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    except Exception as exc:
        used_fallback = True
        logger.exception("Unexpected error during DSPy generation: %s", exc)
        logger.warning("Falling back to heuristic llms.txt generation using %s.", LLMS_JSON_SCHEMA["title"])
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=material.repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
            local_root=local_root,
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
            local_root=local_root,
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

How this addresses your three bullets

1. “Generate artifacts locally without a github url”: `lmstxt ./some/repo` now works (and defaults to `link_style=local` in local mode).
2. “Similar to codefetch”: local-first behavior + optional GitHub token flag is directly aligned with codefetch’s “analyze current directory” and “private repo with token” workflows. ([GitHub][4])
3. “Fix private repo generating (only if broken)”: this doesn’t change the underlying GitHub requirement (you still need auth), but it:

   * makes token usage explicit (`--github-token`)
   * produces an accurate error message when 404 is likely “private + missing auth” (matching GitHub’s documented behavior). ([GitHub Docs][1])

[1]: https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api "https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api"
[2]: https://cli.github.com/manual/gh_auth_token "https://cli.github.com/manual/gh_auth_token"
[3]: https://docs.github.com/rest/overview/authenticating-to-the-rest-api "https://docs.github.com/rest/overview/authenticating-to-the-rest-api"
[4]: https://github.com/regenrek/codefetch "https://github.com/regenrek/codefetch"
