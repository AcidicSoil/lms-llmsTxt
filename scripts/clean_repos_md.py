# path: scripts/clean_repos_md.py
"""
Clean a repo-list Markdown file so only canonical GitHub repo URLs remain.

Input may contain:
- bare URLs: https://github.com/owner/repo
- autolinks: <https://github.com/owner/repo>
- Markdown links: [text](https://github.com/owner/repo)
- reference defs: [id]: https://github.com/owner/repo
- SSH: git@github.com:owner/repo(.git)
- file links: https://github.com/owner/repo/blob/... or https://raw.githubusercontent.com/owner/repo/...

Output is one canonical repo URL per line:
  https://github.com/<owner>/<repo>

Examples:
  python scripts/clean_repos_md.py docs/charm_bracelet_repos/repos.md --in-place
  python scripts/clean_repos_md.py repos.md --out repos.clean.md
  python scripts/clean_repos_md.py repos.md --stdout
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from urllib.parse import urlparse


# Broadly capture GitHub-ish tokens; sanitize after capture.
_GH_CANDIDATE = re.compile(
    r"""
    (?:
        https?://(?:www\.)?(?:github\.com|raw\.githubusercontent\.com)/[^\s<>()\[\]{}"']+
        |
        git@github\.com:[^\s<>()\[\]{}"']+
        |
        (?:www\.)?github\.com/[^\s<>()\[\]{}"']+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Conservative segment validation (avoid garbage leaking into URLs).
_SEGMENT_OK = re.compile(r"^[A-Za-z0-9._-]+$")


def _strip_wrappers(s: str) -> str:
    # peel common surrounding wrappers repeatedly (handles nested like "([<url>])")
    u = s.strip()
    while True:
        before = u
        u = u.strip()
        u = u.strip("<>")
        u = u.strip("()")
        u = u.strip("[]")
        u = u.strip("{}")
        u = u.strip()
        if u == before:
            break
    return u


def _sanitize_github_repo_url(candidate: str) -> str | None:
    """
    Return canonical https://github.com/<owner>/<repo> or None if invalid.

    Accepts:
    - https://github.com/owner/repo[/*]
    - https://www.github.com/owner/repo[/*]
    - github.com/owner/repo[/*]   (scheme-less)
    - git@github.com:owner/repo(.git)
    - https://raw.githubusercontent.com/owner/repo/ref/path (extract owner/repo)
    """
    if not candidate:
        return None

    u = _strip_wrappers(candidate)

    # Strip trailing punctuation common in Markdown contexts.
    # Keep "/" because it's meaningful; remove punctuation that commonly follows URLs.
    u = u.rstrip(")>]}.;,:'\"`")

    # Normalize scheme-less inputs.
    low = u.lower()
    if low.startswith("github.com/") or low.startswith("www.github.com/"):
        u = "https://" + u

    # Handle SSH style.
    if low.startswith("git@github.com:"):
        # git@github.com:owner/repo(.git)[/...]
        rest = u.split(":", 1)[1].strip()
        rest = rest.lstrip("/")
        rest = rest.rstrip(")>]}.;,:'\"`")
        parts = [p for p in rest.split("/") if p]
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        if repo.endswith(".git"):
            repo = repo[: -len(".git")]
        if not (_SEGMENT_OK.match(owner) and _SEGMENT_OK.match(repo)):
            return None
        return f"https://github.com/{owner}/{repo}"

    parsed = urlparse(u)
    if parsed.scheme not in {"http", "https"}:
        return None

    netloc = (parsed.netloc or "").lower()
    path_parts = [p for p in (parsed.path or "").split("/") if p]

    # raw.githubusercontent.com/owner/repo/ref/path...
    if netloc == "raw.githubusercontent.com":
        if len(path_parts) < 2:
            return None
        owner, repo = path_parts[0], path_parts[1]
    else:
        # github.com or www.github.com
        if netloc == "www.github.com":
            netloc = "github.com"
        if netloc != "github.com":
            return None
        if len(path_parts) < 2:
            return None
        owner, repo = path_parts[0], path_parts[1]

    if repo.endswith(".git"):
        repo = repo[: -len(".git")]

    if not (_SEGMENT_OK.match(owner) and _SEGMENT_OK.match(repo)):
        return None

    return f"https://github.com/{owner}/{repo}"


def extract_repo_urls(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in _GH_CANDIDATE.findall(text):
        url = _sanitize_github_repo_url(raw)
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to the Markdown file to clean (e.g., repos.md)")
    ap.add_argument("--out", default=None, help="Write cleaned URLs to this path")
    ap.add_argument(
        "--in-place",
        "-ip",
        action="store_true",
        help="Overwrite the input file with cleaned URLs",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Write cleaned URLs to stdout",
    )
    ap.add_argument(
        "--sort",
        action="store_true",
        help="Sort URLs lexicographically (default preserves first-seen order)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if no GitHub repo URLs are found",
    )
    args = ap.parse_args(argv)

    in_path = pathlib.Path(args.input)
    text = in_path.read_text(encoding="utf-8", errors="replace")

    urls = extract_repo_urls(text)
    if args.sort:
        urls = sorted(urls)

    if not urls and args.strict:
        sys.stderr.write(f"[error] no GitHub repo URLs found in {in_path}\n")
        return 2

    out_text = "\n".join(urls) + ("\n" if urls else "")

    wrote_somewhere = False

    if args.in_place:
        in_path.write_text(out_text, encoding="utf-8")
        wrote_somewhere = True

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_text, encoding="utf-8")
        wrote_somewhere = True

    if args.stdout or not wrote_somewhere:
        sys.stdout.write(out_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
