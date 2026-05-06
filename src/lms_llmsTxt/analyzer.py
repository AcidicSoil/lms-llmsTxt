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

try:
    from dspy.utils.exceptions import AdapterParseError
except Exception:  # pragma: no cover - only used when real DSPy is installed
    AdapterParseError = ()  # type: ignore[assignment]

from .models import AnalyzerTrace, LLMsDocument, LLMsLinkEntry, LLMsSection
from .repo_digest import RepoDigest
from .signatures import (
    AnalyzeCodeStructure,
    AnalyzeRepository,
    AnalyzeRepositoryFromDigest,
    GenerateUsageExamples,
    PlanLLMsSections,
    SynthesizeLLMsSectionNotes,
)

logger = logging.getLogger(__name__)

_URL_VALIDATION_TIMEOUT = 5
_URL_SESSION = requests.Session()
_URL_HEADERS = {"User-Agent": "lms-lmstxt"}


def _clean_path_part(part: str) -> str:
    part = re.sub(r"\.(mdx?|rst|txt|py|ipynb|js|ts|html)$", "", part, flags=re.I)
    part = part.strip("_-. ")
    part = re.sub(r"^\d+[_-]*", "", part)
    lower = part.lower()
    acronyms = {
        "api": "API",
        "sdk": "SDK",
        "cli": "CLI",
        "ui": "UI",
        "llm": "LLM",
        "mcp": "MCP",
        "rest": "REST",
        "json": "JSON",
        "faq": "FAQ",
        "repl": "REPL",
    }
    if lower in acronyms:
        return acronyms[lower]
    return " ".join(piece.capitalize() for piece in re.split(r"[-_\s]+", part) if piece)


def _platform_from_path(path: str) -> str:
    first = path.strip("/").split("/", 1)[0].lower()
    if "python" in first:
        return "Python"
    if "typescript" in first:
        return "TypeScript"
    if "developer" in first:
        return "Developer"
    if first.startswith("3_cli") or first == "cli":
        return "CLI"
    if "lmlink" in first:
        return "LM Link"
    return ""


