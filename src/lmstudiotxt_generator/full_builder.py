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


def fetch_raw_file(
    owner: str,
    repo: str,
    path: str,
    ref: str,
) -> bytes:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    response = requests.get(
        url,
        headers={"User-Agent": "lmstudio-llmstxt-generator"},
        timeout=30,
    )
    if response.status_code == 404:
        raise FileNotFoundError(f"Raw GitHub 404 for {owner}/{repo}/{path}@{ref}")  # noqa: EM102
    response.raise_for_status()
    return response.content


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
    *,
    prefer_raw: bool = False,
    default_ref: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
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
        if not gh:
            continue

        key = (gh.owner, gh.repo, gh.path, gh.ref or "")
        if key in seen:
            continue
        seen.add(key)

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
        except requests.HTTPError as exc:  # pragma: no cover - diagnostic text only
            message = _format_http_error(gh, resolved_ref, exc, auth_used=not prefer_raw)
            body = message.encode("utf-8")
        except Exception as exc:  # pragma: no cover - diagnostic text only
            message = _format_generic_error(gh, resolved_ref, exc)
            body = message.encode("utf-8")

        if len(body) > max_bytes_per_file:
            body = body[:max_bytes_per_file] + b"\n[truncated]\n"

        block_path = sanitize_path_for_block(title, url, gh)
        blocks.append(f"--- {block_path} ---\n{body.decode('utf-8', 'replace')}\n")
        count += 1

    disclaimer = textwrap.dedent(
        """\
        # llms-full (private-aware)
        > Built by GitHub fetches (raw or authenticated). Large files may be truncated.
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
