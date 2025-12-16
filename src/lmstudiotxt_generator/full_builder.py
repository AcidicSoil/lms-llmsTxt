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
        "User-Agent": "llmstxt-generator",
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
        headers={"User-Agent": "llmstxt-generator"},
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


def _fetch_website(url: str, user_agent: str = "llmstxt-generator", timeout: int = 30) -> str:
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