def _topic_from_path(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return ""
    leaf = _clean_path_part(parts[-1])
    parents = [_clean_path_part(p) for p in parts[:-1]]
    parents = [p for p in parents if p and p not in {"Python", "TypeScript", "Developer"}]
    if leaf.lower() in {"index", "readme"} and parents:
        return parents[-1]
    if len(parts) >= 2 and any(token in path.lower() for token in ("api-reference", "getting-started", "plugins", "presets")):
        platform = _platform_from_path(path)
        if platform and not leaf.startswith(platform):
            return f"{platform} {leaf}"
    return leaf or path


def _nicify_title(path: str) -> str:
    if re.search(r"(^|/)README\.md$", path, flags=re.I):
        return "README"
    return _topic_from_path(path) or path


def _short_note(path: str) -> str:
    lower = path.lower()
    platform = _platform_from_path(path)
    topic = _topic_from_path(path)
    subject = topic or "this page"
    platform_prefix = f"{platform} " if platform and not subject.lower().startswith(platform.lower()) else ""

    if any(hint in lower for hint in ["getting-started", "quickstart", "install", "overview", "/readme"]):
        return f"start here for {platform_prefix}{subject.lower()} setup and first-run workflow"
    if any(hint in lower for hint in ["reference", "/api"]):
        return f"lookup the {platform_prefix}{subject.lower()} API contract, parameters, and return behavior"
    if any(hint in lower for hint in ["tutorial", "example", "how-to", "demo"]):
        return f"follow a worked example for {subject.lower()}"
    if any(hint in lower for hint in ["concept", "architecture", "design", "faq"]):
        return f"understand the concept or decision model behind {subject.lower()}"
    if "changelog" in lower or "release" in lower:
        return f"track version changes and migration notes for {subject.lower()}"
    if "license" in lower:
        return "review usage terms and redistribution constraints"
    if "security" in lower:
        return "review the security policy and reporting workflow"
    if "contributing" in lower:
        return "learn how contributors should edit, test, and submit changes"
    return f"read supporting documentation for {subject.lower()}"


def _finish_sentence(text: str) -> str:
    text = " ".join(str(text).strip().split())
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else text + "."


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


def build_document_from_buckets(
    project_name: str,
    project_purpose: str,
    remember_bullets: Iterable[str],
    buckets: List[Tuple[str, List[Tuple[str, str, str]]]],
) -> LLMsDocument:
    sections = [
        LLMsSection(
            name=name,
            entries=[LLMsLinkEntry(title=title, url=url, note=note) for title, url, note in items],
        )
        for name, items in buckets
        if items
    ]
    return LLMsDocument(
        project_name=project_name,
        project_purpose=project_purpose,
        remember_bullets=[str(bullet) for bullet in remember_bullets if str(bullet).strip()],
        sections=sections,
    )


def render_llms_markdown(document: LLMsDocument) -> str:
    bullets = [str(b).strip().rstrip(".") for b in document.remember_bullets if str(b).strip()]
    bullets = bullets[:6] or [
        "Install + Quickstart first",
        "Core concepts & API surface",
        "Use Tutorials for worked examples",
    ]
    if len(bullets) < 3:
        bullets += ["Review API reference", "See Optional for meta docs"][: 3 - len(bullets)]
    purpose_line = (document.project_purpose or "").strip().replace("\n", " ")

    out = [
        f"# {document.project_name}",
        "",
        f"> {purpose_line or 'Project overview unavailable.'}",
        "",
        "**Remember:**",
        *[f"- {bullet}" for bullet in bullets],
        "",
    ]
    for section in document.sections:
        if not section.entries:
            continue
        out.append(f"## {section.name}")
        out.extend(
            f"- [{entry.title}]({entry.url}): {_finish_sentence(entry.note)}"
            for entry in section.entries
        )
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


def _empty_prediction(**kwargs: Any) -> Any:
    return dspy.Prediction(**kwargs)


def _is_adapter_parse_error(exc: Exception) -> bool:
    return bool(AdapterParseError) and isinstance(exc, AdapterParseError)


class RepositoryAnalyzer(dspy.Module):
    """DSPy module that synthesizes an llms.txt summary for a GitHub repository."""

    def __init__(self, production_mode: bool = True) -> None:
        super().__init__()
        predictor = getattr(dspy, "Predict", dspy.ChainOfThought) if production_mode else dspy.ChainOfThought
        self.analyze_repo = predictor(AnalyzeRepository)
        self.analyze_repo_digest = predictor(AnalyzeRepositoryFromDigest)
        self.analyze_structure = predictor(AnalyzeCodeStructure)
        self.generate_examples = predictor(GenerateUsageExamples)
        self.plan_sections = predictor(PlanLLMsSections)
        self.synthesize_section_notes = predictor(SynthesizeLLMsSectionNotes)

    def _resolve_project_name(self, repo_url: str) -> str:
        try:
            _, repo = owner_repo_from_url(repo_url)
            return repo.replace("-", " ").replace("_", " ").title()
        except Exception:
            return "Project"

    def _run_repository_analysis(
        self,
        effective_repo_url: str,
        file_tree: str,
        readme_content: str,
        package_files: str,
        repo_digest: RepoDigest | None,
    ) -> tuple[Any, Any, str]:
        if repo_digest is not None:
            digest_summary = (
                f"Architecture: {repo_digest.architecture_summary}\n"
                f"Primary language: {repo_digest.primary_language}\n"
                f"Entry points: {', '.join(repo_digest.entry_points[:10])}\n"
                f"Dependencies: {', '.join(repo_digest.key_dependencies[:20])}\n"
            )
            try:
                repo_analysis = self.analyze_repo_digest(
                    digest_summary=digest_summary,
                    repo_url=effective_repo_url,
                )
            except Exception as exc:
                if not _is_adapter_parse_error(exc):
                    raise
                logger.warning(
                    "DSPy repository digest analysis response was not parseable; using deterministic digest summary. Reason: %s",
                    exc,
                )
                repo_analysis = _empty_prediction(
                    project_purpose=repo_digest.architecture_summary,
                    key_concepts=[
                        sub.get("name", "")
                        for sub in repo_digest.subsystems[:6]
                        if sub.get("name")
                    ]
                    or repo_digest.key_dependencies[:6],
                    architecture_overview=repo_digest.architecture_summary,
                )
            structure_analysis = dspy.Prediction(
                important_directories=[s.get("name", "") for s in repo_digest.subsystems[:8]],
                entry_points=repo_digest.entry_points[:10],
                development_info=repo_digest.architecture_summary,
            )
            effective_file_tree = file_tree or "\n".join(
                path
                for sub in repo_digest.subsystems
                for path in sub.get("paths", [])[:6]
            )
            return repo_analysis, structure_analysis, effective_file_tree

        try:
            repo_analysis = self.analyze_repo(
                repo_url=effective_repo_url,
                file_tree=file_tree,
                readme_content=readme_content,
            )
        except Exception as exc:
            if not _is_adapter_parse_error(exc):
                raise
            logger.warning(
                "DSPy repository analysis response was not parseable; using deterministic README summary. Reason: %s",
                exc,
            )
            repo_analysis = _empty_prediction(
                project_purpose=_readme_lead_sentence(readme_content) or "Project overview unavailable.",
                key_concepts=[],
                architecture_overview="",
            )
        try:
            structure_analysis = self.analyze_structure(
                file_tree=file_tree,
                package_files=package_files,
            )
        except Exception as exc:
            if not _is_adapter_parse_error(exc):
                raise
            logger.warning(
                "DSPy structure analysis response was not parseable; using deterministic structure fallback. Reason: %s",
                exc,
            )
            structure_analysis = _empty_prediction(
                important_directories=[],
                entry_points=[],
                development_info="Repository structure summary unavailable.",
            )
        return repo_analysis, structure_analysis, file_tree

    def _plan_evidence(
        self,
        repo_url: str,
        file_tree: str,
        default_branch: str | None,
        is_private: bool,
        github_token: str | None,
        link_style: str,
    ) -> tuple[list[tuple[str, list[tuple[str, str, str]]]], AnalyzerTrace]:
        buckets = build_dynamic_buckets(
            repo_url,
            file_tree,
            default_ref=default_branch,
            validate_urls=True,
            is_private=is_private,
            github_token=github_token,
            link_style=link_style,
        )
        trace = AnalyzerTrace(
            selected_evidence=[
                {
                    "section": section_name,
                    "title": title,
                    "url": url,
                    "note": note,
                }
                for section_name, items in buckets
                for title, url, note in items
            ],
            dropped_evidence=[],
            compaction_reasons=[
                "Context compaction and retry budgeting remain enforced upstream in pipeline.run_generation()."
            ],
        )
        return buckets, trace

    def _inspect_evidence(
        self,
        repo_analysis: Any,
        structure_analysis: Any,
        readme_content: str,
        repo_digest: RepoDigest | None,
    ) -> tuple[str, list[str], list[str], list[str], str]:
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
            development_info = _as_text(
                repo_digest.architecture_summary,
                default="Repository architecture summary unavailable.",
            )

        return project_purpose, key_concepts, important_directories, entry_points, development_info

    def _build_usage_section(
        self,
        project_purpose: str,
        key_concepts: list[str],
        entry_points: list[str],
    ) -> LLMsSection | None:
        try:
            usage_prediction = self.generate_examples(
                repo_info=(
                    f"Purpose: {project_purpose}\n\n"
                    f"Concepts: {', '.join(key_concepts)}\n\n"
                    f"Entry points: {', '.join(entry_points)}\n"
                )
            )
        except Exception as exc:
            if not _is_adapter_parse_error(exc):
                raise
            logger.warning(
                "DSPy usage-example response was not parseable; omitting model usage section. Reason: %s",
                exc,
            )
            return None
        usage_examples = _as_text(_pred_get(usage_prediction, "usage_examples"))
        if not usage_examples:
            return None
        return LLMsSection(
            name="Usage",
            entries=[
                LLMsLinkEntry(
                    title="Common Usage Patterns",
                    url="about:usage-examples",
                    note=usage_examples.replace("\n", " ").strip(),
                )
            ],
        )


    def _filter_sections(
        self,
        sections: list[LLMsSection],
        included_sections: list[str],
    ) -> tuple[list[LLMsSection], bool]:
        if not included_sections:
            return sections, False
        included = set(included_sections)
        filtered = [section for section in sections if section.name in included]
        return (filtered or sections), bool(filtered)

    def _apply_section_order(
        self,
        sections: list[LLMsSection],
        preferred_order: list[str],
    ) -> tuple[list[LLMsSection], bool]:
        if not preferred_order:
            return sections, False

        section_by_name = {section.name: section for section in sections}
        ordered: list[LLMsSection] = []
        seen: set[str] = set()
        for name in preferred_order:
            if name in section_by_name and name not in seen:
                ordered.append(section_by_name[name])
                seen.add(name)
        for section in sections:
            if section.name not in seen:
                ordered.append(section)
        if not ordered:
            return sections, False
        return ordered, True

    def _plan_sections(
        self,
        project_name: str,
        project_purpose: str,
        key_concepts: list[str],
        important_directories: list[str],
        entry_points: list[str],
        development_info: str,
        buckets: list[tuple[str, list[tuple[str, str, str]]]],
        usage_section: LLMsSection | None,
        trace: AnalyzerTrace,
    ) -> LLMsDocument:
        document = build_document_from_buckets(
            project_name=project_name,
            project_purpose=project_purpose,
            remember_bullets=key_concepts,
            buckets=buckets,
        )
        if usage_section is not None:
            document.sections.insert(0, usage_section)

        deterministic_sections = [section.name for section in document.sections]
        deterministic_bullets = list(document.remember_bullets)
        trace.deterministic_section_planning = {
            "available_sections": deterministic_sections,
            "remember_bullets": deterministic_bullets,
            "usage_section_added": usage_section is not None,
        }

        try:
            section_plan_prediction = self.plan_sections(
                project_name=project_name,
                project_purpose=project_purpose,
                key_concepts=key_concepts,
                important_directories=important_directories,
                entry_points=entry_points,
                development_info=development_info,
                available_sections=deterministic_sections,
            )
        except Exception as exc:
            if not _is_adapter_parse_error(exc):
                raise
            logger.warning(
                "DSPy section-plan response was not parseable; using deterministic section plan. Reason: %s",
                exc,
            )
            section_plan_prediction = _empty_prediction()
        included_sections = _as_list_of_text(_pred_get(section_plan_prediction, "included_sections"))
        preferred_order = _as_list_of_text(_pred_get(section_plan_prediction, "preferred_section_order"))
        planned_bullets = _as_list_of_text(_pred_get(section_plan_prediction, "remember_bullets"))

        document.sections, used_model_filter = self._filter_sections(document.sections, included_sections)
        filtered_sections = [section.name for section in document.sections]
        document.sections, used_model_order = self._apply_section_order(document.sections, preferred_order)
        final_sections = [section.name for section in document.sections]
        remember_source = "model" if planned_bullets else "deterministic"
        if planned_bullets:
            document.remember_bullets = planned_bullets

        plan_source = "model" if (used_model_filter or used_model_order or planned_bullets) else "deterministic"
        trace.model_section_planning = {
            "included_sections": included_sections,
            "preferred_section_order": preferred_order,
            "remember_bullets": planned_bullets,
            "used_model_filter": used_model_filter,
            "used_model_order": used_model_order,
            "remember_source": remember_source,
            "filtered_sections": filtered_sections,
            "final_sections": final_sections,
        }
        self._synthesize_section_content(project_name, project_purpose, document, trace)
        trace.section_plan = [
            {
                "name": section.name,
                "entry_count": len(section.entries),
                "titles": [entry.title for entry in section.entries[:10]],
                "source": plan_source,
            }
            for section in document.sections
        ]
        return document

    def _is_useful_section_note(self, section_name: str, note: str, entries: list[LLMsLinkEntry]) -> bool:
        cleaned = " ".join(note.strip().split())
        if len(cleaned) < 48:
            return False
        lowered = cleaned.lower()
        generic_phrases = (
            "general documentation",
            "various functionalities",
            "core concepts and frequently asked questions",
            "related to the project",
            "this section contains",
            "documentation and guides",
        )
        if any(phrase in lowered for phrase in generic_phrases):
            return False
        entry_terms = {
            token.lower()
            for entry in entries
            for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", f"{entry.title} {entry.note}")
            if len(token) > 3
        }
        note_terms = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", cleaned) if len(token) > 3}
        # Keep a model note only if it appears grounded in the concrete links for the section.
        return bool(entry_terms & note_terms) or section_name.lower() in lowered

    def _deterministic_section_note(self, section: LLMsSection) -> str:
        titles = [entry.title for entry in section.entries if not entry.url.startswith("about:")]
        notes = [entry.note for entry in section.entries if not entry.url.startswith("about:")]
        title_list = ", ".join(titles[:4])
        if section.name == "Docs":
            return f"Use this section for the first successful path through the project; it prioritizes {title_list or 'setup and overview pages'} so readers can orient before deeper API work"
        if section.name == "API":
            return f"Use this section as the contract surface; it links concrete references such as {title_list or 'the exported API pages'} and should answer what call, parameter, or return shape to inspect"
        if section.name == "Tutorials":
            return f"Use this section when examples matter more than exhaustive reference; it collects worked flows such as {title_list or 'hands-on examples'}"
        if section.name == "Concepts":
            return f"Use this section to understand the product mental model behind the implementation; it points to {title_list or 'conceptual docs'} before code-level changes"
        if section.name == "Optional":
            return f"Use this section for project maintenance and meta information; it includes {title_list or 'supporting repository pages'} rather than the primary integration path"
        sample = title_list or ", ".join(notes[:3]) or section.name
        return f"Use this section for {section.name.lower()} material, especially {sample}, when deciding where a reader should go next"

    def _synthesize_section_content(
        self,
        project_name: str,
        project_purpose: str,
        document: LLMsDocument,
        trace: AnalyzerTrace,
    ) -> None:
        """Ask DSPy for concise section notes and render them deterministically."""
        if not document.sections:
            trace.model_section_planning.setdefault("section_content_synthesis", {"used": False, "notes": {}})
            return

        candidate_entries = [
            f"{section.name} | {entry.title} | {entry.url} | {entry.note}"
            for section in document.sections
            for entry in section.entries[:10]
        ]
        try:
            synthesis_prediction = self.synthesize_section_notes(
                project_name=project_name,
                project_purpose=project_purpose,
                section_plan=[section.name for section in document.sections],
                candidate_entries=candidate_entries,
            )
        except Exception as exc:
            if not _is_adapter_parse_error(exc):
                raise
            logger.warning(
                "DSPy section-note response was not parseable; skipping model section notes. Reason: %s",
                exc,
            )
            trace.model_section_planning["section_content_synthesis"] = {
                "used": False,
                "notes": {},
                "fallback_reason": "adapter-parse-error",
            }
            return
        raw_notes = _as_list_of_text(_pred_get(synthesis_prediction, "section_notes"))
        notes_by_section: dict[str, str] = {}
        valid_sections = {section.name for section in document.sections}
        rejected_notes: dict[str, str] = {}
        for raw_note in raw_notes:
            section_name, sep, note = raw_note.partition(":")
            section_name = section_name.strip()
            note = _finish_sentence(note.strip()).rstrip(".")
            section = next((candidate for candidate in document.sections if candidate.name == section_name), None)
            if not sep or section is None or not note:
                continue
            if self._is_useful_section_note(section_name, note, section.entries):
                notes_by_section[section_name] = note
            else:
                rejected_notes[section_name] = note

        inserted_notes: dict[str, str] = {}
        for section in document.sections:
            if section.name == "Usage" or all(entry.url.startswith("about:") for entry in section.entries):
                continue
            note = notes_by_section.get(section.name)
            source = "model"
            if not note:
                note = self._deterministic_section_note(section)
                source = "deterministic"
            section.entries.insert(
                0,
                LLMsLinkEntry(
                    title=f"{section.name} Overview",
                    url="about:section-synthesis",
                    note=note,
                ),
            )
            inserted_notes[section.name] = f"{source}: {note}"

        trace.model_section_planning["section_content_synthesis"] = {
            "used": bool(inserted_notes),
            "notes": inserted_notes,
            "rejected_notes": rejected_notes,
        }

    def _render_document(self, document: LLMsDocument) -> str:
        return render_llms_markdown(document)

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
        repo_analysis, structure_analysis, effective_file_tree = self._run_repository_analysis(
            effective_repo_url,
            file_tree,
            readme_content,
            package_files,
            repo_digest,
        )
        project_purpose, key_concepts, important_directories, entry_points, development_info = self._inspect_evidence(
            repo_analysis,
            structure_analysis,
            readme_content,
            repo_digest,
        )
        project_name = self._resolve_project_name(effective_repo_url)
        buckets, trace = self._plan_evidence(
            effective_repo_url,
            effective_file_tree,
            default_branch,
            is_private,
            github_token,
            link_style,
        )
        usage_section = self._build_usage_section(project_purpose, key_concepts, entry_points)
        document = self._plan_sections(
            project_name,
            project_purpose,
            key_concepts,
            important_directories,
            entry_points,
            development_info,
            buckets,
            usage_section,
            trace,
        )
        llms_txt_content = self._render_document(document)

        return dspy.Prediction(
            llms_txt_content=llms_txt_content,
            document=document,
            trace=trace,
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
