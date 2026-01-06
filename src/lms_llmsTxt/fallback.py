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
    link_style: str = "blob",
) -> Dict[str, object]:
    buckets = build_dynamic_buckets(
        repo_url,
        file_tree,
        default_ref=default_branch,
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
    link_style: str = "blob",
) -> str:
    payload = fallback_llms_payload(
        repo_name=repo_name,
        repo_url=repo_url,
        file_tree=file_tree,
        readme_content=readme_content,
        default_branch=default_branch,
        link_style=link_style,
    )
    return fallback_markdown_from_payload(repo_name, payload)


__all__ = [
    "fallback_llms_payload",
    "fallback_llms_markdown",
    "fallback_markdown_from_payload",
]
