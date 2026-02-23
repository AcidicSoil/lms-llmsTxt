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
