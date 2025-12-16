from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

import requests

from .github import construct_github_file_url, owner_repo_from_url
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
_URL_HEADERS = {"User-Agent": "lmstudio-llmstxt-generator"}


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


def build_dynamic_buckets(
    repo_url: str,
    file_tree: str,
    default_ref: str | None = None,
    validate_urls: bool = True,
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
                if _url_alive(page["url"]):
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


class RepositoryAnalyzer(dspy.Module):
    """DSPy module that synthesizes an llms.txt summary for a GitHub repository."""

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
        link_style: str = "blob",
    ):
        repo_analysis = self.analyze_repo(
            repo_url=repo_url,
            file_tree=file_tree,
            readme_content=readme_content,
        )
        structure_analysis = self.analyze_structure(
            file_tree=file_tree, package_files=package_files
        )

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
