from __future__ import annotations

import base64
import os
import re
from typing import Iterable

import requests

from .models import RepositoryMaterial

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
        "User-Agent": "lmstudio-llmstxt-generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_default_branch(owner: str, repo: str, token: str | None) -> str:
    resp = _SESSION.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=_auth_headers(token),
        timeout=20,
    )
    if resp.status_code == 404:
        raise FileNotFoundError(f"Repository not found: {owner}/{repo}")
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("default_branch", "main")


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
    ref = get_default_branch(owner, repo, token)

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
    )


def construct_raw_url(repo_url: str, path: str, ref: str | None = None) -> str:
    owner, repo = owner_repo_from_url(repo_url)
    if not ref:
        token = os.getenv("GITHUB_ACCESS_TOKEN") or os.getenv("GH_TOKEN")
        try:
            ref = get_default_branch(owner, repo, token)
        except Exception:
            ref = "main"
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
