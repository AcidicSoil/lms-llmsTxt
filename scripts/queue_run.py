# path: scripts/queue_run.py
r"""Queue `lmstxt` runs for GitHub repos listed in repos.md.

Why sanitization is needed
-------------------------
repos.md can contain Markdown autolinks like:
  <https://github.com/Unity-Technologies/Graphics>

A naive regex like: https://github\.com/[^\s)]+
often captures trailing wrappers like '>' or ')', producing invalid URLs and
bad log filenames.

This script extracts GitHub URLs from common Markdown forms and canonicalizes
each entry to:
  https://github.com/<owner>/<repo>
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import selectors
import signal
import subprocess
import sys
import time
from typing import TextIO
from urllib.parse import urlparse

try:
    import pty  # Unix/WSL only
except Exception:  # pragma: no cover
    pty = None  # type: ignore[assignment]


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


def _tee_write(out: TextIO, log: TextIO, s: str) -> None:
    out.write(s)
    out.flush()
    log.write(s)
    log.flush()


def _run_with_pipes(
    cmd: list[str],
    log_fh: TextIO,
    timeout_s: float | None,
) -> int:
    """
    Stream child stdout+stderr line-by-line (no PTY).
    Good default when PTY isn't available.
    """
    start = time.monotonic()

    # Keep stdin attached so a user can respond to prompts; stdout is piped for tee.
    p = subprocess.Popen(
        cmd,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    assert p.stdout is not None

    try:
        for line in p.stdout:
            _tee_write(sys.stdout, log_fh, line)

            if timeout_s is not None and (time.monotonic() - start) > timeout_s:
                _tee_write(sys.stdout, log_fh, "\n[timeout] terminating...\n")
                p.terminate()
                break

        # Ensure the process ends.
        try:
            rc = p.wait(timeout=10 if timeout_s is not None else None)
        except subprocess.TimeoutExpired:
            _tee_write(sys.stdout, log_fh, "[timeout] killing...\n")
            p.kill()
            rc = p.wait()

        return rc

    except KeyboardInterrupt:
        _tee_write(sys.stdout, log_fh, "\n[interrupt] forwarding SIGINT...\n")
        try:
            p.send_signal(signal.SIGINT)
        except Exception:
            pass

        try:
            rc = p.wait(timeout=3)
            return rc
        except Exception:
            _tee_write(sys.stdout, log_fh, "[interrupt] terminating...\n")
            try:
                p.terminate()
            except Exception:
                pass
            try:
                rc = p.wait(timeout=3)
                return rc
            except Exception:
                _tee_write(sys.stdout, log_fh, "[interrupt] killing...\n")
                try:
                    p.kill()
                except Exception:
                    pass
                return p.wait()


def _run_with_pty(
    cmd: list[str],
    log_fh: TextIO,
    timeout_s: float | None,
) -> int:
    """
    Run child with a PTY for stdout/stderr so tools behave like they're on a real terminal.
    We still tee bytes to both terminal and the log.

    Notes:
    - stdin remains attached to the user's terminal so interactive prompts work.
    - output may include ANSI control sequences; we preserve them in logs.
    """
    if pty is None:
        return _run_with_pipes(cmd, log_fh, timeout_s)

    start = time.monotonic()

    master_fd, slave_fd = pty.openpty()

    # Route stdout+stderr to the PTY slave.
    # Keep stdin attached (None -> inherit), so prompts can be answered.
    p = subprocess.Popen(
        cmd,
        stdin=None,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )

    # Parent doesn't need the slave.
    try:
        os.close(slave_fd)
    except Exception:
        pass

    sel = selectors.DefaultSelector()
    sel.register(master_fd, selectors.EVENT_READ)

    def _drain_available() -> bool:
        """
        Read and write available bytes from master_fd.
        Returns False when EOF-ish.
        """
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            return False
        if not data:
            return False

        # Write raw bytes to stdout buffer when possible; fall back to decode.
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.flush()
        except Exception:
            sys.stdout.write(data.decode("utf-8", errors="replace"))
            sys.stdout.flush()

        try:
            log_fh.write(data.decode("utf-8", errors="replace"))
            log_fh.flush()
        except Exception:
            # If the log file can't take text for some reason, last resort: ignore.
            pass

        return True

    try:
        while True:
            # Timeout check
            if timeout_s is not None and (time.monotonic() - start) > timeout_s:
                _tee_write(sys.stdout, log_fh, "\n[timeout] terminating...\n")
                try:
                    p.terminate()
                except Exception:
                    pass

            # If process ended, drain remaining output then break.
            rc = p.poll()
            if rc is not None:
                # Drain whatever is left.
                while True:
                    ready = sel.select(timeout=0)
                    if not ready:
                        break
                    if not _drain_available():
                        break
                return rc

            events = sel.select(timeout=0.1)
            for _key, _mask in events:
                if not _drain_available():
                    # If PTY closes unexpectedly, wait for process.
                    try:
                        return p.wait(timeout=5)
                    except Exception:
                        return p.returncode if p.returncode is not None else 1

    except KeyboardInterrupt:
        _tee_write(sys.stdout, log_fh, "\n[interrupt] forwarding SIGINT...\n")
        try:
            p.send_signal(signal.SIGINT)
        except Exception:
            pass

        try:
            rc2 = p.wait(timeout=3)
            return rc2
        except Exception:
            _tee_write(sys.stdout, log_fh, "[interrupt] terminating...\n")
            try:
                p.terminate()
            except Exception:
                pass
            try:
                rc3 = p.wait(timeout=3)
                return rc3
            except Exception:
                _tee_write(sys.stdout, log_fh, "[interrupt] killing...\n")
                try:
                    p.kill()
                except Exception:
                    pass
                return p.wait()

    finally:
        try:
            sel.unregister(master_fd)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass


def _pick_use_pty(explicit: bool | None) -> bool:
    """
    Decide whether to use PTY.
    - If user explicitly sets it, respect that.
    - Otherwise, use PTY when running in a real terminal and PTY support exists.
    """
    if explicit is not None:
        return explicit
    return (pty is not None) and sys.stdout.isatty() and sys.stdin.isatty()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--repos-file",
        "-rf",
        default="repos.md",
        help="Path to repos.md (default: repos.md)",
    )
    p.add_argument(
        "--cli",
        default="lmstxt",
        help='CLI to invoke (default: "lmstxt"). Use "lmstudio-lmstxt" if that is installed.',
    )
    p.add_argument(
        "--logs-dir",
        default="logs",
        help='Directory to write logs (default: "logs")',
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print sanitized URLs and exit.",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Per-repo timeout in seconds (default: none).",
    )
    p.add_argument(
        "--pty",
        dest="pty",
        action="store_true",
        default=None,
        help="Force PTY mode for child output (best for interactive CLIs).",
    )
    p.add_argument(
        "--no-pty",
        dest="pty",
        action="store_false",
        default=None,
        help="Disable PTY mode (fallback to pipe streaming).",
    )
    args = p.parse_args(argv)

    md_path = pathlib.Path(args.repos_file)
    md = md_path.read_text(encoding="utf-8")
    urls = _extract_repo_urls(md)

    if args.dry_run:
        for u in urls:
            print(u)
        return 0

    logs_dir = pathlib.Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    use_pty = _pick_use_pty(args.pty)

    failures: list[str] = []

    for u in urls:
        owner_repo = "-".join(urlparse(u).path.strip("/").split("/")[:2])
        log_path = logs_dir / f"{_safe_slug(owner_repo)}.log"

        cmd = [args.cli, u]
        print(">>", " ".join(cmd))
        with log_path.open("w", encoding="utf-8") as log_fh:
            # Header to make logs self-describing
            log_fh.write(f"$ {' '.join(cmd)}\n")
            log_fh.write(f"# started: {time.strftime('%Y-%m-%d %H:%M:%S %z')}\n\n")
            log_fh.flush()

            if use_pty:
                rc = _run_with_pty(cmd, log_fh, args.timeout)
            else:
                rc = _run_with_pipes(cmd, log_fh, args.timeout)

            log_fh.write(f"\n# exit_code: {rc}\n")
            log_fh.write(f"# finished: {time.strftime('%Y-%m-%d %H:%M:%S %z')}\n")
            log_fh.flush()

        if rc != 0:
            failures.append(u)
            print(f"[error] failed for {u} (see {log_path})")
        else:
            print(f"[ok] {u} (log: {log_path})")

    if failures:
        print("\nFailures:")
        for u in failures:
            print(" -", u)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
