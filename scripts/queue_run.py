# path: queue_run.py
"""Queue `lmstxt` runs for GitHub repos listed in repos.md.

Why sanitization is needed
-------------------------
Your repos.md currently uses Markdown autolinks like:
  <https://github.com/Unity-Technologies/Graphics>

The previous regex (`https://github\.com/[^\s)]+`) captures the trailing `>`.
That produces invalid URLs (and also breaks log filenames).

This script extracts GitHub URLs from common Markdown forms and canonicalizes each
entry to:
  https://github.com/<owner>/<repo>
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from urllib.parse import urlparse


# Matches any GitHub URL up to whitespace; we sanitize after capture.
_GH_CANDIDATE = re.compile(r"https?://github\.com/[^\s]+", re.IGNORECASE)


def _sanitize_github_repo_url(candidate: str) -> str | None:
    """Return canonical https://github.com/<owner>/<repo> or None if invalid."""
    if not candidate:
        return None

    u = candidate.strip()

    # Common Markdown/typography wrappers around URLs.
    u = u.strip("<>").strip()

    # Strip common trailing punctuation from Markdown contexts.
    # Example: https://github.com/o/r) or https://github.com/o/r> or ...,
    u = u.rstrip(")>]}.;,:'\"`")

    parsed = urlparse(u)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc.lower() != "github.com":
        return None

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]

    return f"https://github.com/{owner}/{repo}"


def _safe_slug(text: str) -> str:
    """Filesystem-safe slug for logs."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


def _extract_repo_urls(markdown_text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    for raw in _GH_CANDIDATE.findall(markdown_text):
        url = _sanitize_github_repo_url(raw)
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)

    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--repos-file",
        default="repos.md",
        help="Path to repos.md (default: repos.md)",
    )
    p.add_argument(
        "--cli",
        default="lmstxt",
        help='CLI to invoke (default: "lmstxt"). Use "lmstudio-lmstxt" if that is installed.',
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print sanitized URLs and exit.",
    )
    args = p.parse_args(argv)

    md_path = pathlib.Path(args.repos_file)
    md = md_path.read_text(encoding="utf-8")
    urls = _extract_repo_urls(md)

    if args.dry_run:
        for u in urls:
            print(u)
        return 0

    pathlib.Path("logs").mkdir(exist_ok=True)

    for u in urls:
        owner_repo = "-".join(urlparse(u).path.strip("/").split("/")[:2])
        log = pathlib.Path("logs") / f"{_safe_slug(owner_repo)}.log"

        cmd = [args.cli, u]
        print(">>", " ".join(cmd))
        with log.open("w", encoding="utf-8") as fh:
            p_run = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            fh.write(p_run.stdout)
            sys.stdout.write(p_run.stdout)
            sys.stdout.flush()

        if p_run.returncode != 0:
            print(f"[error] failed for {u} (see {log})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
