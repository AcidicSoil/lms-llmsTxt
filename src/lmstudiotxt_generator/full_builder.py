from __future__ import annotations

import base64
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import requests


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
        "User-Agent": "lmstudio-llmstxt-generator",
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


_PAGE_LINK = re.compile(r"^\s*-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^\s)]+)\)", re.M)


def iter_llms_links(curated_text: str) -> Iterable[Tuple[str, str]]:
    for match in _PAGE_LINK.finditer(curated_text):
        yield match.group("title").strip(), match.group("url").strip()


def sanitize_path_for_block(title: str, url: str, gh: Optional[GhRef]) -> str:
    if gh:
        path = gh.path
    else:
        path = title.lower().strip().replace(" ", "-")
    return path.lstrip("/")


def build_llms_full_from_repo(
    curated_llms_text: str,
    max_bytes_per_file: int = 800_000,
    max_files: int = 100,
) -> str:
    token = os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
    blocks = []
    seen = set()
    count = 0

    for title, url in iter_llms_links(curated_llms_text):
        if count >= max_files:
            break
        gh = parse_github_link(url)
        if not gh:
            continue

        key = (gh.owner, gh.repo, gh.path, gh.ref or "")
        if key in seen:
            continue
        seen.add(key)

        try:
            _, body = gh_get_file(gh.owner, gh.repo, gh.path, gh.ref, token)
        except Exception as exc:  # pragma: no cover - diagnostic text only
            body = f"[fetch-error] {gh.owner}/{gh.repo}/{gh.path}@{gh.ref or 'default'} :: {exc}".encode(
                "utf-8"
            )

        if len(body) > max_bytes_per_file:
            body = body[:max_bytes_per_file] + b"\n[truncated]\n"

        block_path = sanitize_path_for_block(title, url, gh)
        blocks.append(f"--- {block_path} ---\n{body.decode('utf-8', 'replace')}\n")
        count += 1

    disclaimer = textwrap.dedent(
        """\
        # llms-full (private-aware)
        > Built by authenticated GitHub API fetches. Large files may be truncated.
        """
    )
    return disclaimer + "\n" + "\n".join(blocks)
